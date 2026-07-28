"""Multi-platform pipeline — run a single-platform pipeline across
several platforms and aggregate the results.

This is the Phase 5 deliverable. We deliberately keep the implementation
simple:

- Fan out `run_full_pipeline` (or `run_keyword_pipeline`) to each
  platform sequentially. The CLI ships `--platforms a,b,c` and we
  iterate.
- Aggregate the per-platform stats into one summary dict.
- No cross-platform ranking (deliberately deferred; see plan §7 Phase 5).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.logger import logger
from models import Platform

from .full_pipeline import run_full_pipeline
from .keyword_pipeline import run_keyword_pipeline


async def run_multi_platform_pipeline(
    platforms: list[str],
    mode: str = "full",
    output_dir: str | Path | None = None,
    fetch_comments: bool = True,
    limit_products: int | None = None,
    keywords: list[str] | None = None,
    max_products_per_keyword: int = 10,
) -> dict:
    """Run the chosen `mode` pipeline against each platform in `platforms`.

    `mode` may be `"full"` or `"keyword"`; other modes are single-platform
    by design and are run per-platform in sequence.
    """
    if not platforms:
        raise ValueError("platforms must be a non-empty list")
    if mode not in {"full", "keyword"}:
        raise ValueError(
            f"Multi-platform pipeline only supports 'full' or 'keyword' mode, got {mode!r}"
        )

    base = Path(output_dir or "outputs")
    base.mkdir(parents=True, exist_ok=True)

    started_at = datetime.utcnow()
    run_id = started_at.strftime("%Y%m%d_%H%M%S")
    results: dict[str, dict] = {}
    total_products = 0
    total_comments = 0

    for plat_value in platforms:
        plat = Platform.parse(plat_value)
        logger.info(
            f"[multi:{mode}] starting platform={plat.value} (run_id={run_id})"
        )
        try:
            if mode == "full":
                res = await run_full_pipeline(
                    platform_value=plat.value,
                    output_dir=base,
                    fetch_comments=fetch_comments,
                    limit_products=limit_products,
                )
            else:  # keyword
                res = await run_keyword_pipeline(
                    keywords=keywords or [],
                    platform_value=plat.value,
                    output_dir=base,
                    fetch_comments=fetch_comments,
                    max_products_per_keyword=max_products_per_keyword,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"[multi:{mode}] platform={plat.value} failed: {exc!r}; continuing"
            )
            results[plat.value] = {"error": str(exc)}
            continue

        results[plat.value] = res
        total_products += res.get("product_count", 0)
        total_comments += res.get("comment_count", 0)

    finished_at = datetime.utcnow()
    summary = {
        "run_id": run_id,
        "mode": mode,
        "platforms": platforms,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "product_count": total_products,
        "comment_count": total_comments,
        "per_platform": results,
    }
    logger.info(
        f"[multi:{mode}] done. platforms={platforms} "
        f"products={total_products} comments={total_comments}"
    )
    return summary
