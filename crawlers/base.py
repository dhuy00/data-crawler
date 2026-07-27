"""BaseCrawler — abstract interface every platform crawler must implement.

Pipeline code talks only to this interface. Concrete crawlers live under
`crawlers/<platform>/` and are wired into the `PlatformRegistry` via the
`@register` decorator from `services.platform_registry`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from models.base_models import Category, Comment, Product
from models.platform import Platform


class BaseCrawler(ABC):
    """Contract every per-platform crawler must satisfy.

    Implementations should:
    - Be stateless across calls (the pipeline owns state).
    - Apply per-host rate limiting via their own `HttpClient` / `BrowserManager`.
    - Return empty lists (not raise) when a page legitimately has no data.
    - Raise only on transient failures the pipeline should retry/abort on.
    """

    #: Class attribute: which platform this crawler serves.
    platform: Platform

    #: Class attribute: whether comments are fetchable from this platform.
    comment_supported: bool = True

    def __init__(self, *args, **kwargs) -> None:
        # Subclasses can accept extra config (headless, http_client, etc.)
        # but the base does not require anything.
        pass

    # -------------------------------------------------------------- menu

    @abstractmethod
    async def fetch_menu(self, level: int = 3) -> list[Category]:
        """Return categories at `level` (1=top, 2=mid, 3=leaf).

        Implementations may return categories from all levels when called
        with `level=3`; the pipeline filters as needed.
        """

    # ---------------------------------------------------------- products

    @abstractmethod
    async def fetch_products(
        self,
        category_url: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Product]:
        """Return products for a given category URL at a given page."""

    # ---------------------------------------------------------- comments

    async def fetch_comments(
        self,
        product_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Comment]:
        """Return comments for a product. Default raises if unsupported.

        Concrete crawlers on platforms without a public comment endpoint
        should set `comment_supported = False` and inherit this default.
        """
        if not self.comment_supported:
            return []
        raise NotImplementedError(
            f"{type(self).__name__} must implement fetch_comments "
            f"or set comment_supported = False"
        )

    # ---------------------------------------------------------- search

    @abstractmethod
    async def search(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Product]:
        """Search products by keyword, return a page of results."""

    # ---------------------------------------------------- convenience

    def supports_comments(self) -> bool:
        return bool(self.comment_supported)

    def describe(self) -> dict[str, Optional[str]]:
        """Return a short dict for logging."""
        return {
            "platform": self.platform.value,
            "comment_supported": str(self.comment_supported),
            "class": type(self).__name__,
        }
