"""`comments_from_products` — read a products CSV, crawl comments per product."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from core import Storage
from core.logger import logger
from services.platform_registry import get_registry


async def run_comments_from_products_pipeline(
    input_file: str | Path,
    platform_value: str = "tiki",
    output_dir: str | Path | None = None,
    limit: int | None = None,
) -> dict:
    """Read a products CSV (from `products_from_menu`) and crawl comments.

    `input_file` must contain a `product_id` column.
    """
    from models import Platform

    platform = Platform.parse(platform_value)
    crawler = get_registry().get(platform)
    if not crawler.supports_comments():
        logger.warning(
            f"[comments] {platform.value} does not support public comments; skipping"
        )
        return {"platform": platform.value, "comment_count": 0, "run_id": None}

    df = pd.read_csv(input_file)
    if "product_id" not in df.columns:
        raise ValueError(f"{input_file} has no 'product_id' column")
    if limit:
        df = df.head(limit)

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        Path(output_dir or "outputs")
        / f"{platform.value}_comments_{run_id}"
    )
    storage = Storage(output_dir, run_id=run_id)

    storage.record_run({
        "run_id": run_id,
        "mode": "comments_from_products",
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
    for i, row in enumerate(df.itertuples(index=False), start=1):
        pid = str(row.product_id)
        logger.info(f"[comments] ({i}/{len(df)}) product_id={pid}")
        try:
            comments = await crawler.fetch_comments(pid, page=1)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"Skipping {pid}: {exc!r}")
            continue
        total += storage.save_comments(
            comments, file_tag=f"comments_{pid}"
        )

    storage.record_run({
        "run_id": run_id,
        "mode": "comments_from_products",
        "platforms": [platform.value],
        "category": None,
        "keywords": [],
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
        "product_count": 0,
        "comment_count": total,
        "output_dir": str(output_dir),
    })
    logger.info(f"[comments] total saved: {total}")
    return {"platform": platform.value, "comment_count": total, "run_id": run_id}
