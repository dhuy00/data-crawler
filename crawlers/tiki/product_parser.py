"""Parse Tiki product data (from search / category HTML) into `Product` models.

Primary input: HTML page with embedded `__NEXT_DATA__` JSON blob.
The JSON tree shape is `props.pageProps.data` (varies by page type). For
search results the relevant array lives under `data.searchResult.products`
or `data.products`. Each item has at minimum `id`, `name`, `url`, and
optional `price`, `original_price`, `rating_average`, `review_count`,
`all_time_quantity_sold`, `categories`.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from models import Platform, Product


_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_float(x: Any) -> float | None:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _coerce_int(x: Any) -> int | None:
    if x is None or x == "":
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def _category_path(data: dict) -> str:
    cats = data.get("categories") or {}
    if isinstance(cats, dict):
        names = cats.get("name") or cats.get("display_name")
        if isinstance(names, list):
            return " > ".join(str(n) for n in names if n)
    if isinstance(cats, list):
        return " > ".join(str(c.get("name") or c) for c in cats if isinstance(c, dict))
    return ""


def _normalize_url(url: str) -> str:
    """Promote Tiki-relative URLs to absolute.

    Tiki's `__NEXT_DATA__` emits URLs in several shapes:
    - absolute: 'https://tiki.vn/iphone-15-p123.html'
    - root-relative: '/apple-iphone-17-p123.html'
    - bare-relative (no scheme, no leading slash): 'apple-iphone-17-p123.html?spid=...'

    All three resolve to the same page on `tiki.vn`. Skip empty.
    """
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("//"):
        return "https:" + url
    if url.startswith("/"):
        return "https://tiki.vn" + url
    return "https://tiki.vn/" + url.lstrip("/")


def _product_from_dict(d: dict) -> Product | None:
    if not isinstance(d, dict):
        return None
    pid = d.get("id") or d.get("product_id") or d.get("sku")
    name = d.get("name") or d.get("title")
    url = _normalize_url(str(d.get("url_path") or d.get("url") or d.get("short_url") or ""))
    if not pid or not name:
        return None
    return Product(
        platform=Platform.TIKI,
        product_id=str(pid),
        name=str(name).strip(),
        price=_coerce_float(d.get("price")),
        original_price=_coerce_float(d.get("original_price") or d.get("list_price")),
        rating=_coerce_float(d.get("rating_average") or d.get("rating")),
        review_count=_coerce_int(d.get("review_count") or d.get("review")),
        sold_count=_coerce_int(d.get("all_time_quantity_sold") or d.get("quantity_sold")),
        category_path=_category_path(d),
        url=url,
        crawled_at=_utcnow(),
    )


def _collect_product_dicts(blob: dict) -> list[dict]:
    """Walk the next-data blob and return all dicts that look like products."""
    found: list[dict] = []

    def is_product_dict(o: Any) -> bool:
        if not isinstance(o, dict):
            return False
        # A product has id + name; require url OR price to avoid matching random leaves.
        return (
            bool(o.get("id"))
            and bool(o.get("name"))
            and (o.get("price") is not None or o.get("url_path") or o.get("url"))
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
    return found


def parse_products_html(html: str) -> list[Product]:
    """Extract products from a Tiki search / category HTML page."""
    m = _NEXT_DATA_RE.search(html or "")
    if not m:
        return []
    try:
        blob = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    raw_dicts = _collect_product_dicts(blob)
    out: list[Product] = []
    seen: set[tuple[str, str]] = set()
    for d in raw_dicts:
        p = _product_from_dict(d)
        if p is None:
            continue
        key = (p.platform.value, p.product_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def parse_products_json(payload: dict) -> list[Product]:
    """Fallback parser for a plain JSON list / wrapped response."""
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        for key in ("data", "products", "items", "results"):
            v = payload.get(key)
            if isinstance(v, list):
                items = v
                break
        else:
            return []
    else:
        return []

    out: list[Product] = []
    for d in items:
        p = _product_from_dict(d)
        if p is not None:
            out.append(p)
    return out
