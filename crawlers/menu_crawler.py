"""
Menu/Category crawler using Playwright & HTTP API.

Crawls Tiki category hierarchy (3 levels) with deduplication, fast API acceleration, and filtering.
"""
import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urljoin
from tqdm import tqdm
from core.logger import logger
from core.browser import PlaywrightBrowser
from core.http_client import HTTPClient
from models import CategoryModel
from config.settings import settings
from config.constants import (
    MENU_LEVEL_1_XPATH,
    MENU_LEVEL_2_3_XPATH,
    CATEGORY_MIN_NAME_LENGTH,
    CATEGORY_MAX_NAME_LENGTH,
    CATEGORY_REQUIRED_PATH_SEGMENT,
    CATEGORY_EXCLUDE_PARAMS,
    CATEGORY_LOAD_DELAY,
    SUBCATEGORY_LOAD_DELAY,
)


class MenuCrawler:
    """Crawls Tiki category hierarchy (3 levels) efficiently."""

    def __init__(self, headless: bool = settings.BROWSER_HEADLESS):
        """
        Initialize menu crawler.
        
        Args:
            headless: Run browser in headless mode
        """
        self.headless = headless
        self.browser: Optional[PlaywrightBrowser] = None
        self.http_client: Optional[HTTPClient] = None
        self.categories: List[CategoryModel] = []
        self.global_seen: Set[Tuple[str, str, str]] = set()

    async def initialize(self) -> None:
        """Initialize browser and HTTP client."""
        self.browser = PlaywrightBrowser()
        await self.browser.launch(headless=self.headless)
        self.http_client = HTTPClient()
        logger.info("Menu crawler initialized")

    async def close(self) -> None:
        """Close browser and HTTP client."""
        if self.browser:
            await self.browser.close()
        if self.http_client:
            self.http_client.close()
        logger.info("Menu crawler closed")

    @staticmethod
    def _is_valid_category_name(name: str) -> bool:
        """Validate category name."""
        if not name:
            return False
        if len(name) < CATEGORY_MIN_NAME_LENGTH or len(name) > CATEGORY_MAX_NAME_LENGTH:
            return False
        return True

    @staticmethod
    def _is_valid_category_url(url: str) -> bool:
        """Validate category URL."""
        if not url:
            return False
        if CATEGORY_REQUIRED_PATH_SEGMENT not in url:
            return False
        for param in CATEGORY_EXCLUDE_PARAMS:
            if param in url:
                return False
        return True

    @staticmethod
    def _extract_category_id(url: str) -> Optional[str]:
        """Extract category ID from URL."""
        if not url:
            return None
        try:
            match = re.search(r"/c(\d+)", str(url))
            if match:
                return match.group(1)
        except Exception as e:
            logger.warning(f"Error extracting category ID from {url}: {e}")
        return None

    def _fetch_subcategories_api(self, category_id: str) -> List[Dict[str, str]]:
        """
        Fetch subcategories for a given category ID using Tiki API.
        
        Args:
            category_id: Parent category ID
            
        Returns:
            List of subcategory dicts with name, category_id, and url
        """
        if not category_id:
            return []
        
        params = {
            "limit": 1,
            "category": category_id,
            "page": 1,
            "aggregations": 2,
            "version": "mweb-v2",
        }
        
        try:
            response = self.http_client.get(
                settings.TIKI_PRODUCT_API_URL,
                params=params,
            )
            if response.status_code == 200:
                data = response.json()
                subcategories = []
                
                for f in data.get("filters", []):
                    if f.get("query_name") == "category":
                        for v in f.get("values", []):
                            cat_id = str(v.get("query_value"))
                            url_path = v.get("url_path", "")
                            
                            name = v.get("display_value") or v.get("name")
                            if not name and url_path:
                                raw_name = url_path.split("/c")[0].strip("/")
                                name = raw_name.replace("-", " ").title()
                            
                            if not name or not url_path:
                                continue
                            
                            full_url = urljoin(settings.TIKI_BASE_URL, url_path)
                            
                            if self._is_valid_category_name(name) and self._is_valid_category_url(full_url):
                                subcategories.append({
                                    "name": name.strip(),
                                    "category_id": cat_id,
                                    "url": full_url,
                                })
                
                return subcategories
        except Exception as e:
            logger.debug(f"API subcategory fetch failed for category {category_id}: {e}")
        
        return []

    async def crawl_level_1(self) -> List[Dict[str, str]]:
        """
        Crawl level 1 categories using Playwright.
        
        Returns:
            List of level 1 category data
        """
        logger.info("Starting level 1 category crawl")
        
        context = await self.browser.create_context()
        page = await self.browser.create_page(context)
        
        try:
            await self.browser.goto_with_retry(
                page,
                settings.TIKI_MENU_URL,
                wait_until="domcontentloaded",
            )
            
            await page.wait_for_timeout(int(CATEGORY_LOAD_DELAY * 1000))
            
            lv1_elements = await page.locator(MENU_LEVEL_1_XPATH).all()
            logger.info(f"Found {len(lv1_elements)} raw level 1 category elements")
            
            level_1_data = []
            lv1_visited: Set[str] = set()
            
            for element in lv1_elements:
                try:
                    name = (await element.text_content()).strip()
                    url = await element.get_attribute("href")
                    if url and not url.startswith("http"):
                        url = urljoin(settings.TIKI_BASE_URL, url)
                    
                    if not self._is_valid_category_name(name) or not self._is_valid_category_url(url):
                        continue
                    
                    if url in lv1_visited:
                        continue
                    
                    cat_id = self._extract_category_id(url)
                    
                    lv1_visited.add(url)
                    level_1_data.append({
                        "lv1_name": name,
                        "lv1_url": url,
                        "category_id": cat_id,
                    })
                
                except Exception as e:
                    logger.warning(f"Error extracting level 1 category: {e}")
                    continue
            
            logger.info(f"Extracted {len(level_1_data)} valid level 1 categories")
            return level_1_data
        
        finally:
            await page.close()
            await context.close()


    async def crawl_level_2_3(self, level_1_data: List[Dict[str, str]]) -> None:
        """
        Crawl level 2 and 3 categories using fast API with Playwright fallback.
        
        Args:
            level_1_data: Level 1 category data
        """
        logger.info(f"Starting level 2/3 crawl for {len(level_1_data)} level 1 categories")
        
        for lv1_row in tqdm(level_1_data, desc="Crawling Categories"):
            lv1_name = lv1_row["lv1_name"]
            lv1_url = lv1_row["lv1_url"]
            lv1_id = lv1_row.get("category_id") or self._extract_category_id(lv1_url)
            
            # Record level 1 category
            self._add_category(
                lv1_name, lv1_url,
                None, None,
                None, None,
            )
            
            if not lv1_id:
                continue
            
            # Fast API fetch for Level 2
            lv2_items = self._fetch_subcategories_api(lv1_id)
            
            if lv2_items:
                valid_lv2_items = []
                for lv2 in lv2_items:
                    lv2_name = lv2["name"]
                    lv2_url = lv2["url"]
                    
                    if lv2_url == lv1_url or lv2_name == lv1_name:
                        continue
                    
                    valid_lv2_items.append(lv2)
                    
                    # Record level 2 category
                    self._add_category(
                        lv1_name, lv1_url,
                        lv2_name, lv2_url,
                        None, None,
                    )
                
                # Parallel API fetch for Level 3 subcategories
                if valid_lv2_items:
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = [
                            executor.submit(self._fetch_subcategories_api, lv2["category_id"])
                            for lv2 in valid_lv2_items
                        ]
                        
                        for lv2, future in zip(valid_lv2_items, futures):
                            lv2_name = lv2["name"]
                            lv2_url = lv2["url"]
                            try:
                                lv3_items = future.result()
                                for lv3 in lv3_items:
                                    lv3_name = lv3["name"]
                                    lv3_url = lv3["url"]
                                    
                                    if (
                                        lv3_url == lv2_url
                                        or lv3_url == lv1_url
                                        or lv3_name == lv2_name
                                        or lv3_name == lv1_name
                                    ):
                                        continue
                                    
                                    # Record level 3 category
                                    self._add_category(
                                        lv1_name, lv1_url,
                                        lv2_name, lv2_url,
                                        lv3_name, lv3_url,
                                    )
                            except Exception as e:
                                logger.debug(f"Error fetching L3 for {lv2_name}: {e}")
            else:
                # Fallback to Playwright DOM extraction if API returns no subcategories
                await self._fallback_playwright_level_2_3(lv1_name, lv1_url)

    async def _fallback_playwright_level_2_3(self, lv1_name: str, lv1_url: str) -> None:
        """Fallback to Playwright for level 2 & 3 if API returns empty."""
        context = await self.browser.create_context()
        page = await self.browser.create_page(context)
        
        try:
            success = await self.browser.goto_with_retry(
                page,
                lv1_url,
                wait_until="domcontentloaded",
            )
            if not success:
                return
            
            await page.wait_for_timeout(int(SUBCATEGORY_LOAD_DELAY * 1000))
            
            lv2_elements = await page.locator(MENU_LEVEL_2_3_XPATH).all()
            for lv2_elem in lv2_elements:
                try:
                    lv2_name = (await lv2_elem.text_content()).strip()
                    lv2_url = await lv2_elem.get_attribute("href")
                    if lv2_url and not lv2_url.startswith("http"):
                        lv2_url = urljoin(settings.TIKI_BASE_URL, lv2_url)
                    
                    if not self._is_valid_category_name(lv2_name) or not self._is_valid_category_url(lv2_url):
                        continue
                    
                    if lv2_url == lv1_url or lv2_name == lv1_name:
                        continue
                    
                    self._add_category(
                        lv1_name, lv1_url,
                        lv2_name, lv2_url,
                        None, None,
                    )
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Fallback Playwright failed for {lv1_name}: {e}")
        finally:
            await page.close()
            await context.close()

    def _add_category(
        self,
        lv1_name: str,
        lv1_url: str,
        lv2_name: Optional[str],
        lv2_url: Optional[str],
        lv3_name: Optional[str],
        lv3_url: Optional[str],
    ) -> None:
        """Add category with deduplication by category_id or URL."""
        category_url = lv3_url or lv2_url or lv1_url
        category_id = self._extract_category_id(category_url)
        
        dedup_key = category_id or (category_url.strip().lower() if category_url else None) or (lv1_name, lv2_name or "", lv3_name or "")
        
        if dedup_key in self.global_seen:
            return
        
        self.global_seen.add(dedup_key)
        
        category = CategoryModel(
            lv1_name=lv1_name,
            lv1_url=lv1_url,
            lv2_name=lv2_name,
            lv2_url=lv2_url,
            lv3_name=lv3_name,
            lv3_url=lv3_url,
            category_id=category_id,
            category_url=category_url,
        )
        
        self.categories.append(category)

    async def crawl(self) -> List[CategoryModel]:
        """
        Execute full menu crawl.
        
        Returns:
            List of crawled categories
        """
        try:
            await self.initialize()
            
            # Level 1
            level_1_data = await self.crawl_level_1()
            
            # Level 2 + 3
            await self.crawl_level_2_3(level_1_data)
            
            logger.info(f"Menu crawl completed. Total categories: {len(self.categories)}")
            return self.categories
        
        finally:
            await self.close()


async def run_menu_crawler(headless: bool = settings.BROWSER_HEADLESS) -> List[CategoryModel]:
    """
    Convenience function to run menu crawler.
    
    Args:
        headless: Run in headless mode
        
    Returns:
        List of categories
    """
    crawler = MenuCrawler(headless=headless)
    return await crawler.crawl()


if __name__ == "__main__":
    categories = asyncio.run(run_menu_crawler(headless=True))
    logger.info(f"Total categories crawled: {len(categories)}")
    for cat in categories[:5]:
        logger.info(cat.dict())
