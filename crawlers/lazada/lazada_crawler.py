"""Lazada implementation of `BaseCrawler`.

Strategy (Phase 3):
- `fetch_menu`   → curated seed (Lazada has no public category-tree
  endpoint that returns a full 3-level tree for the unauthenticated
  crawler).
- `fetch_products` → GET `/catalog/api/...` JSON endpoint; fall back
  to Playwright HTML scrape on failure.
- `fetch_comments` → GET the `/pdp/review/getReviewsByProductId`
  JSON endpoint. Lazada's productId in URLs is usually the numeric
  `p{id}.html` slug — we extract that automatically.
- `search`       → the `/catalog/api/search` endpoint.
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
from .menu_seed import LAZADA_MENU_SEED
from .product_parser import parse_products_json


@register(Platform.LAZADA)
class LazadaCrawler(BaseCrawler):
    platform = Platform.LAZADA
    comment_supported = True

    BASE_URL = "https://www.lazada.vn"
    API_BASE = "https://www.lazada.vn/catalog/api"

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
            logger.warning(f"Lazada GET {url}: not JSON, will Playwright fallback")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Lazada GET {url} failed: {exc!r}")
            return None

    @staticmethod
    def _extract_product_id(product_id: str) -> str:
        """Pull the numeric id from `p12345.html`, `i12345`, or raw `12345`."""
        if product_id.isdigit():
            return product_id
        if product_id.startswith("p") and product_id.endswith(".html"):
            mid = product_id[1:-5]
            if mid.isdigit():
                return mid
        # Fall back: take digit-only suffix if any
        digits = "".join(c for c in product_id if c.isdigit())
        return digits or product_id

    def _browser_fallback_products(self, category_url: str, page: int) -> list[Product]:
        try:
            with BrowserManager() as bm:
                bm.fetch_html(category_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Playwright Lazada products fallback failed: {exc!r}")
        # Lazada DOM scrape is out of scope for Phase 3; return empty.
        return []

    def _browser_fallback_comments(
        self,
        product_id: str,
        page: int,
    ) -> list[Comment]:
        numeric = self._extract_product_id(product_id)
        url = f"{self.BASE_URL}/products/p{numeric}.html"
        try:
            with BrowserManager() as bm:
                html = bm.fetch_html(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Playwright Lazada comments fallback failed: {exc!r}")
            return []
        return parse_comments_html(html, product_id=product_id)

    # ---------------------------------------------------------- menu

    async def fetch_menu(self, level: int = 3) -> list[Category]:
        all_seeded = parse_seed(LAZADA_MENU_SEED)
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
        url = (
            f"{self.API_BASE}/category"
            f"?q=&pageSize={page_size}&page={page}"
        )
        payload = self._get_json(url)
        if payload is not None:
            products = parse_products_json(payload)
            if products:
                return products
        logger.info("Lazada API path empty; Playwright fallback")
        return self._browser_fallback_products(category_url, page)

    # ------------------------------------------------------ comments

    async def fetch_comments(
        self,
        product_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Comment]:
        numeric = self._extract_product_id(product_id)
        if not numeric:
            return []
        url = (
            f"{self.BASE_URL}/pdp/review/getReviewsByProductId"
            f"?productId={numeric}&pageSize={page_size}&page={page}"
        )
        payload = self._get_json(url)
        if payload is not None:
            comments = parse_comments_json(payload, product_id=numeric)
            if comments:
                return comments
        logger.info("Lazada review API empty/blocked; Playwright fallback")
        return self._browser_fallback_comments(product_id, page)

    # ---------------------------------------------------------- search

    async def search(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Product]:
        url = (
            f"{self.API_BASE}/q"
            f"?q={keyword}&pageSize={page_size}&page={page}"
        )
        payload = self._get_json(url)
        if payload is None:
            return []
        return parse_products_json(payload)
