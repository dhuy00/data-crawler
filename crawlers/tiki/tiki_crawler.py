"""Tiki implementation of `BaseCrawler`.

Behavior:
- `fetch_menu`: returns the static seed (Phase 1). A live refresh via
  `BrowserManager` is on the roadmap for Phase 2+.
- `fetch_products`: GETs the category HTML page, parses `__NEXT_DATA__`.
  Pagination is approximated by URL slug `?page=N` — Tiki's actual
  pagination is JS-driven and varies by category; consumers can pass
  explicit URLs to chain pages if needed.
- `fetch_comments`: GETs the product detail page and parses embedded reviews.
- `search`: GETs `/search?q=...&page=...` HTML and parses products.
"""

from __future__ import annotations

from typing import Optional

from core.http_client import HttpClient, RateLimiter
from core.logger import logger
from crawlers.base import BaseCrawler
from models import Category, Comment, Platform, Product
from services.platform_registry import register

from .comment_parser import parse_comments_html
from .keyword_parser import parse_search_html
from .menu_parser import parse_menu_html, parse_seed
from .menu_seed import TIKI_MENU_SEED
from .product_parser import parse_products_html


@register(Platform.TIKI)
class TikiCrawler(BaseCrawler):
    platform = Platform.TIKI
    comment_supported = True

    BASE_URL = "https://tiki.vn"

    def __init__(
        self,
        http_client: Optional[HttpClient] = None,
        rate_per_second: float = 1.5,
    ) -> None:
        super().__init__()
        self.http = http_client or HttpClient(
            rate_limiter=RateLimiter(requests_per_second=rate_per_second),
        )

    # ------------------------------------------------------ helpers

    def _get_html(self, url: str) -> str:
        logger.debug(f"Tiki GET {url}")
        return self.http.get(url).text

    # ---------------------------------------------------------- menu

    async def fetch_menu(self, level: int = 3) -> list[Category]:
        """Return categories up to `level` from the static seed.

        Phase 2+ will replace this with a live DOM scrape via Playwright.
        """
        all_seeded = parse_seed(TIKI_MENU_SEED)
        if level >= 3:
            return all_seeded
        return [c for c in all_seeded if c.level <= level]

    async def refresh_menu_from_page(self, page_url: str) -> list[Category]:
        """Optionally enrich the seed with breadcrumb info from a live page."""
        try:
            html = self._get_html(page_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"refresh_menu_from_page failed: {exc!r}")
            return []
        return parse_menu_html(html, page_url=page_url)

    # ------------------------------------------------------ products

    async def fetch_products(
        self,
        category_url: str,
        page: int = 1,
        page_size: int = 20,  # noqa: ARG002 — currently unused; kept for interface symmetry
    ) -> list[Product]:
        url = category_url
        if page > 1:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}page={page}"
        html = self._get_html(url)
        return parse_products_html(html)

    # ------------------------------------------------------ comments

    async def fetch_comments(
        self,
        product_id: str,
        page: int = 1,
        page_size: int = 20,  # noqa: ARG002
    ) -> list[Comment]:
        url = f"{self.BASE_URL}/p/{product_id}"
        if page > 1:
            url = f"{url}?page={page}"
        html = self._get_html(url)
        return parse_comments_html(html, product_id=product_id)

    # ---------------------------------------------------------- search

    async def search(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,  # noqa: ARG002
    ) -> list[Product]:
        url = f"{self.BASE_URL}/search"
        params = f"q={keyword}&page={page}"
        html = self._get_html(f"{url}?{params}")
        return parse_search_html(html)
