"""
Menu -> Products pipeline: menu -> products
"""
import asyncio
from typing import Optional
from core.logger import logger
from crawlers import run_menu_crawler, run_product_crawler
from services import CategoryService, ProductService
from config.settings import settings


async def menu_products_pipeline(
    headless: bool = settings.BROWSER_HEADLESS,
    output_dir: Optional[str] = None,
):
    """
    Execute menu to products crawling pipeline.
    
    Args:
        headless: Run browser in headless mode
        output_dir: Output directory for results (defaults to settings.RAW_OUTPUT_DIR)
    """
    logger.info("Starting menu -> products pipeline")
    target_output_dir = output_dir or settings.RAW_OUTPUT_DIR

    # Menu crawl
    categories = await run_menu_crawler(headless=headless)
    CategoryService.save_categories(
        categories,
        target_output_dir,
        filename=settings.MENU_OUTPUT_FILE,
        formats=[settings.MENU_OUTPUT_FORMAT],
    )

    # Convert to list of dicts for product crawler
    categories_dicts = [c.dict() for c in categories]

    # Products crawl
    products = run_product_crawler(categories_dicts)
    ProductService.save_products(
        products,
        target_output_dir,
        filename=settings.PRODUCT_OUTPUT_FILE,
        formats=[settings.PRODUCT_OUTPUT_FORMAT],
    )

    logger.info("Menu -> products pipeline completed")
    return products


if __name__ == "__main__":
    asyncio.run(menu_products_pipeline(headless=True))
