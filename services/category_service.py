"""
Category service for managing category data.
"""
import pandas as pd
from typing import List, Dict, Optional
from core.logger import logger
from core.storage import DataStorage
from models import CategoryModel
from config.settings import settings


class CategoryService:
    """Manages category data operations."""

    @staticmethod
    def categories_to_dataframe(categories: List[CategoryModel]) -> pd.DataFrame:
        """
        Convert category models to DataFrame.
        
        Args:
            categories: List of category models
            
        Returns:
            DataFrame with category data
        """
        logger.info(f"Converting {len(categories)} categories to DataFrame")
        
        data = [cat.dict() for cat in categories]
        df = pd.DataFrame(data)
        
        logger.info(f"Created DataFrame with shape: {df.shape}")
        return df

    @staticmethod
    def save_categories(
        categories: List[CategoryModel],
        output_dir: str,
        filename: str = "tiki_categories",
        formats: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Save categories to files with automatic deduplication.
        
        Args:
            categories: List of category models
            output_dir: Output directory
            filename: Output filename
            formats: Export formats
            
        Returns:
            Export results
        """
        if formats is None:
            formats = [settings.MENU_OUTPUT_FORMAT]
        
        # Automatic deduplication before saving
        categories = CategoryService.deduplicate_categories(categories)
        
        logger.info(f"Saving {len(categories)} unique categories")
        
        df = CategoryService.categories_to_dataframe(categories)
        
        results = DataStorage.export_dataframe(
            df,
            output_dir,
            filename,
            formats,
        )
        
        logger.info(f"Categories saved: {results}")
        return results

    @staticmethod
    def load_categories(file_path: str) -> List[CategoryModel]:
        """
        Load categories from file.
        
        Args:
            file_path: Path to category file
            
        Returns:
            List of category models
        """
        logger.info(f"Loading categories from {file_path}")
        
        df = DataStorage.load_dataframe(file_path)
        
        categories = []
        for _, row in df.iterrows():
            row_dict = {}
            for k, v in row.to_dict().items():
                if pd.notna(v):
                    if k == "category_id" and isinstance(v, (float, int)):
                        row_dict[k] = str(int(v))
                    else:
                        row_dict[k] = str(v) if not isinstance(v, (str, dict, list)) else v
            categories.append(CategoryModel(**row_dict))
        
        # Deduplicate loaded categories
        categories = CategoryService.deduplicate_categories(categories)
        
        logger.info(f"Loaded {len(categories)} unique categories")
        return categories

    @staticmethod
    def deduplicate_categories(
        categories: List[CategoryModel],
    ) -> List[CategoryModel]:
        """
        Get unique categories by category_id or category_url.
        
        Args:
            categories: List of categories
            
        Returns:
            List of unique categories
        """
        logger.info(f"Deduplicating {len(categories)} categories")
        
        seen = set()
        unique = []
        
        for cat in categories:
            key = str(cat.category_id).strip() if cat.category_id else (cat.category_url or "").strip().lower()
            if not key:
                key = (
                    (cat.lv1_name or "").strip().lower(),
                    (cat.lv2_name or "").strip().lower(),
                    (cat.lv3_name or "").strip().lower(),
                )
            
            if key not in seen:
                seen.add(key)
                unique.append(cat)
        
        logger.info(f"Unique categories: {len(unique)} (removed {len(categories) - len(unique)} duplicates)")
        return unique

    @staticmethod
    def get_unique_categories(
        categories: List[CategoryModel],
    ) -> List[CategoryModel]:
        """Alias for deduplicate_categories."""
        return CategoryService.deduplicate_categories(categories)

    @staticmethod
    def get_categories_by_level(
        categories: List[CategoryModel],
        level: int = 1,
    ) -> List[CategoryModel]:
        """
        Get categories by level (1, 2, or 3).
        
        Args:
            categories: List of categories
            level: Category level (1-3)
            
        Returns:
            Filtered categories
        """
        if level == 1:
            filtered = [c for c in categories if c.lv1_name and not c.lv2_name]
        elif level == 2:
            filtered = [c for c in categories if c.lv2_name and not c.lv3_name]
        elif level == 3:
            filtered = [c for c in categories if c.lv3_name]
        else:
            filtered = categories
        
        logger.info(f"Level {level}: {len(filtered)} categories")
        return filtered
