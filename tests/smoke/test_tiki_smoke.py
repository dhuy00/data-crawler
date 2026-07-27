"""Smoke tests that hit the live Tiki site.

Skipped unless `RUN_NETWORK_TESTS=1` is set in the environment. These
tests are intentionally lightweight: 1 page, 1 category, no Playwright.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from crawlers.tiki.tiki_crawler import TikiCrawler
from models import Platform

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_NETWORK_TESTS") != "1",
    reason="Set RUN_NETWORK_TESTS=1 to run live-network smoke tests",
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_tiki_search_smoke():
    c = TikiCrawler()
    products = _run(c.search("iphone"))
    # Don't assert exact count — Tiki changes layout — just sanity.
    assert all(p.platform is Platform.TIKI for p in products)
    if products:
        p = products[0]
        assert p.product_id and p.name


def test_tiki_menu_smoke():
    c = TikiCrawler()
    cats = _run(c.fetch_menu(level=1))
    assert len(cats) > 0
    assert all(cat.platform is Platform.TIKI for cat in cats)
