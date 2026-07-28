"""Parse Lazada product JSON into `Product` models.

Lazada's catalog search returns `{"products": [...]}` where each item
carries `id`, `name`, `price` (already a float string like "259.00"),
`originalPrice`, `ratingScore`, `review`, `soldCount` etc. Categories
are not deeply nested in search results; we leave `category_path` as
a flat path from the URL slug when available.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

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
        return f"https://www.lazada.vn/products/p{product_id}.html"
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://www.lazada.vn" + url
    return f"https://www.lazada.vn/products/p{product_id}.html"


def _category_path_from(item: dict) -> str:
    """Best-effort breadcrumb; Lazada search results are usually flat."""
    # Newer response uses `pdtCategoryName` as a single string.
    single = (
        item.get("pdtCategoryName") or item.get("category_name")
        or item.get("mainCategoryName")
    )
    if single:
        return str(single)
    cats = item.get("categories")
    if isinstance(cats, list):
        parts = [
            str(c.get("name") or c) for c in cats
            if isinstance(c, dict) and c.get("name")
        ]
        if parts:
            return " > ".join(parts)
    return ""


def _product_from_item(item: dict) -> Product | None:
    if not isinstance(item, dict):
        return None
    pid = item.get("id") or item.get("itemId") or item.get("productId")
    name = item.get("name") or item.get("title")
    if not pid or not name:
        return None

    price = item.get("price")
    if isinstance(price, str):
        try:
            price_val = float(price)
        except ValueError:
            price_val = None
    else:
        price_val = _coerce_float(price)

    original_price = item.get("originalPrice") or item.get("original_price")
    if isinstance(original_price, str):
        try:
            original_price_val = float(original_price)
        except ValueError:
            original_price_val = None
    else:
        original_price_val = _coerce_float(original_price)

    rating = (
        item.get("ratingScore")
        or item.get("rating")
        or item.get("averageRating")
    )
    if isinstance(rating, dict):
        rating = rating.get("average")

    url_hint = (
        item.get("productUrl") or item.get("url")
        or item.get("pdpUrl") or ""
    )

    return Product(
        platform=Platform.LAZADA,
        product_id=str(pid),
        name=str(name).strip(),
        price=price_val,
        original_price=original_price_val,
        rating=_coerce_float(rating),
        review_count=_coerce_int(item.get("review")),
        sold_count=_coerce_int(item.get("soldCount") or item.get("quantitySold")),
        category_path=_category_path_from(item),
        url=_normalize_url(url_hint, str(pid)),
        crawled_at=_utcnow(),
    )


def parse_products_json(payload: Any) -> list[Product]:
    """Parse a Lazada `/catalog/` JSON payload."""
    items: list[dict] = []
    if isinstance(payload, list):
        items = [x for x in payload if isinstance(x, dict)]
    elif isinstance(payload, dict):
        for key in ("products", "items", "results", "data"):
            v = payload.get(key)
            if isinstance(v, list):
                items = [x for x in v if isinstance(x, dict)]
                break
            if isinstance(v, dict):
                inner = v.get("products") or v.get("items")
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
