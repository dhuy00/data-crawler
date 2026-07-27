"""
Full pipeline: menu -> products -> comments
"""
import asyncio
from core.logger import logger
from crawlers import run_menu_crawler, run_product_crawler, run_comment_crawler
from services import CategoryService, ProductService, CommentService, RankingService
from config.settings import settings
from core.storage import DataStorage


from typing import Optional


async def full_pipeline(
    headless: bool = settings.BROWSER_HEADLESS,
    output_dir: Optional[str] = None,
):
    logger.info("Starting full pipeline: menu -> products -> comments")
    target_output_dir = output_dir or settings.RAW_OUTPUT_DIR

    # Menu crawl
    categories = await run_menu_crawler(headless=headless)
    cat_results = CategoryService.save_categories(
        categories,
        target_output_dir,
        filename=settings.MENU_OUTPUT_FILE,
        formats=[settings.MENU_OUTPUT_FORMAT],
    )

    # Convert to list of dicts for product crawler
    categories_dicts = [c.dict() for c in categories]

    # Products
    products = run_product_crawler(categories_dicts)
    ProductService.save_products(
        products,
        target_output_dir,
        filename=settings.PRODUCT_OUTPUT_FILE,
        formats=[settings.PRODUCT_OUTPUT_FORMAT],
    )

    # Comments
    comments = run_comment_crawler([p.dict() for p in products])
    CommentService.save_comments(
        comments,
        target_output_dir,
        filename=settings.COMMENT_OUTPUT_FILE,
        formats=[settings.COMMENT_OUTPUT_FORMAT],
    )

    logger.info("Full pipeline completed")


if __name__ == "__main__":
    asyncio.run(full_pipeline(headless=True))
