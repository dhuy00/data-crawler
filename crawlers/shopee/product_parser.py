"""Parse Shopee product data into `Product` models.

Input is a JSON response from Shopee's search/category endpoints
(`/api/v4/search/search`, `/api/v4/recommend/recommend`, etc.). The
response shape is `{"items": [...], "total_count": N}`. Each item
contains nested fields like `item_basic` (id, name, price, images,
shop_location, brand) and `item_rating` (rating_star, rating_count,
historical_sold).
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
    import math
    if not math.isfinite(v):
        return None
    return v


def _coerce_int(x: Any) -> int | None:
    if x is None or x == "":
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _coerce_price(x: Any) -> float | None:
    """Shopee prices are stored as hundredths (e.g. 19900000 -> 199000.00)."""
    raw = _coerce_float(x)
    if raw is None:
        return None
    if raw > 1_000_000:  # likely sub-units; divide
        return raw / 100_000.0
    return raw


def _normalize_url(url: str, itemid: str, shopid: str) -> str:
    """Build a canonical Shopee product URL."""
    if not url:
        return f"https://shopee.vn/product/{shopid}/{itemid}"
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://shopee.vn" + url
    return f"https://shopee.vn/product/{shopid}/{itemid}"


def _category_path_from(item: dict) -> str:
    """Best-effort category breadcrumb from a Shopee item dict.

    Shopee exposes `categories` (list of {catid, display_name, ...}) and
    sometimes `catid` directly on the item. We prefer the latter for
    breadcrumb depth.
    """
    cats = item.get("categories") or []
    parts: list[str] = []
    if isinstance(cats, list):
        for c in cats:
            if isinstance(c, dict):
                name = c.get("display_name") or c.get("name")
                if name:
                    parts.append(str(name))
            elif isinstance(c, str):
                parts.append(c)
    if not parts:
        # Single-cat fallback
        catid = item.get("catid")
        if catid:
            parts.append(str(catid))
    return " > ".join(parts)


def _product_from_item(item: dict) -> Product | None:
    """Extract a `Product` from a Shopee API item dict."""
    if not isinstance(item, dict):
        return None
    # `item_basic` carries the canonical product fields in nested responses;
    # unwrap if present, otherwise use the item itself.
    core = item.get("item_basic") if isinstance(item.get("item_basic"), dict) else item

    itemid = core.get("itemid") or core.get("id") or item.get("itemid")
    name = core.get("name") or item.get("name") or item.get("title")
    shopid = (
        core.get("shopid") or item.get("shopid")
        or core.get("shop_id") or item.get("shop_id") or "0"
    )
    if not itemid or not name:
        return None

    # Shopee puts `item_rating` on the outer item, NOT inside `item_basic`.
    rating_obj = item.get("item_rating")
    if not isinstance(rating_obj, dict):
        rating_obj = core.get("item_rating") if isinstance(core.get("item_rating"), dict) else {}
    rating = rating_obj.get("rating_star") or item.get("rating_star")
    review_count = rating_obj.get("rating_count") or item.get("rating_count")
    sold = rating_obj.get("historical_sold") or item.get("historical_sold")

    url_hint = (
        core.get("url") or item.get("url") or item.get("short_url")
        or item.get("share_url") or ""
    )

    return Product(
        platform=Platform.SHOPEE,
        product_id=f"{shopid}_{itemid}",
        name=str(name).strip(),
        price=_coerce_price(core.get("price") or item.get("price")),
        original_price=_coerce_price(core.get("price_before_discount")
                                     or item.get("price_before_discount")),
        rating=_coerce_float(rating),
        review_count=_coerce_int(review_count),
        sold_count=_coerce_int(sold),
        category_path=_category_path_from(item),
        url=_normalize_url(url_hint, str(itemid), str(shopid)),
        crawled_at=_utcnow(),
    )


def parse_products_json(payload: Any) -> list[Product]:
    """Parse a Shopee API search/category JSON payload.

    Accepts:
    - a `{"items": [...]}` wrapper
    - a bare list of item dicts
    - a wrapped `{"data": {"items": [...]}}` shape
    """
    items: list[dict] = []
    if isinstance(payload, list):
        items = [x for x in payload if isinstance(x, dict)]
    elif isinstance(payload, dict):
        # Try common wrappers in order.
        for key in ("items", "data", "products"):
            v = payload.get(key)
            if isinstance(v, list):
                items = [x for x in v if isinstance(x, dict)]
                break
            if isinstance(v, dict):
                inner = v.get("items")
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
    """Alias for `parse_products_json` used by the keyword pipeline."""
    return parse_products_json(payload)
