"""
Comment/Review crawler for Tiki products.

Crawls product reviews with pagination and metadata enrichment.
Implements strict validation to filter out garbage data.
"""
import math
import re
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime
from tqdm import tqdm
from core.logger import logger
from core.http_client import HTTPClient
from core.comment_validator import CommentValidator, get_comment_quality_report
from models import CommentModel
from config.settings import settings
from config.constants import DEFAULT_COMMENT_PAGE_SIZE, REVIEW_API_PARAMS


class CommentCrawler:
    """Crawls comments/reviews for products."""

    def __init__(
        self,
        max_products: Optional[int] = None,
        max_pages_per_product: Optional[int] = None,
        limit_per_page: int = DEFAULT_COMMENT_PAGE_SIZE,
    ):
        """
        Initialize comment crawler.
        
        Args:
            max_products: Maximum products to crawl (None = all)
            max_pages_per_product: Maximum pages per product (None = all)
            limit_per_page: Comments per page
        """
        self.max_products = max_products or settings.COMMENT_MAX_PRODUCTS
        self.max_pages_per_product = max_pages_per_product or settings.COMMENT_MAX_PAGES
        self.limit_per_page = limit_per_page
        self.http_client = HTTPClient()
        self.comments: List[CommentModel] = []
        self.comment_ids_seen: Set[str] = set()
        
        # Quality tracking
        self.total_comments_processed = 0
        self.valid_comments_count = 0
        self.skipped_reasons: Dict[str, int] = {
            'validation_failed': 0,
            'content_validation_failed': 0,
            'seller_response': 0,
            'duplicate': 0,
            'normalization_error': 0,
        }

    def _fetch_review_page(
        self,
        product_id: str,
        seller_product_id: Optional[str],
        page: int,
    ) -> Dict:
        """
        Fetch review page from API.
        
        Args:
            product_id: Product ID
            seller_product_id: Seller product ID (optional)
            page: Page number
            
        Returns:
            API response JSON
        """
        params = {
            **REVIEW_API_PARAMS,
            "limit": self.limit_per_page,
            "page": page,
            "product_id": int(product_id),
        }
        
        if seller_product_id and str(seller_product_id).strip():
            try:
                params["spid"] = int(float(seller_product_id))
            except (ValueError, TypeError):
                # Invalid seller product ID can be safely ignored for review fetching.
                pass
        
        try:
            response = self.http_client.get(
                settings.TIKI_REVIEW_API_URL,
                params=params,
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching reviews for product {product_id}, page {page}: {e}")
            return {}

    def _get_total_pages(
        self,
        payload: Dict,
        fallback_review_count: int,
    ) -> int:
        """
        Calculate total pages from API response.
        
        Args:
            payload: API response payload
            fallback_review_count: Fallback review count
            
        Returns:
            Total pages
        """
        paging = payload.get("paging") or {}
        
        for key in ["last_page", "total_pages"]:
            value = paging.get(key)
            if value:
                return int(value)
        
        total = paging.get("total") or fallback_review_count
        if not total:
            return 1
        
        return max(1, math.ceil(int(total) / self.limit_per_page))

    def _normalize_comment(
        self,
        comment: Dict,
        product_row: Dict,
        page: int,
        position: int,
    ) -> Optional[CommentModel]:
        """
        Normalize raw comment data to model.
        
        Implements strict validation to skip low-quality comments.
        
        Args:
            comment: Raw comment data
            product_row: Product row data
            page: Page number
            position: Position in page
            
        Returns:
            Normalized comment model or None if invalid
        """
        self.total_comments_processed += 1
        
        # First validation pass: structure and required fields
        is_valid, error_msg = CommentValidator.validate_raw_comment(comment)
        if not is_valid:
            logger.debug(f"Comment validation failed: {error_msg}")
            self.skipped_reasons['validation_failed'] += 1
            return None
        
        # Extract and sanitize text fields
        title = CommentValidator.sanitize_comment_text(comment.get('title'))
        content = CommentValidator.sanitize_comment_text(comment.get('content'))
        
        # Second validation pass: content quality
        is_valid, error_msg = CommentValidator.validate_comment_content(title, content)
        if not is_valid:
            logger.debug(f"Comment content validation failed: {error_msg}")
            self.skipped_reasons['content_validation_failed'] += 1
            return None
        
        # Check if it's a seller response
        if CommentValidator.is_seller_response(content, title):
            logger.debug("Filtering out seller response")
            self.skipped_reasons['seller_response'] += 1
            return None
        
        # Build comment model with clean data
        try:
            created_by = comment.get("created_by") or {}
            seller = comment.get("seller") or {}
            timeline = comment.get("timeline") or {}
            
            # Parse creation date if present
            created_at = None
            created_at_str = comment.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                except Exception:
                    # Some review timestamps are not ISO-formatted; keep created_at as None.
                    pass
            
            model = CommentModel(
                product_id=str(product_row.get("product_id")),
                seller_product_id=product_row.get("seller_product_id"),
                product_name=product_row.get("product_name"),
                product_url=product_row.get("product_url"),
                category_id=product_row.get("category_id"),
                category_url=product_row.get("category_url"),
                lv1_name=product_row.get("lv1_name"),
                lv2_name=product_row.get("lv2_name"),
                lv3_name=product_row.get("lv3_name"),
                product_review_count=product_row.get("review_count", 0),
                product_rating_average=product_row.get("rating_average"),
                comment_page=page,
                comment_position=position,
                comment_id=str(comment.get("id")),
                customer_id=created_by.get("id"),
                customer_name=created_by.get("name"),
                customer_full_name=created_by.get("full_name"),
                customer_region=created_by.get("region"),
                customer_avatar_url=created_by.get("avatar_url"),
                rating=comment.get("rating"),
                title=title,
                content=content,
                thank_count=comment.get("thank_count", 0),
                score=comment.get("score"),
                status=comment.get("status"),
                is_photo=comment.get("is_photo", False),
                seller_id=seller.get("id"),
                seller_name=seller.get("name"),
                created_at=created_at,
                created_at_text=timeline.get("review_created_date"),
                purchased_at=timeline.get("purchased_at"),
            )
            self.valid_comments_count += 1
            return model
        
        except Exception as e:
            logger.debug(f"Error normalizing comment: {e}")
            self.skipped_reasons['normalization_error'] += 1
            return None

    def _add_comment(self, comment: Optional[CommentModel]) -> bool:
        """
        Add comment with deduplication.
        
        Args:
            comment: Comment model (can be None if validation failed)
            
        Returns:
            True if added, False if duplicate or None
        """
        if comment is None:
            return False
        
        if comment.comment_id in self.comment_ids_seen:
            self.skipped_reasons['duplicate'] += 1
            return False
        
        self.comment_ids_seen.add(comment.comment_id)
        self.comments.append(comment)
        return True

    def crawl_product(
        self,
        product_row: Dict,
    ) -> int:
        """
        Crawl all comments for a product.
        
        Args:
            product_row: Product row data
            
        Returns:
            Number of comments crawled
        """
        product_id = str(product_row.get("product_id"))
        seller_product_id = product_row.get("seller_product_id")
        product_name = product_row.get("product_name", "Unknown")
        review_count = int(product_row.get("review_count", 0))
        
        # Skip products with no reviews
        if review_count == 0:
            logger.debug(f"Product {product_id} has no reviews, skipping")
            return 0
        
        logger.info(f"Crawling reviews for {product_name} (ID: {product_id}, Expected: {review_count})")
        
        comments_count = 0
        page = 1
        max_pages_reached = False
        
        while not max_pages_reached:
            response = self._fetch_review_page(product_id, seller_product_id, page)
            
            if not response or "data" not in response:
                logger.debug(f"No review data for product {product_id}, page {page}")
                break
            
            comments = response.get("data", [])
            
            if not comments:
                logger.debug(f"Empty review page {page} for product {product_id}")
                break
            
            # Process comments
            for position, comment in enumerate(comments, 1):
                try:
                    normalized = self._normalize_comment(
                        comment,
                        product_row,
                        page,
                        position,
                    )
                    
                    if self._add_comment(normalized):
                        comments_count += 1
                
                except Exception as e:
                    logger.warning(f"Error processing comment: {e}")
                    self.skipped_reasons['normalization_error'] += 1
                    continue
            
            # Calculate total pages
            total_pages = self._get_total_pages(response, review_count)
            
            if page >= total_pages:
                max_pages_reached = True
            
            if self.max_pages_per_product and page >= self.max_pages_per_product:
                max_pages_reached = True
            
            page += 1
            logger.debug(f"Product {product_id}: {comments_count} comments, page {page-1}/{total_pages}")
        
        logger.info(f"Product {product_id}: {comments_count} reviews")
        return comments_count

    def crawl_products(self, products: List[Dict]) -> List[CommentModel]:
        """
        Crawl comments for multiple products.
        
        Args:
            products: List of product rows
            
        Returns:
            List of comments
        """
        logger.info(f"Starting comment crawl for {len(products)} products")
        
        # Filter products with reviews
        products_with_reviews = [
            p for p in products
            if int(p.get("review_count", 0)) > 0
        ]
        
        logger.info(f"Found {len(products_with_reviews)} products with reviews")
        
        products_to_crawl = products_with_reviews
        if self.max_products:
            products_to_crawl = products_with_reviews[:self.max_products]
            logger.info(f"Limited to {len(products_to_crawl)} products")
        
        total_comments = 0
        
        for idx, product in enumerate(tqdm(products_to_crawl, desc="Products"), 1):
            try:
                count = self.crawl_product(product)
                total_comments += count
                
                # Checkpoint save
                if idx % settings.COMMENT_SAVE_EVERY_N_PRODUCTS == 0:
                    logger.info(f"Checkpoint at product {idx}: {total_comments} comments total")
            
            except Exception as e:
                logger.error(f"Error crawling product: {e}")
                continue
        
        logger.info(f"Comment crawl completed. Total comments: {len(self.comments)}")
        
        # Generate and log quality report
        report = get_comment_quality_report(
            self.total_comments_processed,
            self.valid_comments_count,
            self.skipped_reasons,
        )
        
        return self.comments

    def close(self) -> None:
        """Close HTTP client."""
        self.http_client.close()
        logger.info("Comment crawler closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def run_comment_crawler(
    products: List[Dict],
    max_products: Optional[int] = None,
    max_pages_per_product: Optional[int] = None,
) -> List[CommentModel]:
    """
    Convenience function to run comment crawler.
    
    Args:
        products: List of product data
        max_products: Maximum products
        max_pages_per_product: Maximum pages per product
        
    Returns:
        List of comments
    """
    with CommentCrawler(max_products, max_pages_per_product) as crawler:
        return crawler.crawl_products(products)
