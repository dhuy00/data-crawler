"""CLI entrypoint for the data-crawler framework.

Phase 1: single-platform pipelines (default Tiki).
Phase 5: multi-platform mode (`--platforms a,b,c`).
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from core.logger import logger
from pipelines.comments_from_products_pipeline import run_comments_from_products_pipeline
from pipelines.full_pipeline import run_full_pipeline
from pipelines.keyword_pipeline import run_keyword_pipeline
from pipelines.menu_pipeline import run_menu_pipeline
from pipelines.products_from_menu_pipeline import run_products_from_menu_pipeline

# Importing the crawlers package triggers each crawler module's
# `@register(...)` decorator, populating the platform registry.
import crawlers  # noqa: F401
import crawlers.tiki  # noqa: F401  (Phase 1 ships Tiki; later phases add others)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Multi-platform Vietnamese e-commerce crawler"
    )
    p.add_argument(
        "--mode",
        default="menu",
        choices=["menu", "products_from_menu", "comments_from_products",
                 "keyword", "full"],
        help="Pipeline mode to run.",
    )
    p.add_argument(
        "--platform",
        default="tiki",
        help="Platform key (tiki, shopee, lazada, sendo). Phase 5: --platforms a,b,c for multi.",
    )
    p.add_argument("--platforms", default=None,
                   help="Comma-separated list of platforms (Phase 5).")
    p.add_argument("--output-dir", default=None,
                   help="Output directory (default: outputs/).")
    p.add_argument("--input-file", default=None,
                   help="Input CSV/JSONL (for products_from_menu / comments_from_products).")
    p.add_argument("--keywords", default=None,
                   help="Comma-separated keywords for --mode keyword.")
    p.add_argument("--limit", type=int, default=None,
                   help="Limit number of categories/products crawled.")
    p.add_argument("--max-pages", type=int, default=1,
                   help="Max pages per category.")
    p.add_argument("--no-comments", action="store_true",
                   help="Skip comment crawl in `full` and `keyword` modes.")
    p.add_argument("--max-products-per-keyword", type=int, default=10,
                   help="Top N products to fetch comments for in keyword mode.")
    p.add_argument("--level", type=int, default=3,
                   help="Max menu depth for `menu` mode.")
    return p.parse_args()


async def _dispatch(args: argparse.Namespace) -> dict:
    if args.platforms:
        logger.warning(
            "--platforms is a Phase 5 feature; falling back to first platform only"
        )
        platform_value = args.platforms.split(",")[0].strip()
    else:
        platform_value = args.platform

    mode = args.mode
    out = args.output_dir

    if mode == "menu":
        return await run_menu_pipeline(
            platform_value=platform_value,
            output_dir=out,
            level=args.level,
        )
    if mode == "products_from_menu":
        if not args.input_file:
            raise SystemExit("--input-file is required for products_from_menu")
        return await run_products_from_menu_pipeline(
            input_file=args.input_file,
            platform_value=platform_value,
            output_dir=out,
            max_pages=args.max_pages,
            limit_per_level=args.limit,
        )
    if mode == "comments_from_products":
        if not args.input_file:
            raise SystemExit("--input-file is required for comments_from_products")
        return await run_comments_from_products_pipeline(
            input_file=args.input_file,
            platform_value=platform_value,
            output_dir=out,
            limit=args.limit,
        )
    if mode == "keyword":
        if not args.keywords:
            raise SystemExit("--keywords is required for keyword mode")
        kw_list = [k.strip() for k in args.keywords.split(",") if k.strip()]
        return await run_keyword_pipeline(
            keywords=kw_list,
            platform_value=platform_value,
            output_dir=out,
            fetch_comments=not args.no_comments,
            max_products_per_keyword=args.max_products_per_keyword,
        )
    if mode == "full":
        return await run_full_pipeline(
            platform_value=platform_value,
            output_dir=out,
            fetch_comments=not args.no_comments,
            limit_products=args.limit,
        )
    raise SystemExit(f"Unknown mode: {mode}")


def main() -> None:
    args = parse_args()
    try:
        result = asyncio.run(_dispatch(args))
        logger.info(f"Result: {result}")
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Pipeline failed: {exc!r}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
