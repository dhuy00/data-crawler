"""
Menu pipeline: crawl categories/menu hierarchy only.
"""
import asyncio
from typing import Optional
from core.logger import logger
from crawlers import run_menu_crawler
from services import CategoryService
from config.settings import settings


async def menu_pipeline(
    headless: bool = settings.BROWSER_HEADLESS,
    output_dir: Optional[str] = None,
):
    """
    Execute menu crawling pipeline.
    
    Args:
        headless: Run browser in headless mode
        output_dir: Output directory for results (defaults to settings.RAW_OUTPUT_DIR)
    """
    logger.info("Starting menu pipeline")
    target_output_dir = output_dir or settings.RAW_OUTPUT_DIR

    # Menu crawl
    categories = await run_menu_crawler(headless=headless)
    cat_results = CategoryService.save_categories(
        categories,
        target_output_dir,
        filename=settings.MENU_OUTPUT_FILE,
        formats=[settings.MENU_OUTPUT_FORMAT],
    )

    logger.info(f"Menu pipeline completed. Total categories: {len(categories)}")
    return categories


if __name__ == "__main__":
    asyncio.run(menu_pipeline(headless=True))
