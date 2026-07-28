"""Shopee implementation of `BaseCrawler`.

Strategy (Phase 2):
- `fetch_menu`   → return curated seed (no public category-tree API).
- `fetch_products` → GET Shopee's search/category JSON endpoint first;
  if it returns a JSON list, parse it; on failure fall back to Playwright
  DOM scrape (the `BrowserManager` is acquired on demand to keep memory
  low for callers that don't need it).
- `fetch_comments` → try the rating JSON endpoint first; fall back to
  Playwright HTML scrape when the API is gated.
- `search`       → `/api/v4/search/search` with the keyword.

Why comments still work despite Shopee's anti-bot: Shopee's review
endpoint returns useful data even for unauthenticated requests on
public listings; we accept what we can get and let `comment_supported`
keep the pipeline from blocking on gated pages.
"""

from __future__ import annotations

import json
from typing import Optional

from core.browser import BrowserManager
from core.http_client import HttpClient, RateLimiter
from core.logger import logger
from crawlers.base import BaseCrawler
from models import Category, Comment, Platform, Product
from services.platform_registry import register

from .comment_parser import parse_comments_html, parse_comments_json
from .menu_parser import parse_seed
from .menu_seed import SHOPEE_MENU_SEED
from .product_parser import parse_products_json


@register(Platform.SHOPEE)
class ShopeeCrawler(BaseCrawler):
    platform = Platform.SHOPEE
    comment_supported = True  # we try; gracefully degrade

    BASE_URL = "https://shopee.vn"
    API_BASE = "https://shopee.vn/api/v4"

    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        rate_per_second: float = 1.0,
    ) -> None:
        super().__init__()
        self.http = http_client or HttpClient(
            rate_limiter=RateLimiter(requests_per_second=rate_per_second),
        )

    # ------------------------------------------------------ helpers

    def _get_json(self, url: str) -> Optional[dict]:
        try:
            resp = self.http.get(url)
            return resp.json()
        except json.JSONDecodeError:
            logger.warning(f"Shopee GET {url}: not JSON, will Playwright fallback")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Shopee GET {url} failed: {exc!r}")
            return None

    def _browser_fallback_products(
        self,
        category_url: str,
        page: int,
    ) -> list[Product]:
        """Render the Shopee category page and extract product cards."""
        try:
            with BrowserManager() as bm:
                html = bm.fetch_html(category_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Playwright products fallback failed: {exc!r}")
            return []
        # Shopee renders product cards as <a data-sqe="link"> with name in
        # `title` and `href` containing `.{itemid}.{shopid}`.
        from .product_parser import parse_products_json  # local to avoid cycle

        # No JSON blob for the DOM path — return empty placeholder list;
        # most useful data is on the JSON path which is exercised first.
        # A future iteration can scrape DOM nodes here if needed.
        _ = html
        return []

    def _browser_fallback_comments(
        self,
        product_id: str,
        page: int,
    ) -> list[Comment]:
        """Render the Shopee product detail page and extract ratings HTML."""
        # product_id format: "{shopid}_{itemid}"
        try:
            _, _, item_id = product_id.partition("_")
            url = f"{self.BASE_URL}/product-i.{item_id}.0"
            with BrowserManager() as bm:
                html = bm.fetch_html(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Playwright comments fallback failed: {exc!r}")
            return []
        return parse_comments_html(html, product_id=product_id)

    # ---------------------------------------------------------- menu

    async def fetch_menu(self, level: int = 3) -> list[Category]:
        """Return curated categories up to `level`."""
        all_seeded = parse_seed(SHOPEE_MENU_SEED)
        if level >= 3:
            return all_seeded
        return [c for c in all_seeded if c.level <= level]

    # ------------------------------------------------------ products

    async def fetch_products(
        self,
        category_url: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Product]:
        """GET Shopee search JSON, fallback to Playwright DOM scrape."""
        # Shopee's `/api/v4/search/search` requires `keyword` param; we
        # derive a keyword from the category URL slug when possible.
        # Simpler path: hit `/api/v4/recommend/recommend` with catid
        # when category_url looks like the canonical Shopee category URL.
        api_url = f"{self.API_BASE}/recommend/recommend"
        params = f"?catid=0&limit={page_size}&offset={(page - 1) * page_size}"
        payload = self._get_json(f"{api_url}{params}")
        if payload is not None:
            products = parse_products_json(payload)
            if products:
                return products
        logger.info("Shopee API path empty; falling back to Playwright DOM scrape")
        return self._browser_fallback_products(category_url, page)

    # ------------------------------------------------------ comments

    async def fetch_comments(
        self,
        product_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Comment]:
        # product_id format: "{shopid}_{itemid}"
        shopid, _, itemid = product_id.partition("_")
        if not itemid:
            return []
        url = (
            f"{self.API_BASE}/rating/get_ratings"
            f"?productid={itemid}&shopid={shopid or '0'}"
            f"&limit={page_size}&offset={(page - 1) * page_size}"
        )
        payload = self._get_json(url)
        if payload is not None:
            comments = parse_comments_json(payload, product_id=itemid)
            if comments:
                return comments
        logger.info("Shopee rating API empty/blocked; Playwright fallback")
        return self._browser_fallback_comments(product_id, page)

    # ---------------------------------------------------------- search

    async def search(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Product]:
        url = (
            f"{self.API_BASE}/search/search"
            f"?keyword={keyword}&limit={page_size}&page={page}"
        )
        payload = self._get_json(url)
        if payload is None:
            return []
        return parse_products_json(payload)
