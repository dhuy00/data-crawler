"""`full` pipeline — menu -> products -> comments (single platform)."""

from __future__ import annotations

from pathlib import Path

from core.logger import logger

from .comments_from_products_pipeline import run_comments_from_products_pipeline
from .menu_pipeline import run_menu_pipeline
from .products_from_menu_pipeline import run_products_from_menu_pipeline


async def run_full_pipeline(
    platform_value: str = "tiki",
    output_dir: str | Path | None = None,
    fetch_comments: bool = True,
    limit_products: int | None = None,
) -> dict:
    """End-to-end: menu -> products -> comments.

    Each step writes to its own run-folder under `output_dir`.
    """
    base = Path(output_dir or "outputs")
    menu_res = await run_menu_pipeline(platform_value, output_dir=base)

    # Locate the menu CSV just written by the menu pipeline.
    menu_dir = base / f"{platform_value}_menu_{menu_res['run_id']}"
    csvs = list(menu_dir.glob("*.csv"))
    if not csvs:
        raise RuntimeError("Menu pipeline produced no CSV — cannot continue")
    menu_csv = max(csvs, key=lambda p: p.stat().st_mtime)

    prod_res = await run_products_from_menu_pipeline(
        input_file=menu_csv,
        platform_value=platform_value,
        output_dir=base,
        limit_per_level=limit_products,
    )

    comments_total = 0
    if fetch_comments:
        products_dir = base / f"{platform_value}_products_{prod_res['run_id']}"
        product_csvs = list(products_dir.glob("*.csv"))
        if product_csvs:
            # Concatenate all product CSVs into a temp file for the comments step.
            product_csv = max(product_csvs, key=lambda p: p.stat().st_mtime)
            cmt_res = await run_comments_from_products_pipeline(
                input_file=product_csv,
                platform_value=platform_value,
                output_dir=base,
                limit=limit_products,
            )
            comments_total = cmt_res.get("comment_count", 0)

    logger.info(
        f"[full] platform={platform_value} products={prod_res['product_count']} "
        f"comments={comments_total}"
    )
    return {
        "platform": platform_value,
        "categories": menu_res["count"],
        "product_count": prod_res["product_count"],
        "comment_count": comments_total,
    }
