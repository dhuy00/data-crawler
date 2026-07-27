"""
Ranking service for products.

Implements weighted scoring and ranking algorithms.
"""
from typing import List, Dict, Optional
import pandas as pd
from core.logger import logger
from models import ProductModel
from config.settings import settings


class RankingService:
    """Provides product ranking and scoring services."""

    def __init__(
        self,
        weight_rating: float = settings.RANKING_WEIGHT_RATING,
        weight_reviews: float = settings.RANKING_WEIGHT_REVIEWS,
        weight_sold: float = settings.RANKING_WEIGHT_SOLD,
    ):
        """
        Initialize ranking service.
        
        Args:
            weight_rating: Weight for rating score (0-1)
            weight_reviews: Weight for review count (0-1)
            weight_sold: Weight for quantity sold (0-1)
        """
        total_weight = weight_rating + weight_reviews + weight_sold
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"Weights don't sum to 1.0: {total_weight}. Normalizing...")
        
        self.weight_rating = weight_rating
        self.weight_reviews = weight_reviews
        self.weight_sold = weight_sold

    def calculate_score(
        self,
        rating_average: Optional[float],
        review_count: int,
        quantity_sold: Optional[int],
    ) -> float:
        """
        Calculate weighted ranking score.
        
        Args:
            rating_average: Average rating (0-5)
            review_count: Number of reviews
            quantity_sold: Quantity sold
            
        Returns:
            Ranking score (0-100)
        """
        # Normalize rating to 0-100
        rating_score = (rating_average / 5.0 * 100) if rating_average else 0
        
        # Normalize review count (assume max 10000 reviews)
        review_score = min(review_count / 10000 * 100, 100)
        
        # Normalize quantity sold (assume max 100000 sold)
        sold_score = min((quantity_sold or 0) / 100000 * 100, 100)
        
        # Weighted sum
        total_score = (
            self.weight_rating * rating_score +
            self.weight_reviews * review_score +
            self.weight_sold * sold_score
        )
        
        return min(total_score, 100)

    def rank_products(
        self,
        products: List[ProductModel],
        ascending: bool = False,
    ) -> List[ProductModel]:
        """
        Rank products by weighted score.
        
        Args:
            products: List of products
            ascending: Sort ascending (default: descending)
            
        Returns:
            Ranked products
        """
        logger.info(f"Ranking {len(products)} products")
        
        # Handle empty product list
        if not products:
            logger.info("No products to rank")
            return []
        
        # Calculate scores
        scores = []
        for product in products:
            score = self.calculate_score(
                product.rating_average,
                product.review_count,
                product.quantity_sold_value,
            )
            scores.append(score)
        
        # Sort
        sorted_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=not ascending,
        )
        
        ranked_products = [products[i] for i in sorted_indices]
        
        logger.info(f"Ranking completed. Top product score: {scores[sorted_indices[0]]:.2f}")
        return ranked_products

    def get_top_n(
        self,
        products: List[ProductModel],
        n: int = 50,
    ) -> List[ProductModel]:
        """
        Get top N products by ranking score.
        
        Args:
            products: List of products
            n: Number of top products
            
        Returns:
            Top N products
        """
        ranked = self.rank_products(products)
        top_n = ranked[:n]
        logger.info(f"Selected top {len(top_n)} from {len(products)} products")
        return top_n

    def get_top_n_by_category(
        self,
        products: List[ProductModel],
        n: int = 50,
    ) -> Dict[str, List[ProductModel]]:
        """
        Get top N products per category.
        
        Args:
            products: List of products
            n: Number of top products per category
            
        Returns:
            Dictionary mapping category to top products
        """
        logger.info(f"Getting top {n} products per category")
        
        # Group by category
        categories = {}
        for product in products:
            category_key = product.category_id or "unknown"
            if category_key not in categories:
                categories[category_key] = []
            categories[category_key].append(product)
        
        # Get top N for each
        result = {}
        for category, category_products in categories.items():
            top_products = self.get_top_n(category_products, n)
            result[category] = top_products
            logger.debug(f"Category {category}: {len(top_products)} top products")
        
        logger.info(f"Completed: {len(result)} categories processed")
        return result
