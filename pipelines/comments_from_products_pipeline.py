"""
Comments from Products pipeline: crawl comments from existing product file
"""
import os
from pathlib import Path
from typing import Optional
from core.logger import logger
from crawlers import run_comment_crawler
from services import ProductService, CommentService
from config.settings import settings


def comments_from_products_pipeline(
    input_file: Optional[str] = None,
    output_dir: Optional[str] = None,
):
    """
    Execute comment crawling pipeline from existing products CSV/Parquet file.
    
    Args:
        input_file: Path to product file (defaults to outputs/tiki_products.csv)
        output_dir: Output directory for comment results (defaults to outputs/)
    """
    logger.info("Starting comments_from_products pipeline")
    target_output_dir = output_dir or settings.RAW_OUTPUT_DIR

    # Resolve default input file if not provided
    if not input_file:
        default_path = Path(settings.RAW_OUTPUT_DIR) / f"{settings.PRODUCT_OUTPUT_FILE}.csv"
        if not default_path.exists():
            for ext in [".parquet", ".xlsx"]:
                alt_path = Path(settings.RAW_OUTPUT_DIR) / f"{settings.PRODUCT_OUTPUT_FILE}{ext}"
                if alt_path.exists():
                    default_path = alt_path
                    break
        input_file = str(default_path)

    if not Path(input_file).exists():
        logger.error(f"Input product file not found: {input_file}")
        raise FileNotFoundError(f"Product file not found: {input_file}")

    logger.info(f"Loading products from: {input_file}")
    products = ProductService.load_products(input_file)
    logger.info(f"Loaded {len(products)} products")

    products_dicts = [p.dict() for p in products]

    # Crawl comments
    comments = run_comment_crawler(products_dicts)
    
    # Validate and deduplicate comments
    comments, _ = CommentService.validate_comments(comments)
    comments = CommentService.deduplicate_comments(comments)

    # Save comments
    CommentService.save_comments(
        comments,
        target_output_dir,
        filename=settings.COMMENT_OUTPUT_FILE,
        formats=[settings.COMMENT_OUTPUT_FORMAT],
    )

    logger.info(f"comments_from_products pipeline completed. Total comments: {len(comments)}")
    return comments


if __name__ == "__main__":
    comments_from_products_pipeline()
