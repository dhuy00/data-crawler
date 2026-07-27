"""
Keyword search crawler for Tiki.

Crawls products by keyword search.
"""
from typing import List, Dict, Optional
from tqdm import tqdm
from core.logger import logger
from core.http_client import HTTPClient
from models import ProductModel
from config.settings import settings
from config.constants import DEFAULT_PRODUCT_PAGE_SIZE, SEARCH_API_PARAMS


class KeywordCrawler:
    """Crawls products by keyword search."""

    def __init__(
        self,
        max_products: Optional[int] = None,
        limit_per_page: int = DEFAULT_PRODUCT_PAGE_SIZE,
    ):
        """
        Initialize keyword crawler.
        
        Args:
            max_products: Maximum products to crawl
            limit_per_page: Products per page
        """
        self.max_products = max_products or settings.KEYWORD_MAX_PRODUCTS
        self.limit_per_page = limit_per_page
        self.http_client = HTTPClient()
        self.products: List[ProductModel] = []

    def _search_products(
        self,
        keyword: str,
        page: int,
    ) -> Dict:
        """
        Search products by keyword.
        
        Args:
            keyword: Search keyword
            page: Page number
            
        Returns:
            API response JSON
        """
        params = {
            **SEARCH_API_PARAMS,
            "limit": self.limit_per_page,
            "page": page,
            "q": keyword,
        }
        
        try:
            response = self.http_client.get(
                settings.TIKI_SEARCH_API_URL,
                params=params,
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error searching for keyword '{keyword}', page {page}: {e}")
            return {}

    def _normalize_search_product(
        self,
        product: Dict,
        keyword: str,
        page: int,
        position: int,
    ) -> ProductModel:
        """Normalize search result to product model."""
        quantity_sold = product.get("quantity_sold")
        quantity_sold_text, quantity_sold_value = None, None
        
        if isinstance(quantity_sold, dict):
            quantity_sold_text = quantity_sold.get("text")
            quantity_sold_value = quantity_sold.get("value")
        
        url_path = product.get("url_path") or product.get("url")
        product_url = f"{settings.TIKI_BASE_URL}/{url_path}" if url_path else None
        
        seller_product_id = product.get("seller_product_id")
        if seller_product_id is not None:
            seller_product_id = str(seller_product_id)

        return ProductModel(
            lv1_name=f"Search: {keyword}",
            category_id="search",
            category_url=None,
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

    def search_keyword(self, keyword: str) -> List[ProductModel]:
        """
        Search products for a keyword.
        
        Args:
            keyword: Search keyword
            
        Returns:
            List of products
        """
        logger.info(f"Searching for keyword: {keyword}")
        
        products_count = 0
        page = 1
        max_pages_reached = False
        
        while not max_pages_reached and products_count < self.max_products:
            response = self._search_products(keyword, page)
            
            if not response or "data" not in response:
                logger.debug(f"No data for keyword '{keyword}', page {page}")
                break
            
            products = response.get("data", [])
            
            if not products:
                logger.debug(f"Empty page {page} for keyword '{keyword}'")
                break
            
            # Process products
            for position, product in enumerate(products, 1):
                if products_count >= self.max_products:
                    max_pages_reached = True
                    break
                
                try:
                    normalized = self._normalize_search_product(
                        product,
                        keyword,
                        page,
                        position,
                    )
                    self.products.append(normalized)
                    products_count += 1
                
                except Exception as e:
                    logger.warning(f"Error normalizing search product: {e}")
                    continue
            
            # Check if more pages
            paging = response.get("paging", {})
            if not paging.get("has_next", False):
                max_pages_reached = True
            
            page += 1
            logger.debug(f"Keyword '{keyword}': {products_count} products, page {page-1}")
        
        logger.info(f"Keyword '{keyword}': {products_count} products")
        return self.products

    def search_keywords(self, keywords: List[str]) -> List[ProductModel]:
        """
        Search multiple keywords.
        
        Args:
            keywords: List of keywords
            
        Returns:
            Combined list of products
        """
        logger.info(f"Starting keyword search for {len(keywords)} keywords")
        
        all_products = []
        seen_product_ids = set()
        
        for keyword in tqdm(keywords, desc="Keywords"):
            try:
                self.products = []  # Reset for each keyword
                products = self.search_keyword(keyword)
                
                # Add unique products
                for product in products:
                    product_key = (product.product_id, product.seller_product_id)
                    if product_key not in seen_product_ids:
                        seen_product_ids.add(product_key)
                        all_products.append(product)
            
            except Exception as e:
                logger.error(f"Error searching keyword '{keyword}': {e}")
                continue
        
        logger.info(f"Keyword search completed. Total unique products: {len(all_products)}")
        return all_products

    def close(self) -> None:
        """Close HTTP client."""
        self.http_client.close()
        logger.info("Keyword crawler closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def run_keyword_crawler(
    keywords: List[str],
    max_products: Optional[int] = None,
) -> List[ProductModel]:
    """
    Convenience function to run keyword crawler.
    
    Args:
        keywords: List of keywords
        max_products: Maximum products per keyword
        
    Returns:
        List of products
    """
    with KeywordCrawler(max_products) as crawler:
        return crawler.search_keywords(keywords)
