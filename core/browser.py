"""
Playwright browser manager with support for contexts, retries, and cleanup.

Provides a reusable browser automation interface.
"""
import random
from typing import Optional, Dict, Any
from urllib.parse import urljoin
from playwright.async_api import async_playwright, Browser, Page, BrowserContext
from core.logger import logger
from config.settings import settings


class PlaywrightBrowser:
    """Manages Playwright browser instances with automatic cleanup."""

    def __init__(self):
        """Initialize browser manager."""
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def launch(self, headless: bool = settings.BROWSER_HEADLESS) -> None:
        """
        Launch Playwright browser.
        
        Args:
            headless: Run in headless mode
        """
        logger.info(f"Launching Playwright browser (headless={headless})")
        
        self.playwright = await async_playwright().start()
        
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
            ],
        )
        
        logger.info("Browser launched successfully")

    async def create_context(self) -> BrowserContext:
        """
        Create a new browser context with rotation user agent.
        
        Returns:
            Browser context
        """
        user_agent = random.choice(settings.BROWSER_USER_AGENTS)
        
        self.context = await self.browser.new_context(
            viewport={
                "width": settings.BROWSER_VIEWPORT_WIDTH,
                "height": settings.BROWSER_VIEWPORT_HEIGHT,
            },
            user_agent=user_agent,
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
        )
        
        logger.debug(f"Browser context created with user-agent: {user_agent[:50]}...")
        return self.context

    async def create_page(self, context: Optional[BrowserContext] = None) -> Page:
        """
        Create a new page in context.
        
        Args:
            context: Browser context (creates new if not provided)
            
        Returns:
            Page instance
        """
        if context is None:
            context = await self.create_context()
        
        self.page = await context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(settings.BROWSER_TIMEOUT)
        self.page.set_default_navigation_timeout(settings.BROWSER_TIMEOUT)
        
        logger.debug("Page created successfully")
        return self.page

    async def goto_with_retry(
        self,
        page: Page,
        url: str,
        max_retries: int = 3,
        wait_until: str = "networkidle",
    ) -> bool:
        """
        Navigate to URL with retry logic.
        
        Args:
            page: Page instance
            url: Target URL
            max_retries: Maximum retry attempts
            wait_until: Wait condition (load, domcontentloaded, networkidle)
            
        Returns:
            True if successful, False otherwise
        """
        if url and not url.startswith(("http://", "https://")):
            url = urljoin(settings.TIKI_BASE_URL, url)
        for attempt in range(max_retries):
            try:
                logger.debug(f"Navigating to {url} (attempt {attempt + 1}/{max_retries})")
                await page.goto(url, wait_until=wait_until)
                logger.info(f"Successfully navigated to {url}")
                return True
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await page.wait_for_timeout(1000)
                continue
        
        logger.error(f"Failed to navigate to {url} after {max_retries} attempts")
        return False

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        try:
            if self.page:
                await self.page.close()
                logger.debug("Page closed")
            
            if self.context:
                await self.context.close()
                logger.debug("Context closed")
            
            if self.browser:
                await self.browser.close()
                logger.debug("Browser closed")
            
            if self.playwright:
                await self.playwright.stop()
                logger.debug("Playwright stopped")
            
            logger.info("Browser cleanup completed")
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.launch()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
