"""Sendo implementation of `BaseCrawler`.

Strategy (Phase 4): use `api.sendo.vn/web/` directly. The endpoints
are the same ones the public site uses, so we get well-formed JSON.
Playwright fallback exists for the rare schema drift case.
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
from .menu_seed import SENDO_MENU_SEED
from .product_parser import parse_products_json


@register(Platform.SENDO)
class SendoCrawler(BaseCrawler):
    platform = Platform.SENDO
    comment_supported = True

    BASE_URL = "https://www.sendo.vn"
    API_BASE = "https://api.sendo.vn/web"

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
            logger.warning(f"Sendo GET {url}: not JSON, will Playwright fallback")
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Sendo GET {url} failed: {exc!r}")
            return None

    def _browser_fallback_products(self, category_url: str, page: int) -> list[Product]:
        try:
            with BrowserManager() as bm:
                bm.fetch_html(category_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Playwright Sendo products fallback failed: {exc!r}")
        return []

    def _browser_fallback_comments(
        self,
        product_id: str,
        page: int,
    ) -> list[Comment]:
        url = f"{self.BASE_URL}/product/{product_id}.htm"
        try:
            with BrowserManager() as bm:
                html = bm.fetch_html(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Playwright Sendo comments fallback failed: {exc!r}")
            return []
        return parse_comments_html(html, product_id=product_id)

    # ---------------------------------------------------------- menu

    async def fetch_menu(self, level: int = 3) -> list[Category]:
        all_seeded = parse_seed(SENDO_MENU_SEED)
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
        # Category-id-driven catalog endpoint
        url = (
            f"{self.API_BASE}/catalog/product/list"
            f"?page={page}&size={page_size}&sortType=desc"
        )
        payload = self._get_json(url)
        if payload is not None:
            products = parse_products_json(payload)
            if products:
                return products
        logger.info("Sendo API path empty; Playwright fallback")
        return self._browser_fallback_products(category_url, page)

    # ------------------------------------------------------ comments

    async def fetch_comments(
        self,
        product_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Comment]:
        url = (
            f"{self.API_BASE}/product/rating"
            f"?productId={product_id}&page={page}&size={page_size}"
        )
        payload = self._get_json(url)
        if payload is not None:
            comments = parse_comments_json(payload, product_id=product_id)
            if comments:
                return comments
        logger.info("Sendo rating API empty/blocked; Playwright fallback")
        return self._browser_fallback_comments(product_id, page)

    # ---------------------------------------------------------- search

    async def search(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Product]:
        url = (
            f"{self.API_BASE}/search-product"
            f"?q={keyword}&page={page}&size={page_size}"
        )
        payload = self._get_json(url)
        if payload is None:
            return []
        return parse_products_json(payload)
