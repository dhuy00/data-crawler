"""Per-category review pipeline — fetch menu, pick 3 L1 categories, then
for each category crawl products + reviews and emit one wide CSV per
category (~25 columns mirroring the project's sample.csv shape).

Flow:
    fetch_menu(level=3) ->
        pick 3 leaf categories (configurable via `category_ids`) ->
            for each cat: fetch products (page 1) ->
                for each product: fetch_reviews_wide(page 1..N) ->
                    join product fields + review fields + category fields
                    into one flat row
                    -> append to per-category CSV

Outputs:
    <output_dir>/<platform>_<category_slug>_reviews_<run_id>.csv  (one file per category)

The CSV is intentionally wide: every product field Tiki exposes + every
review field Tiki exposes + every category field, denormalized into one
row per review. Schema matches `sample.csv` plus a few extras.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from core.logger import logger
from crawlers.tiki.product_parser import raw_extract_product_wide
from models import Platform
from services.platform_registry import get_registry


# Default column order: matches the project's sample.csv layout closely
# (product-side fields on the left, category tree, then review-side).
WIDE_COLUMNS: list[str] = [
    # Product
    "product_id",
    "seller_product_id",
    "product_name",
    "product_url",
    "product_price",
    "product_original_price",
    "product_rating_average",
    "product_review_count",
    "product_sold_count",
    "product_thumbnail_url",
    "product_brand",
    "product_categories_id",
    # Category (tree + per-row context)
    "category_id",
    "category_url",
    "category_name",
    "category_level",
    "category_parent_id",
    "lv1_name",
    "lv2_name",
    "lv3_name",
    # Seller
    "seller_id",
    "seller_name",
    # Review
    "comment_id",
    "comment_page",
    "comment_position",
    "customer_id",
    "customer_name",
    "customer_full_name",
    "customer_region",
    "customer_avatar_url",
    "rating",
    "title",
    "content",
    "thank_count",
    "score",
    "status",
    "is_photo",
    "created_at",
    "created_at_text",
    "purchased_at",
    # Crawl metadata
    "platform",
    "crawled_at",
]


def _empty_row_template() -> dict[str, Any]:
    return {col: None for col in WIDE_COLUMNS}


async def _gather_products_for_category(
    crawler,
    cat_row: dict,
    *,
    page: int = 1,
) -> list[dict]:
    """Get raw product dicts for one category.

    Strategy: use the category name as a search keyword against Tiki's
    search HTML. Tiki's category listing pages are JS-driven and the
    raw HTML may not contain enough product data; the search endpoint
    returns a richer `__NEXT_DATA__` blob.

    Returns the raw product dicts (NOT normalized `Product` objects),
    because we need seller_id/brand/etc. for the wide export.
    """
    cat_name = (cat_row.get("name") or cat_row.get("category_id") or "").strip()
    if not cat_name:
        return []

    search_html = ""
    try:
        # Use the crawler's underlying HTTP client (no public search-html
        # method exists, so we synthesize the URL ourselves).
        url = f"https://tiki.vn/search?q={cat_name}&page={page}"
        search_html = crawler._get_html(url)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"search HTML for {cat_name!r} failed: {exc!r}")
        return []

    if not search_html:
        return []

    import json as _json
    import re as _re
    m = _re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                   search_html, _re.DOTALL)
    if not m:
        return []
    try:
        blob = _json.loads(m.group(1))
    except _json.JSONDecodeError:
        return []

    found: list[dict] = []

    def is_product_dict(o: Any) -> bool:
        if not isinstance(o, dict):
            return False
        return bool(o.get("id")) and bool(o.get("name")) and (
            o.get("price") is not None
            or o.get("url_path") or o.get("url")
        )

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if is_product_dict(node):
                found.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(blob)
    seen: set[str] = set()
    out: list[dict] = []
    for d in found:
        pid = str(d.get("id"))
        if pid in seen:
            continue
        seen.add(pid)
        out.append(d)
    return out


async def _gather_products_from_category_html(
    crawler,
    category_url: str,
    page: int = 1,
) -> list[dict]:
    """Re-parse the category page so we keep the full product dict.

    Kept as a fallback for platforms whose search HTML doesn't include
    product-level wide fields. Tiki's category HTML returns the
    `__NEXT_DATA__` blob but no product list at L1, so this path
    usually returns `[]` for Tiki. The new
    `_gather_products_for_category` is preferred.
    """
    html = await crawler.fetch_category_html(category_url, page=page)
    if not html:
        return []
    import json as _json
    import re as _re
    m = _re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                   html, _re.DOTALL)
    if not m:
        return []
    try:
        blob = _json.loads(m.group(1))
    except _json.JSONDecodeError:
        return []

    found: list[dict] = []

    def is_product_dict(o: Any) -> bool:
        if not isinstance(o, dict):
            return False
        return bool(o.get("id")) and bool(o.get("name")) and (
            o.get("price") is not None
            or o.get("url_path") or o.get("url")
        )

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            if is_product_dict(node):
                found.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(blob)
    seen: set[str] = set()
    out: list[dict] = []
    for d in found:
        pid = str(d.get("id"))
        if pid in seen:
            continue
        seen.add(pid)
        out.append(d)
    return out


def _category_breadcrumb(
    seed_root: dict[str, dict],
    category_id: str,
) -> dict[str, str | None]:
    """Compute lv1/lv2/lv3 names by walking parent_id chain."""
    out: dict[str, str | None] = {"lv1_name": None, "lv2_name": None, "lv3_name": None}
    pid: str | None = category_id
    seen: set[str] = set()
    while pid and pid not in seen:
        seen.add(pid)
        row = seed_root.get(pid)
        if not row:
            break
        level = row.get("level")
        name = row.get("name")
        if level == 1:
            out["lv1_name"] = name
        elif level == 2:
            out["lv2_name"] = name
        elif level == 3:
            out["lv3_name"] = name
        pid = row.get("parent_id")
    return out


async def _process_product(
    crawler,
    product_dict: dict,
    *,
    cat_row: dict,
    breadcrumb: dict,
) -> list[dict[str, Any]]:
    """For one product, fetch reviews and return wide rows."""
    pid = str(product_dict.get("id"))
    if not pid:
        return []
    product_wide = raw_extract_product_wide(product_dict)

    # Reviews — page 1 only by default; the pipeline caller can request more.
    try:
        reviews = await crawler.fetch_reviews_wide(pid, page=1, position_start=1)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"fetch_reviews_wide({pid}) failed: {exc!r}")
        reviews = []

    rows: list[dict[str, Any]] = []
    if not reviews:
        row = _empty_row_template()
        row.update({
            "product_id": pid,
            "seller_product_id": product_wide.get("seller_product_id"),
            "product_name": product_wide.get("product_name"),
            "product_url": product_wide.get("product_url"),
            "product_price": product_wide.get("product_price"),
            "product_original_price": product_wide.get("product_original_price"),
            "product_rating_average": product_wide.get("product_rating_average"),
            "product_review_count": product_wide.get("product_review_count"),
            "product_sold_count": product_wide.get("product_sold_count"),
            "product_thumbnail_url": product_wide.get("product_thumbnail_url"),
            "product_brand": product_wide.get("product_brand"),
            "product_categories_id": product_wide.get("product_categories_id"),
            "category_id": cat_row.get("category_id"),
            "category_url": cat_row.get("url"),
            "category_name": cat_row.get("name"),
            "category_level": cat_row.get("level"),
            "category_parent_id": cat_row.get("parent_id"),
            "lv1_name": breadcrumb.get("lv1_name"),
            "lv2_name": breadcrumb.get("lv2_name"),
            "lv3_name": breadcrumb.get("lv3_name"),
            "seller_id": product_wide.get("seller_id"),
            "seller_name": product_wide.get("seller_name"),
            "platform": Platform.TIKI.value,
        })
        rows.append(row)
        return rows

    for r in reviews:
        row = _empty_row_template()
        row.update({
            "product_id": pid,
            "seller_product_id": product_wide.get("seller_product_id"),
            "product_name": product_wide.get("product_name"),
            "product_url": product_wide.get("product_url"),
            "product_price": product_wide.get("product_price"),
            "product_original_price": product_wide.get("product_original_price"),
            "product_rating_average": product_wide.get("product_rating_average"),
            "product_review_count": product_wide.get("product_review_count"),
            "product_sold_count": product_wide.get("product_sold_count"),
            "product_thumbnail_url": product_wide.get("product_thumbnail_url"),
            "product_brand": product_wide.get("product_brand"),
            "product_categories_id": product_wide.get("product_categories_id"),
            "category_id": cat_row.get("category_id"),
            "category_url": cat_row.get("url"),
            "category_name": cat_row.get("name"),
            "category_level": cat_row.get("level"),
            "category_parent_id": cat_row.get("parent_id"),
            "lv1_name": breadcrumb.get("lv1_name"),
            "lv2_name": breadcrumb.get("lv2_name"),
            "lv3_name": breadcrumb.get("lv3_name"),
            "seller_id": product_wide.get("seller_id") or r.get("seller_id"),
            "seller_name": product_wide.get("seller_name") or r.get("seller_name"),
            "comment_id": r.get("comment_id"),
            "comment_page": r.get("page_no"),
            "comment_position": r.get("position"),
            "customer_id": r.get("customer_id"),
            "customer_name": r.get("customer_name"),
            "customer_full_name": r.get("customer_full_name"),
            "customer_region": r.get("customer_region"),
            "customer_avatar_url": r.get("customer_avatar_url"),
            "rating": r.get("rating"),
            "title": r.get("title"),
            "content": r.get("content"),
            "thank_count": r.get("thank_count"),
            "score": r.get("score"),
            "status": r.get("status"),
            "is_photo": r.get("is_photo"),
            "created_at": r.get("created_at"),
            "created_at_text": r.get("created_at_text"),
            "purchased_at": r.get("purchased_at"),
            "platform": Platform.TIKI.value,
            "crawled_at": r.get("crawled_at"),
        })
        rows.append(row)
    return rows


async def _process_category(
    crawler,
    cat_row: dict,
    *,
    seed_root: dict[str, dict],
    max_products: int = 5,
) -> list[dict[str, Any]]:
    """Crawl one category: products + reviews."""
    cat_id = str(cat_row.get("category_id"))
    cat_url = cat_row.get("url")
    if not cat_url:
        logger.warning(f"Skipping category {cat_id!r} (no url)")
        return []
    logger.info(f"[category] {cat_row.get('name', cat_id)} -> {cat_url}")
    # Preferred path: search by category name (returns products with wide fields)
    product_dicts = await _gather_products_for_category(crawler, cat_row)
    if not product_dicts:
        # Fallback to direct category URL parse
        product_dicts = await _gather_products_from_category_html(
            crawler, cat_url
        )
    product_dicts = product_dicts[:max_products]
    logger.info(f"  fetched {len(product_dicts)} products")

    breadcrumb = _category_breadcrumb(seed_root, cat_id)

    all_rows: list[dict[str, Any]] = []
    for pd_dict in product_dicts:
        rows = await _process_product(
            crawler, pd_dict, cat_row=cat_row, breadcrumb=breadcrumb
        )
        all_rows.extend(rows)
    return all_rows


async def run_category_reviews_pipeline(
    *,
    platform_value: str = "tiki",
    category_ids: Iterable[str] | None = None,
    max_products_per_category: int = 5,
    output_dir: str | Path | None = None,
) -> dict:
    """Crawl menu, pick 3 categories, and emit one wide CSV per category."""
    platform = Platform.parse(platform_value)
    crawler = get_registry().get(platform)

    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base = Path(output_dir or "outputs")
    base.mkdir(parents=True, exist_ok=True)

    menu = await crawler.fetch_menu(level=3)
    seed_root = {
        str(c.category_id): {
            "name": c.name,
            "level": c.level,
            "parent_id": str(c.parent_id) if c.parent_id else None,
        }
        for c in menu
    }
    logger.info(f"menu has {len(menu)} categories")

    if category_ids is not None:
        wanted = [str(x) for x in category_ids]
        chosen = [c for c in menu if str(c.category_id) in wanted]
        if not chosen:
            chosen = menu[:3]
    else:
        chosen = [c for c in menu if c.level == 1][:3]
        if len(chosen) < 3:
            extras = [c for c in menu if c.level != 1]
            chosen = (chosen + extras)[:3]
    logger.info(f"selected categories: {[c.category_id for c in chosen]}")

    cat_rows = [
        {
            "category_id": str(c.category_id),
            "name": c.name,
            "url": c.url,
            "level": c.level,
            "parent_id": str(c.parent_id) if c.parent_id else None,
        }
        for c in chosen
    ]

    summary: list[dict[str, Any]] = []
    for cat_row in cat_rows:
        rows = await _process_category(
            crawler,
            cat_row,
            seed_root=seed_root,
            max_products=max_products_per_category,
        )
        if not rows:
            logger.warning(f"  no rows for {cat_row['category_id']!r}")
            continue
        df = pd.DataFrame(rows, columns=WIDE_COLUMNS)
        slug = str(cat_row["category_id"]).replace("/", "_")
        csv_path = base / f"{platform.value}_{slug}_reviews_{run_id}.csv"
        df.to_csv(csv_path, index=False, encoding="utf-8")
        jsonl_path = base / "raw" / f"{platform.value}_{slug}_reviews_{run_id}.jsonl"
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, default=str, ensure_ascii=False) + "\n")
        logger.info(
            f"  wrote {len(rows)} rows -> {csv_path.name} "
            f"(+ {jsonl_path.name})"
        )
        summary.append({
            "category_id": cat_row["category_id"],
            "category_name": cat_row["name"],
            "csv": str(csv_path),
            "jsonl": str(jsonl_path),
            "row_count": len(rows),
            "product_count": len({r["product_id"] for r in rows}),
        })

    return {
        "platform": platform.value,
        "run_id": run_id,
        "categories": summary,
        "output_dir": str(base),
    }


def main() -> None:  # pragma: no cover — manual runner
    import argparse

    p = argparse.ArgumentParser(description="Per-category wide review pipeline")
    p.add_argument("--platform", default="tiki")
    p.add_argument(
        "--category-ids",
        default=None,
        help="Comma-separated list of category_ids. Default: first 3 L1.",
    )
    p.add_argument("--max-products-per-category", type=int, default=5)
    p.add_argument("--output-dir", default=None)
    args = p.parse_args()

    cats = (
        [c.strip() for c in args.category_ids.split(",") if c.strip()]
        if args.category_ids
        else None
    )
    result = asyncio.run(
        run_category_reviews_pipeline(
            platform_value=args.platform,
            category_ids=cats,
            max_products_per_category=args.max_products_per_category,
            output_dir=args.output_dir,
        )
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":  # pragma: no cover
    main()
