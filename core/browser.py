"""Playwright async browser manager.

A small wrapper that lazily creates a single browser instance per process
and exposes a context manager for pages. Crawlers that need JS rendering
get a `page` and are responsible for closing it.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .logger import logger


class BrowserManager:
    """Lazy, single-browser manager for Playwright.

    Usage:
        async with BrowserManager(headless=True) as bm:
            page = await bm.new_page()
            ...
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser: Browser | None = None

    async def __aenter__(self) -> "BrowserManager":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        logger.info(f"Playwright browser started (headless={self.headless})")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._browser is not None:
            await self._browser.close()
        if self._playwright is not None:
            await self._playwright.stop()
        logger.info("Playwright browser closed")

    @asynccontextmanager
    async def new_page(self) -> AsyncIterator[Page]:
        """Yield a new page inside a fresh context. Caller closes the context."""
        if self._browser is None:
            raise RuntimeError("BrowserManager must be used as an async context manager")
        context: BrowserContext = await self._browser.new_context()
        try:
            page = await context.new_page()
            try:
                yield page
            finally:
                await page.close()
        finally:
            await context.close()
