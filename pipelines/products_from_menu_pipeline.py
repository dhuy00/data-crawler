"""`products_from_menu` — read a menu CSV/JSONL, crawl products per category."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from core import Storage
from core.logger import logger
from services.platform_registry import get_registry


async def run_products_from_menu_pipeline(
    input_file: str | Path,
    platform_value: str = "tiki",
    output_dir: str | Path | None = None,
    max_pages: int = 1,
    limit_per_level: int | None = None,
) -> dict:
    """Read categories from `input_file`, crawl products per category.

    `input_file` is a CSV (or JSONL) produced by `menu` pipeline; rows
    containing the leaf-level categories (level >= 2 by default) are crawled.

    Args:
        input_file: CSV/JSONL file produced by the menu pipeline.
        platform_value: platform key (default "tiki").
        output_dir: where to save results.
        max_pages: how many pages to crawl per category (Tiki uses page=1 only).
        limit_per_level: for debugging, cap number of categories crawled.
    """
    from models import Platform

    platform = Platform.parse(platform_value)
    crawler = get_registry().get(platform)

    input_path = Path(input_file)
    if input_path.suffix.lower() == ".csv":
        df = pd.read_csv(input_path)
        records = df.to_dict("records")
    else:
        with input_path.open("r", encoding="utf-8") as fh:
            records = [json.loads(line) for line in fh if line.strip()]

    # Filter to URL-bearing rows — prefer leaf-level categories.
    cats = [r for r in records if r.get("url") and (not limit_per_level or 1)]
    if limit_per_level is not None:
        cats = cats[:limit_per_level]

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        Path(output_dir or "outputs")
        / f"{platform.value}_products_{run_id}"
    )
    storage = Storage(output_dir, run_id=run_id)

    storage.record_run({
        "run_id": run_id,
        "mode": "products_from_menu",
        "platforms": [platform.value],
        "category": None,
        "keywords": [],
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
        "product_count": 0,
        "comment_count": 0,
        "output_dir": str(output_dir),
    })

    total = 0
    for i, c in enumerate(cats, start=1):
        url = c["url"]
        logger.info(
            f"[products] ({i}/{len(cats)}) {c.get('name', url)} "
            f"-> {url}"
        )
        try:
            products = await crawler.fetch_products(url, page=1)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Skipping {url}: {exc!r}")
            continue
        total += storage.save_products(
            products, file_tag=f"products_{c.get('category_id', i)}"
        )

    storage.record_run({
        "run_id": run_id,
        "mode": "products_from_menu",
        "platforms": [platform.value],
        "category": None,
        "keywords": [],
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
        "product_count": total,
        "comment_count": 0,
        "output_dir": str(output_dir),
    })
    logger.info(f"[products] total saved: {total}")
    return {"platform": platform.value, "product_count": total, "run_id": run_id}
