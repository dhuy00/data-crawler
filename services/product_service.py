"""
Product service for managing product data.
"""
import pandas as pd
from typing import List, Dict, Optional
from core.logger import logger
from core.storage import DataStorage
from models import ProductModel
from config.settings import settings
from config.constants import PRODUCT_DEDUP_KEYS


class ProductService:
    """Manages product data operations."""

    @staticmethod
    def products_to_dataframe(products: List[ProductModel]) -> pd.DataFrame:
        """
        Convert product models to DataFrame.
        
        Args:
            products: List of product models
            
        Returns:
            DataFrame with product data
        """
        logger.info(f"Converting {len(products)} products to DataFrame")
        
        data = [prod.dict() for prod in products]
        df = pd.DataFrame(data)
        
        logger.info(f"Created DataFrame with shape: {df.shape}")
        return df

    @staticmethod
    def save_products(
        products: List[ProductModel],
        output_dir: str,
        filename: str = "tiki_products",
        formats: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Save products to files.
        
        Args:
            products: List of product models
            output_dir: Output directory
            filename: Output filename
            formats: Export formats
            
        Returns:
            Export results
        """
        if formats is None:
            formats = [settings.PRODUCT_OUTPUT_FORMAT]
        
        logger.info(f"Saving {len(products)} products")
        
        df = ProductService.products_to_dataframe(products)
        
        results = DataStorage.export_dataframe(
            df,
            output_dir,
            filename,
            formats,
        )
        
        logger.info(f"Products saved: {results}")
        return results

    @staticmethod
    def load_products(file_path: str) -> List[ProductModel]:
        """
        Load products from file.
        
        Args:
            file_path: Path to product file
            
        Returns:
            List of product models
        """
        logger.info(f"Loading products from {file_path}")
        
        df = DataStorage.load_dataframe(file_path)
        
        products = [
            ProductModel(**{k: v for k, v in row.to_dict().items() if pd.notna(v)})
            for _, row in df.iterrows()
        ]
        
        logger.info(f"Loaded {len(products)} products")
        return products

    @staticmethod
    def deduplicate_products(
        products: List[ProductModel],
    ) -> List[ProductModel]:
        """
        Remove duplicate products.
        
        Args:
            products: List of products
            
        Returns:
            Deduplicated products
        """
        logger.info(f"Deduplicating {len(products)} products")
        
        seen = set()
        unique = []
        
        for prod in products:
            key = (prod.category_id, prod.product_id, prod.seller_product_id)
            key_str = "_".join(str(x) for x in key)
            
            if key_str not in seen:
                seen.add(key_str)
                unique.append(prod)
        
        logger.info(f"Unique products: {len(unique)} (removed {len(products) - len(unique)})")
        return unique

    @staticmethod
    def filter_by_rating(
        products: List[ProductModel],
        min_rating: float = 0.0,
        max_rating: float = 5.0,
    ) -> List[ProductModel]:
        """
        Filter products by rating.
        
        Args:
            products: List of products
            min_rating: Minimum rating
            max_rating: Maximum rating
            
        Returns:
            Filtered products
        """
        filtered = [
            p for p in products
            if p.rating_average is not None and min_rating <= p.rating_average <= max_rating
        ]
        logger.info(f"Filtered {len(filtered)} products by rating {min_rating}-{max_rating}")
        return filtered

    @staticmethod
    def filter_by_reviews(
        products: List[ProductModel],
        min_reviews: int = 0,
        max_reviews: Optional[int] = None,
    ) -> List[ProductModel]:
        """
        Filter products by review count.
        
        Args:
            products: List of products
            min_reviews: Minimum reviews
            max_reviews: Maximum reviews
            
        Returns:
            Filtered products
        """
        filtered = [
            p for p in products
            if p.review_count >= min_reviews and (max_reviews is None or p.review_count <= max_reviews)
        ]
        logger.info(f"Filtered {len(filtered)} products by reviews {min_reviews}-{max_reviews}")
        return filtered

    @staticmethod
    def filter_by_category(
        products: List[ProductModel],
        category_ids: List[str],
    ) -> List[ProductModel]:
        """
        Filter products by category.
        
        Args:
            products: List of products
            category_ids: List of category IDs
            
        Returns:
            Filtered products
        """
        filtered = [p for p in products if p.category_id in category_ids]
        logger.info(f"Filtered {len(filtered)} products by categories {category_ids}")
        return filtered

    @staticmethod
    def get_products_by_category(
        products: List[ProductModel],
    ) -> Dict[str, List[ProductModel]]:
        """
        Group products by category.
        
        Args:
            products: List of products
            
        Returns:
            Dictionary mapping category to products
        """
        categories = {}
        for prod in products:
            category_key = prod.category_id or "unknown"
            if category_key not in categories:
                categories[category_key] = []
            categories[category_key].append(prod)
        
        logger.info(f"Grouped {len(products)} products into {len(categories)} categories")
        return categories
