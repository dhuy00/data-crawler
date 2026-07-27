"""
Comment service for managing comment/review data.

Provides validation, filtering, and aggregation services for comments.
"""
import pandas as pd
from typing import List, Dict, Optional, Tuple
from core.logger import logger
from core.storage import DataStorage
from core.comment_validator import CommentValidator
from models import CommentModel
from config.settings import settings


class CommentService:
    """Manages comment data operations."""

    @staticmethod
    def comments_to_dataframe(comments: List[CommentModel]) -> pd.DataFrame:
        """
        Convert comment models to DataFrame.
        
        Args:
            comments: List of comment models
            
        Returns:
            DataFrame with comment data
        """
        logger.info(f"Converting {len(comments)} comments to DataFrame")
        
        data = [comment.dict() for comment in comments]
        df = pd.DataFrame(data)
        
        logger.info(f"Created DataFrame with shape: {df.shape}")
        return df

    @staticmethod
    def save_comments(
        comments: List[CommentModel],
        output_dir: str,
        filename: str = "tiki_comments",
        formats: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Save comments to files.
        
        Args:
            comments: List of comment models
            output_dir: Output directory
            filename: Output filename
            formats: Export formats
            
        Returns:
            Export results
        """
        if formats is None:
            formats = [settings.COMMENT_OUTPUT_FORMAT]
        
        logger.info(f"Saving {len(comments)} comments")
        
        df = CommentService.comments_to_dataframe(comments)
        
        results = DataStorage.export_dataframe(
            df,
            output_dir,
            filename,
            formats,
        )
        
        logger.info(f"Comments saved: {results}")
        return results

    @staticmethod
    def validate_comments(
        comments: List[CommentModel],
    ) -> Tuple[List[CommentModel], Dict[str, int]]:
        """
        Validate comments and filter out low-quality ones.
        
        Args:
            comments: List of comment models
            
        Returns:
            Tuple of (valid_comments, skip_counts_by_reason)
        """
        logger.info(f"Validating {len(comments)} comments")
        
        valid_comments = []
        skip_counts = {
            'empty_content': 0,
            'seller_response': 0,
            'spam_detected': 0,
        }
        
        for comment in comments:
            # Check for empty content
            if not comment.content and not comment.title:
                skip_counts['empty_content'] += 1
                continue
            
            # Check if seller response
            if CommentValidator.is_seller_response(comment.content, comment.title):
                skip_counts['seller_response'] += 1
                continue
            
            # Check for spam
            is_spam_title, _ = CommentValidator._check_spam_pattern(comment.title or "")
            is_spam_content, _ = CommentValidator._check_spam_pattern(comment.content or "")
            if is_spam_title or is_spam_content:
                skip_counts['spam_detected'] += 1
                continue
            
            valid_comments.append(comment)
        
        logger.info(f"Validation complete: {len(valid_comments)} valid, {len(comments) - len(valid_comments)} filtered")
        for reason, count in skip_counts.items():
            if count > 0:
                logger.debug(f"  - {reason}: {count}")
        
        return valid_comments, skip_counts

    @staticmethod
    def deduplicate_comments(
        comments: List[CommentModel],
    ) -> List[CommentModel]:
        """
        Remove duplicate comments by ID.
        
        Args:
            comments: List of comment models
            
        Returns:
            Deduplicated comments
        """
        logger.info(f"Deduplicating {len(comments)} comments")
        
        seen = set()
        unique = []
        
        for comment in comments:
            if comment.comment_id not in seen:
                seen.add(comment.comment_id)
                unique.append(comment)
        
        removed = len(comments) - len(unique)
        if removed > 0:
            logger.info(f"Removed {removed} duplicate comments")
        
        return unique

    @staticmethod
    def load_comments(file_path: str) -> List[CommentModel]:
        """
        Load comments from file.
        
        Args:
            file_path: Path to comment file
            
        Returns:
            List of comment models
        """
        logger.info(f"Loading comments from {file_path}")
        
        df = DataStorage.load_dataframe(file_path)
        
        comments = [
            CommentModel(**{k: v for k, v in row.to_dict().items() if pd.notna(v)})
            for _, row in df.iterrows()
        ]
        
        logger.info(f"Loaded {len(comments)} comments")
        return comments

    @staticmethod
    def filter_by_rating(
        comments: List[CommentModel],
        min_rating: int = 1,
        max_rating: int = 5,
    ) -> List[CommentModel]:
        """
        Filter comments by rating.
        
        Args:
            comments: List of comments
            min_rating: Minimum rating
            max_rating: Maximum rating
            
        Returns:
            Filtered comments
        """
        filtered = [
            c for c in comments
            if c.rating is not None and min_rating <= c.rating <= max_rating
        ]
        logger.info(f"Filtered {len(filtered)} comments by rating {min_rating}-{max_rating}")
        return filtered

    @staticmethod
    def filter_by_product(
        comments: List[CommentModel],
        product_ids: List[str],
    ) -> List[CommentModel]:
        """
        Filter comments by product.
        
        Args:
            comments: List of comments
            product_ids: List of product IDs
            
        Returns:
            Filtered comments
        """
        filtered = [c for c in comments if c.product_id in product_ids]
        logger.info(f"Filtered {len(filtered)} comments by products {product_ids}")
        return filtered

    @staticmethod
    def get_comments_by_product(
        comments: List[CommentModel],
    ) -> Dict[str, List[CommentModel]]:
        """
        Group comments by product.
        
        Args:
            comments: List of comments
            
        Returns:
            Dictionary mapping product_id to comments
        """
        products = {}
        for comment in comments:
            prod_id = comment.product_id
            if prod_id not in products:
                products[prod_id] = []
            products[prod_id].append(comment)
        
        logger.info(f"Grouped {len(comments)} comments into {len(products)} products")
        return products

    @staticmethod
    def get_comments_by_category(
        comments: List[CommentModel],
    ) -> Dict[str, List[CommentModel]]:
        """
        Group comments by category.
        
        Args:
            comments: List of comments
            
        Returns:
            Dictionary mapping category to comments
        """
        categories = {}
        for comment in comments:
            cat_id = comment.category_id or "unknown"
            if cat_id not in categories:
                categories[cat_id] = []
            categories[cat_id].append(comment)
        
        logger.info(f"Grouped {len(comments)} comments into {len(categories)} categories")
        return categories

    @staticmethod
    def calculate_aggregate_stats(
        comments: List[CommentModel],
    ) -> Dict:
        """
        Calculate aggregate statistics.
        
        Args:
            comments: List of comments
            
        Returns:
            Statistics dictionary
        """
        df = CommentService.comments_to_dataframe(comments)
        
        stats = {
            "total_comments": len(comments),
            "avg_rating": df["rating"].mean() if "rating" in df.columns else None,
            "total_products": df["product_id"].nunique() if "product_id" in df.columns else 0,
            "total_customers": df["customer_id"].nunique() if "customer_id" in df.columns else 0,
            "with_photos": len([c for c in comments if c.is_photo]),
        }
        
        logger.info(f"Aggregate stats: {stats}")
        return stats
