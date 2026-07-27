"""`menu` pipeline — crawl categories, save to CSV/SQLite/JSONL."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core import Storage
from core.logger import logger
from services.platform_registry import get_registry


async def run_menu_pipeline(
    platform_value: str = "tiki",
    output_dir: str | Path | None = None,
    level: int = 3,
) -> dict:
    """Crawl the menu tree for one platform, save results.

    Returns a small dict summary `{platform, count, run_id}`.
    """
    from models import Platform

    platform = Platform.parse(platform_value)
    crawler = get_registry().get(platform)

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(output_dir or "outputs") / f"{platform.value}_menu_{run_id}"
    storage = Storage(output_dir, run_id=run_id)

    storage.record_run({
        "run_id": run_id,
        "mode": "menu",
        "platforms": [platform.value],
        "category": None,
        "keywords": [],
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
        "product_count": 0,
        "comment_count": 0,
        "output_dir": str(output_dir),
    })

    logger.info(f"[menu] platform={platform.value} level={level} run_id={run_id}")
    categories = await crawler.fetch_menu(level=level)
    n = storage.save_categories(categories, file_tag="menu")

    storage.record_run({
        "run_id": run_id,
        "mode": "menu",
        "platforms": [platform.value],
        "category": None,
        "keywords": [],
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
        "product_count": 0,
        "comment_count": 0,
        "output_dir": str(output_dir),
    })
    logger.info(f"[menu] saved {n} categories")
    return {"platform": platform.value, "count": n, "run_id": run_id}
