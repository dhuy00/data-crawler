"""Parse Sendo product reviews into `Comment` models.

Sendo's review payload (when accessible) lives under `data.feedBacks`
or `data.reviews`. Each rating carries `id`, `content`, `rating`,
`customerName`, `createdAt`.
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


def _walk_collect_reviews(node: Any, out: list[dict]) -> None:
    if isinstance(node, dict):
        rid = node.get("id") or node.get("review_id")
        if rid and (
            "content" in node or "rating" in node
            or "customerName" in node
        ):
            out.append(node)
        for v in node.values():
            _walk_collect_reviews(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_collect_reviews(v, out)


def _comment_from_review(d: dict, *, default_product_id: str = "") -> Comment | None:
    if not isinstance(d, dict):
        return None
    rid = d.get("id") or d.get("review_id")
    if not rid:
        return None
    pid = (
        d.get("product_id") or d.get("productId")
        or d.get("item_id") or default_product_id
    )
    if not pid:
        return None
    return Comment(
        platform=Platform.SENDO,
        product_id=str(pid),
        comment_id=str(rid),
        author=_coerce_str(d.get("customerName") or d.get("author") or d.get("userName")),
        rating=_coerce_int(d.get("rating")),
        content=_coerce_str(d.get("content") or d.get("comment") or ""),
        created_at=_coerce_str(d.get("createdAt") or d.get("create_time") or ""),
        crawled_at=_utcnow(),
    )


def parse_comments_json(payload: Any, *, product_id: str = "") -> list[Comment]:
    candidates: list[dict] = []
    if isinstance(payload, dict):
        _walk_collect_reviews(payload, candidates)
    elif isinstance(payload, list):
        for x in payload:
            if isinstance(x, dict):
                _walk_collect_reviews(x, candidates)

    out: list[Comment] = []
    seen: set[str] = set()
    for d in candidates:
        c = _comment_from_review(d, default_product_id=product_id)
        if c is None:
            continue
        if c.comment_id in seen:
            continue
        seen.add(c.comment_id)
        out.append(c)
    return out


def parse_comments_html(html: str, *, product_id: str = "") -> list[Comment]:
    m = _INITIAL_STATE_RE.search(html or "")
    if not m:
        return []
    try:
        blob = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    return parse_comments_json(blob, product_id=product_id)
