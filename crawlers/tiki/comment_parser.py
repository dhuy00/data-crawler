"""Parse Tiki product reviews from HTML.

Reviews live in the product detail page's `__NEXT_DATA__` blob under
`props.pageProps.reviews` (newer site) or `props.pageProps.data.reviews`
or `props.pageProps.data.product.reviews`. Each entry has keys like
`id`, `content`, `customer_name`, `rating`, `created_at`.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from models import Comment, Platform


_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_int(x: Any) -> int | None:
    if x is None or x == "":
        return None
    try:
        v = int(x)
    except (TypeError, ValueError):
        return None
    if not 1 <= v <= 5:
        return None
    return v


def _comment_from_dict(d: dict, *, default_product_id: str = "") -> Comment | None:
    if not isinstance(d, dict):
        return None
    cid = d.get("id") or d.get("review_id") or d.get("comment_id")
    content = d.get("content") or d.get("body") or d.get("text") or ""
    if not cid:
        return None
    pid = (
        d.get("product_id")
        or d.get("productId")
        or default_product_id
    )
    if not pid:
        # Without a product_id we cannot save the comment — drop it.
        return None
    return Comment(
        platform=Platform.TIKI,
        product_id=str(pid),
        comment_id=str(cid),
        author=str(d.get("customer_name") or d.get("author") or "").strip(),
        rating=_coerce_int(d.get("rating")),
        content=str(content).strip(),
        created_at=str(d.get("created_at") or d.get("createdAt") or ""),
        crawled_at=_utcnow(),
    )


def _find_review_arrays(blob: dict) -> list[list[dict]]:
    """Walk the blob and return any lists that look like review arrays."""
    arrays: list[list[dict]] = []

    def looks_like_review(d: dict) -> bool:
        return bool(d.get("id")) and (
            "content" in d or "body" in d or "text" in d or "rating" in d
        )

    def walk(node: Any) -> None:
        if isinstance(node, list):
            if node and all(isinstance(x, dict) and looks_like_review(x) for x in node[:3]):
                arrays.append(node)
            for v in node:
                walk(v)
        elif isinstance(node, dict):
            for v in node.values():
                walk(v)

    walk(blob)
    return arrays


def parse_comments_html(html: str, *, product_id: str = "") -> list[Comment]:
    """Extract reviews from a Tiki product detail HTML page."""
    m = _NEXT_DATA_RE.search(html or "")
    if not m:
        return []
    try:
        blob = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    out: list[Comment] = []
    seen: set[str] = set()
    for arr in _find_review_arrays(blob):
        for d in arr:
            c = _comment_from_dict(d, default_product_id=product_id)
            if c is None:
                continue
            if c.comment_id in seen:
                continue
            seen.add(c.comment_id)
            out.append(c)
    return out
