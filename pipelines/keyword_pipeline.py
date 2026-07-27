"""`keyword` pipeline — search by keywords, save top products + their top comments."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core import Storage
from core.logger import logger
from services.platform_registry import get_registry


async def run_keyword_pipeline(
    keywords: list[str],
    platform_value: str = "tiki",
    output_dir: str | Path | None = None,
    fetch_comments: bool = True,
    max_products_per_keyword: int = 10,
) -> dict:
    """For each keyword, search & save top products (+ optionally their comments)."""
    from models import Platform

    platform = Platform.parse(platform_value)
    crawler = get_registry().get(platform)

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = (
        Path(output_dir or "outputs")
        / f"{platform.value}_keyword_{run_id}"
    )
    storage = Storage(output_dir, run_id=run_id)

    storage.record_run({
        "run_id": run_id,
        "mode": "keyword",
        "platforms": [platform.value],
        "category": None,
        "keywords": keywords,
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
        "product_count": 0,
        "comment_count": 0,
        "output_dir": str(output_dir),
    })

    total_p = 0
    total_c = 0
    for kw in keywords:
        logger.info(f"[keyword] searching platform={platform.value} kw={kw!r}")
        try:
            products = await crawler.search(kw, page=1)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"search failed for {kw!r}: {exc!r}")
            continue
        top = products[:max_products_per_keyword]
        total_p += storage.save_products(
            top, file_tag=f"keyword_{kw}_top"
        )

        if fetch_comments and crawler.supports_comments():
            for p in top:
                try:
                    cs = await crawler.fetch_comments(p.product_id, page=1)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"comments failed for {p.product_id}: {exc!r}")
                    continue
                total_c += storage.save_comments(
                    cs, file_tag=f"keyword_{kw}_{p.product_id}_comments"
                )

    storage.record_run({
        "run_id": run_id,
        "mode": "keyword",
        "platforms": [platform.value],
        "category": None,
        "keywords": keywords,
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": datetime.utcnow().isoformat(),
        "product_count": total_p,
        "comment_count": total_c,
        "output_dir": str(output_dir),
    })
    logger.info(f"[keyword] total products={total_p}, comments={total_c}")
    return {
        "platform": platform.value,
        "product_count": total_p,
        "comment_count": total_c,
        "run_id": run_id,
    }
