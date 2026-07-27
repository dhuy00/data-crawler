"""
Product crawler for Tiki using HTTP API.

Crawls products from categories with pagination and ranking support.
"""
import re
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin
import pandas as pd
from tqdm import tqdm
from core.logger import logger
from core.http_client import HTTPClient
from models import ProductModel
from config.settings import settings
from config.constants import (
    DEFAULT_PRODUCT_PAGE_SIZE,
    PRODUCT_API_PARAMS,
    PRODUCT_DEDUP_KEYS,
)


class ProductCrawler:
    """Crawls products from Tiki categories using API."""

    def __init__(
        self,
        max_categories: Optional[int] = None,
        max_pages: Optional[int] = None,
        limit_per_page: int = DEFAULT_PRODUCT_PAGE_SIZE,
    ):
        """
        Initialize product crawler.
        
        Args:
            max_categories: Maximum categories to crawl (None = all)
            max_pages: Maximum pages per category (None = all)
            limit_per_page: Products per page
        """
        self.max_categories = max_categories or settings.PRODUCT_MAX_CATEGORIES
        self.max_pages = max_pages or settings.PRODUCT_MAX_PAGES
        self.limit_per_page = limit_per_page
        self.http_client = HTTPClient()
        self.products: List[ProductModel] = []
        self.product_ids_seen: Set[str] = set()

    def _extract_category_id(self, url: str) -> Optional[str]:
        """Extract category ID from URL."""
        try:
            match = re.search(r"/c(\d+)", str(url))
            if match:
                return match.group(1)
        except Exception as e:
            logger.warning(f"Error extracting category ID: {e}")
        
        return None

    def _fetch_product_page(
        self,
        category_id: str,
        page: int,
    ) -> Dict:
        """
        Fetch product page from API.
        
        Args:
            category_id: Category ID
            page: Page number
            
        Returns:
            API response JSON
        """
        params = {
            **PRODUCT_API_PARAMS,
            "limit": self.limit_per_page,
            "category": category_id,
            "page": page,
        }
        
        try:
            response = self.http_client.get(
                settings.TIKI_PRODUCT_API_URL,
                params=params,
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching page {page} for category {category_id}: {e}")
            return {}

    @staticmethod
    def _get_quantity_sold(product: Dict) -> tuple:
        """Extract quantity sold info."""
        quantity_sold = product.get("quantity_sold")
        
        if isinstance(quantity_sold, dict):
            return quantity_sold.get("text"), quantity_sold.get("value")
        
        return None, None

    def _normalize_product(
        self,
        product: Dict,
        category_row: Dict,
        page: int,
        position: int,
    ) -> ProductModel:
        """Normalize raw product data to model."""
        quantity_sold_text, quantity_sold_value = self._get_quantity_sold(product)
        url_path = product.get("url_path") or product.get("url")
        product_url = urljoin(settings.TIKI_BASE_URL, url_path) if url_path else None
        
        seller_product_id = product.get("seller_product_id")
        if seller_product_id is not None:
            seller_product_id = str(seller_product_id)

        return ProductModel(
            lv1_name=category_row.get("lv1_name"),
            lv1_url=category_row.get("lv1_url"),
            lv2_name=category_row.get("lv2_name"),
            lv2_url=category_row.get("lv2_url"),
            lv3_name=category_row.get("lv3_name"),
            lv3_url=category_row.get("lv3_url"),
            category_id=category_row.get("category_id"),
            category_url=category_row.get("category_url"),
            page=page,
            position=position,
            product_id=str(product.get("id")),
            seller_product_id=seller_product_id,
            sku=product.get("sku"),
            product_name=product.get("name"),
            product_url=product_url,
            brand_name=product.get("brand_name"),
            price=product.get("price"),
            list_price=product.get("list_price"),
            original_price=product.get("original_price"),
            discount=product.get("discount"),
            discount_rate=product.get("discount_rate"),
            rating_average=product.get("rating_average"),
            review_count=int(product.get("review_count", 0)),
            quantity_sold_text=quantity_sold_text,
            quantity_sold_value=quantity_sold_value,
            thumbnail_url=product.get("thumbnail_url"),
        )

    def _add_product(self, product: ProductModel) -> bool:
        """
        Add product with deduplication.
        
        Args:
            product: Product model
            
        Returns:
            True if added, False if duplicate
        """
        dedup_key = (
            product.category_id,
            product.product_id,
            product.seller_product_id,
        )
        dedup_key_str = "_".join(str(x) for x in dedup_key)
        
        if dedup_key_str in self.product_ids_seen:
            return False
        
        self.product_ids_seen.add(dedup_key_str)
        self.products.append(product)
        return True

    def crawl_category(
        self,
        category_row: Dict,
    ) -> int:
        """
        Crawl products from single category.
        
        Args:
            category_row: Category data
            
        Returns:
            Number of products crawled
        """
        category_id = category_row.get("category_id")
        category_name = category_row.get("lv3_name") or category_row.get("lv2_name") or category_row.get("lv1_name")
        
        logger.info(f"Crawling category: {category_name} (ID: {category_id})")
        
        products_count = 0
        page = 1
        max_pages_reached = False
        
        while not max_pages_reached:
            response = self._fetch_product_page(category_id, page)
            
            if not response or "data" not in response:
                logger.debug(f"No data for category {category_id}, page {page}")
                break
            
            products = response.get("data", [])
            
            if not products:
                logger.debug(f"Empty page {page} for category {category_id}")
                break
            
            # Process products
            for position, product in enumerate(products, 1):
                try:
                    normalized = self._normalize_product(
                        product,
                        category_row,
                        page,
                        position,
                    )
                    
                    if self._add_product(normalized):
                        products_count += 1
                
                except Exception as e:
                    logger.warning(f"Error normalizing product: {e}")
                    continue
            
            # Check if more pages
            paging = response.get("paging", {})
            if not paging.get("has_next", False):
                max_pages_reached = True
            
            if self.max_pages and page >= self.max_pages:
                max_pages_reached = True
            
            page += 1
            logger.debug(f"Crawled {products_count} products from {category_name}, page {page-1}")
        
        logger.info(f"Category {category_name}: {products_count} products")
        return products_count

    def crawl_categories(self, categories: List[Dict]) -> List[ProductModel]:
        """
        Crawl products from multiple categories.
        
        Args:
            categories: List of category data
            
        Returns:
            List of crawled products
        """
        logger.info(f"Starting product crawl for {len(categories)} categories")
        
        categories_to_crawl = categories
        if self.max_categories:
            categories_to_crawl = categories[:self.max_categories]
            logger.info(f"Limited to {len(categories_to_crawl)} categories")
        
        total_products = 0
        
        for idx, category in enumerate(tqdm(categories_to_crawl, desc="Categories"), 1):
            try:
                count = self.crawl_category(category)
                total_products += count
                
                # Checkpoint save
                if idx % settings.PRODUCT_SAVE_EVERY_N_CATEGORIES == 0:
                    logger.info(f"Checkpoint at category {idx}: {total_products} products total")
            
            except Exception as e:
                logger.error(f"Error crawling category: {e}")
                continue
        
        logger.info(f"Product crawl completed. Total products: {len(self.products)}")
        return self.products

    def close(self) -> None:
        """Close HTTP client."""
        self.http_client.close()
        logger.info("Product crawler closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def run_product_crawler(
    categories: List[Dict],
    max_categories: Optional[int] = None,
    max_pages: Optional[int] = None,
) -> List[ProductModel]:
    """
    Convenience function to run product crawler.
    
    Args:
        categories: List of category data
        max_categories: Maximum categories
        max_pages: Maximum pages per category
        
    Returns:
        List of products
    """
    with ProductCrawler(max_categories, max_pages) as crawler:
        return crawler.crawl_categories(categories)
