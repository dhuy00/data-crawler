"""
Products from Menu pipeline: crawl products from existing menu/category file
"""
import os
from pathlib import Path
from typing import Optional
from core.logger import logger
from crawlers import run_product_crawler
from services import CategoryService, ProductService
from config.settings import settings


def products_from_menu_pipeline(
    input_file: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    """
    Execute product crawling pipeline from existing category CSV/Parquet file.
    
    Args:
        input_file: Path to category file (defaults to outputs/tiki_menu_3_levels.csv)
        output_dir: Output directory for product results (defaults to outputs/)
    """
    logger.info("Starting products_from_menu pipeline")
    target_output_dir = output_dir or settings.RAW_OUTPUT_DIR

    # Resolve default input file if not provided
    if not input_file:
        default_path = Path(settings.RAW_OUTPUT_DIR) / f"{settings.MENU_OUTPUT_FILE}.csv"
        if not default_path.exists():
            # Check for alternative extensions
            for ext in [".parquet", ".xlsx"]:
                alt_path = Path(settings.RAW_OUTPUT_DIR) / f"{settings.MENU_OUTPUT_FILE}{ext}"
                if alt_path.exists():
                    default_path = alt_path
                    break
        input_file = str(default_path)

    if not Path(input_file).exists():
        logger.error(f"Input category file not found: {input_file}")
        raise FileNotFoundError(f"Category file not found: {input_file}")

    logger.info(f"Loading categories from: {input_file}")
    categories = CategoryService.load_categories(input_file)
    logger.info(f"Loaded {len(categories)} categories")

    categories_dicts = [c.dict() for c in categories]

    # Crawl products
    products = run_product_crawler(categories_dicts)
    
    # Save products
    ProductService.save_products(
        products,
        target_output_dir,
        filename=settings.PRODUCT_OUTPUT_FILE,
        formats=[settings.PRODUCT_OUTPUT_FORMAT],
    )

    logger.info(f"products_from_menu pipeline completed. Total products: {len(products)}")
    return products


if __name__ == "__main__":
    products_from_menu_pipeline()
