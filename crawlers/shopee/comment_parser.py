"""Parse Shopee product reviews into `Comment` models.

Shopee's review API (`/api/v2/rating/get_ratings`) is heavily protected;
the simplest reliable fallback is Playwright scraping of the product
detail page. We therefore accept either:

- a JSON `{"data": {"ratings": [...]}}` payload (preferred), or
- an HTML string with embedded initial-state JSON.

Each rating dict has fields: `cmtid` (comment id), `comment`, `rating`,
`author_username`, `ctime` (unix seconds, as string).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from models import Comment, Platform


_INITIAL_STATE_RE = re.compile(
    r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;', re.DOTALL
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_int(x: Any) -> int | None:
    if x is None or x == "":
        return None
    try:
        v = int(float(x))
    except (TypeError, ValueError):
        return None
    if not 1 <= v <= 5:
        return None
    return v


def _coerce_str(x: Any) -> str:
    if x is None:
        return ""
    return str(x).strip()


def _walk_collect_ratings(node: Any, out: list[dict]) -> None:
    """Walk any JSON structure and collect dicts that look like Shopee ratings."""
    if isinstance(node, dict):
        cmtid = node.get("cmtid") or node.get("comment_id")
        if cmtid and (
            "comment" in node or "rating" in node or "author_username" in node
        ):
            out.append(node)
        for v in node.values():
            _walk_collect_ratings(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_collect_ratings(v, out)


def _comment_from_rating(d: dict, *, default_product_id: str = "") -> Comment | None:
    if not isinstance(d, dict):
        return None
    cmtid = d.get("cmtid") or d.get("comment_id")
    if not cmtid:
        return None
    productid = d.get("productid") or d.get("itemid") or default_product_id
    if not productid:
        return None
    ctime = d.get("ctime") or d.get("create_time") or ""
    if ctime:
        try:
            ctime = str(int(float(ctime)))
        except (TypeError, ValueError):
            ctime = str(ctime)
    return Comment(
        platform=Platform.SHOPEE,
        product_id=str(productid),
        comment_id=str(cmtid),
        author=_coerce_str(d.get("author_username") or d.get("author")),
        rating=_coerce_int(d.get("rating")),
        content=_coerce_str(d.get("comment") or d.get("content") or ""),
        created_at=ctime,
        crawled_at=_utcnow(),
    )


def parse_comments_json(payload: Any, *, product_id: str = "") -> list[Comment]:
    """Parse a Shopee rating API JSON payload."""
    candidates: list[dict] = []
    if isinstance(payload, dict):
        _walk_collect_ratings(payload, candidates)
    elif isinstance(payload, list):
        for x in payload:
            if isinstance(x, dict):
                _walk_collect_ratings(x, candidates)

    out: list[Comment] = []
    seen: set[str] = set()
    for d in candidates:
        c = _comment_from_rating(d, default_product_id=product_id)
        if c is None:
            continue
        if c.comment_id in seen:
            continue
        seen.add(c.comment_id)
        out.append(c)
    return out


def parse_comments_html(html: str, *, product_id: str = "") -> list[Comment]:
    """Fallback parser: extract embedded initial-state JSON from Shopee HTML."""
    m = _INITIAL_STATE_RE.search(html or "")
    if not m:
        return []
    try:
        blob = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    return parse_comments_json(blob, product_id=product_id)
