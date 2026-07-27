"""Tests for services/platform_registry.py and crawlers/base.py."""

from __future__ import annotations

import pytest

from crawlers.base import BaseCrawler
from models import Platform
from services.platform_registry import PlatformRegistry, register


class FakeCrawler(BaseCrawler):
    platform = Platform.TIKI
    comment_supported = True

    async def fetch_menu(self, level=3):
        return []

    async def fetch_products(self, category_url, page=1, page_size=20):
        return []

    async def search(self, keyword, page=1, page_size=20):
        return []


class NoCommentCrawler(BaseCrawler):
    platform = Platform.LAZADA
    comment_supported = False

    async def fetch_menu(self, level=3):
        return []

    async def fetch_products(self, category_url, page=1, page_size=20):
        return []

    async def search(self, keyword, page=1, page_size=20):
        return []


def test_register_decorator_wires_crawler():
    reg = PlatformRegistry()

    @register_with_registry(reg, Platform.TIKI)
    class TikiFake(FakeCrawler):
        pass

    assert Platform.TIKI in reg
    crawler = reg.get(Platform.TIKI)
    assert isinstance(crawler, FakeCrawler)


def test_registry_get_missing_raises():
    reg = PlatformRegistry()
    with pytest.raises(LookupError):
        reg.get(Platform.SHOPEE)


def test_base_crawler_fetch_comments_default():
    """Default BaseCrawler.fetch_comments raises when supported is True."""
    crawler = FakeCrawler()
    assert crawler.supports_comments() is True

    import asyncio
    with pytest.raises(NotImplementedError):
        asyncio.run(crawler.fetch_comments("P1"))


def test_base_crawler_comments_disabled_returns_empty():
    crawler = NoCommentCrawler()

    import asyncio
    result = asyncio.run(crawler.fetch_comments("P1"))
    assert result == []


def test_base_crawler_describe():
    crawler = FakeCrawler()
    info = crawler.describe()
    assert info["platform"] == "tiki"
    assert info["class"] == "FakeCrawler"


# --- helper ---------------------------------------------------------


def register_with_registry(reg: PlatformRegistry, platform: Platform):
    """Test-only decorator: same as services.platform_registry.register
    but bound to a specific registry instance so tests don't pollute the
    process-wide registry singleton.
    """
    def _wrap(cls):
        reg.register(platform, cls)
        return cls
    return _wrap
