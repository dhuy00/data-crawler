"""
Main entrypoint for Tiki crawling framework.

Provides simple CLI usage for crawling menu, products, comments, or searching by keyword.
"""
import argparse
import asyncio
import sys
from core.logger import logger
from pipelines import (
    full_pipeline,
    keyword_pipeline,
    menu_pipeline,
    menu_products_pipeline,
    products_from_menu_pipeline,
    comments_from_products_pipeline,
)


def parse_args():
    parser = argparse.ArgumentParser(description="Tiki Crawling Framework")
    parser.add_argument(
        "--mode",
        type=str,
        default="full",
        help=(
            "Pipeline mode: full | menu | 'menu -> products' (or menu_products) | "
            "products_from_menu | comments_from_products | keyword"
        ),
    )
    parser.add_argument("--headless", action="store_true", help="Run browsers headless")
    parser.add_argument("--keywords", type=str, help="Comma-separated keywords for keyword mode")
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="Input CSV/Parquet file path for products_from_menu or comments_from_products mode",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory to save output files (defaults to outputs/)",
    )
    return parser.parse_args()


def normalize_mode(mode: str) -> str:
    """Normalize mode input string to standard mode key."""
    if not mode:
        return ""
    
    cleaned = mode.strip().lower()
    
    if cleaned in ["menu"]:
        return "menu"
    elif cleaned in [
        "menu -> products",
        "menu->products",
        "menu_products",
        "menu-products",
        "menu_to_products",
        "menu to products",
    ]:
        return "menu_products"
    elif cleaned in [
        "products_from_menu",
        "products-from-menu",
        "products_menu",
        "products from menu",
    ]:
        return "products_from_menu"
    elif cleaned in [
        "comments_from_products",
        "comments-from-products",
        "comments_products",
        "comments from products",
    ]:
        return "comments_from_products"
    elif cleaned in ["full"]:
        return "full"
    elif cleaned in ["keyword"]:
        return "keyword"
    
    return cleaned


def main():
    args = parse_args()
    mode = normalize_mode(args.mode)
    output_dir = args.output_dir
    input_file = args.input_file

    try:
        if mode == "menu":
            logger.info("Running mode: menu")
            asyncio.run(menu_pipeline(headless=args.headless, output_dir=output_dir))

        elif mode == "menu_products":
            logger.info("Running mode: menu -> products")
            asyncio.run(menu_products_pipeline(headless=args.headless, output_dir=output_dir))

        elif mode == "products_from_menu":
            logger.info("Running mode: products_from_menu")
            products_from_menu_pipeline(input_file=input_file, output_dir=output_dir)

        elif mode == "comments_from_products":
            logger.info("Running mode: comments_from_products")
            comments_from_products_pipeline(input_file=input_file, output_dir=output_dir)

        elif mode == "full":
            logger.info("Running mode: full (menu -> products -> comments)")
            asyncio.run(full_pipeline(headless=args.headless, output_dir=output_dir))

        elif mode == "keyword":
            if not args.keywords:
                logger.error("Provide --keywords for keyword mode")
                sys.exit(1)
            
            keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
            if not keywords:
                logger.error("No valid keywords provided")
                sys.exit(1)
            
            logger.info(f"Starting keyword pipeline with keywords: {keywords}")
            keyword_pipeline(keywords, output_dir=output_dir)

        else:
            logger.error(f"Unknown mode: {args.mode}")
            logger.error(
                "Supported modes: menu | 'menu -> products' | products_from_menu | "
                "comments_from_products | full | keyword"
            )
            sys.exit(1)

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
