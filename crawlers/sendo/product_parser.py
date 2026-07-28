"""Parse Sendo product JSON into `Product` models.

Sendo's search and category endpoints return `{"data": [...]}` or
`{"result": {"data": [...]}}`. Each item carries `id`, `name`, `price`,
`final_price`, `discount_price`, `rating`, `review_count`, `sold_quantity`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from models import Platform, Product


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_float(x: Any) -> float | None:
    if x is None or x == "":
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    # Reject NaN/inf — pydantic's `ge=0` does not.
    import math
    if not math.isfinite(v):
        return None
    return v


def _coerce_int(x: Any) -> int | None:
    if x is None or x == "":
        return None
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return None


def _normalize_url(url: str, product_id: str) -> str:
    if not url:
        return f"https://www.sendo.vn/product/{product_id}.htm"
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://www.sendo.vn" + url
    return f"https://www.sendo.vn/product/{product_id}.htm"


def _category_path_from(item: dict) -> str:
    cat = (
        item.get("category_name")
        or item.get("cat_name")
        or item.get("categoryName")
    )
    if cat:
        return str(cat)
    catid = item.get("category_id") or item.get("catid")
    return str(catid) if catid else ""


def _first_price(item: dict) -> tuple[Any, Any]:
    """Sendo uses `final_price`/`price` (current) and `market_price`/`list_price` (original)."""
    price = (
        item.get("final_price")
        or item.get("price")
        or item.get("discount_price")
    )
    original = (
        item.get("market_price")
        or item.get("list_price")
        or item.get("original_price")
    )
    return price, original


def _product_from_item(item: dict) -> Product | None:
    if not isinstance(item, dict):
        return None
    pid = item.get("id") or item.get("product_id") or item.get("sku")
    name = item.get("name") or item.get("title")
    if not pid or not name:
        return None
    price, original = _first_price(item)
    return Product(
        platform=Platform.SENDO,
        product_id=str(pid),
        name=str(name).strip(),
        price=_coerce_float(price),
        original_price=_coerce_float(original),
        rating=_coerce_float(item.get("rating") or item.get("rating_average")),
        review_count=_coerce_int(item.get("review_count") or item.get("review_total")),
        sold_count=_coerce_int(item.get("sold_quantity") or item.get("sold")),
        category_path=_category_path_from(item),
        url=_normalize_url(item.get("url") or item.get("product_url") or "", str(pid)),
        crawled_at=_utcnow(),
    )


def parse_products_json(payload: Any) -> list[Product]:
    """Parse a Sendo API JSON payload."""
    items: list[dict] = []
    if isinstance(payload, list):
        items = [x for x in payload if isinstance(x, dict)]
    elif isinstance(payload, dict):
        for key in ("data", "result", "items"):
            v = payload.get(key)
            if isinstance(v, list):
                items = [x for x in v if isinstance(x, dict)]
                break
            if isinstance(v, dict):
                inner = v.get("data") or v.get("items")
                if isinstance(inner, list):
                    items = [x for x in inner if isinstance(x, dict)]
                    break
    else:
        return []

    out: list[Product] = []
    seen: set[str] = set()
    for it in items:
        p = _product_from_item(it)
        if p is None:
            continue
        if p.product_id in seen:
            continue
        seen.add(p.product_id)
        out.append(p)
    return out


def parse_search_json(payload: Any) -> list[Product]:
    """Alias used by the keyword pipeline."""
    return parse_products_json(payload)
