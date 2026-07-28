"""Parse Tiki product reviews from HTML.

Reviews live in the product detail page's `__NEXT_DATA__` blob under
`props.pageProps.reviews` (newer site) or `props.pageProps.data.reviews`
or `props.pageProps.data.product.reviews`. Each entry has keys like
`id`, `content`, `customer_name`, `rating`, `created_at`.

Two parsers exposed:

- `parse_comments_html(html, product_id)` -> list[Comment]
    The canonical `Comment` model. Used by the standard pipeline.

- `parse_reviews_wide(html, product_id, page_no, position_start)` -> list[dict]
    Returns every field Tiki exposes, flattened for export to a wide CSV
    (~25+ columns mirroring the project sample.csv). This path is used by
    the `category_reviews` pipeline.
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


def _str_or_none(x: Any) -> str | None:
    if x is None:
        return None
    s = str(x).strip()
    return s or None


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


# ----------------------------------------------------------- wide parser


def _flatten_review(d: dict) -> dict[str, Any] | None:
    """Extract every review field we can from a Tiki review dict.

    Field names follow the project's sample.csv convention.
    """
    if not isinstance(d, dict):
        return None
    if not (d.get("id") or d.get("review_id")):
        return None

    content = d.get("content") or d.get("body") or d.get("text") or ""
    return {
        "comment_id": _str_or_none(d.get("id") or d.get("review_id")),
        "customer_id": _str_or_none(d.get("customer_id") or d.get("customerId")),
        "customer_name": _str_or_none(d.get("customer_name") or d.get("customerName")),
        "customer_full_name": _str_or_none(
            d.get("full_name") or d.get("customer_full_name")
        ),
        "customer_region": _str_or_none(
            d.get("region") or d.get("customer_region") or d.get("location")
        ),
        "customer_avatar_url": _str_or_none(
            d.get("avatar_url") or d.get("avatar") or d.get("customer_avatar_url")
        ),
        "rating": _coerce_int(d.get("rating")),
        "title": _str_or_none(d.get("title")),
        "content": str(content).strip() if content else "",
        "thank_count": _coerce_int(
            d.get("thank_count") or d.get("thanks_count") or d.get("likes")
        ),
        "score": (
            float(d.get("score"))
            if isinstance(d.get("score"), (int, float))
            else (float(str(d.get("score"))) if _str_or_none(d.get("score")) else None)
        ),
        "status": _str_or_none(d.get("status")),
        "is_photo": (
            bool(d.get("is_photo") or d.get("has_photo"))
            if d.get("is_photo") is not None or d.get("has_photo") is not None
            else None
        ),
        "created_at": _str_or_none(
            d.get("created_at") or d.get("createdAt")
        ),
        "created_at_text": _str_or_none(
            d.get("created_at_text") or d.get("createdAt_text") or d.get("created_at_display")
        ),
        "purchased_at": _str_or_none(
            d.get("purchased_at") or d.get("purchasedAt")
        ),
        "seller_id": _str_or_none(
            d.get("seller_id") or d.get("sellerId") or d.get("shop_id")
        ),
        "seller_name": _str_or_none(
            d.get("seller_name") or d.get("sellerName") or d.get("shop_name")
        ),
    }


def parse_reviews_wide(
    html: str,
    *,
    product_id: str = "",
    page_no: int = 1,
    position_start: int = 1,
) -> list[dict[str, Any]]:
    """Return reviews as flat dicts (every field Tiki exposes).

    Each dict additionally carries:
      - `page_no` (int): the page index this batch came from.
      - `position` (int, 1-based): position of this review on the page.
      - `product_id` (str): the parent product id.
      - `crawled_at` (ISO str): timestamp.
      - `platform` ("tiki"): constant tag for downstream pipelines.
    """
    m = _NEXT_DATA_RE.search(html or "")
    if not m:
        return []
    try:
        blob = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    crawled = _utcnow().isoformat()
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    pos = position_start
    for arr in _find_review_arrays(blob):
        for raw in arr:
            r = _flatten_review(raw)
            if r is None or not r["comment_id"]:
                continue
            if r["comment_id"] in seen:
                continue
            seen.add(r["comment_id"])
            r.update({
                "platform": Platform.TIKI.value,
                "product_id": product_id,
                "page_no": page_no,
                "position": pos,
                "crawled_at": crawled,
            })
            out.append(r)
            pos += 1
    return out


# ----------------------------------------------------- reviews API parser


def _epoch_to_iso(epoch) -> str | None:
    """Convert epoch seconds to ISO string. None -> None."""
    if epoch is None or epoch == "":
        return None
    try:
        e = int(epoch)
        return datetime.fromtimestamp(e, tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _flatten_review_from_api(d: dict) -> dict[str, Any] | None:
    """Flatten a Tiki reviews API row (list element of `data`).

    Key map to sample.csv columns:
      id -> comment_id
      created_by.{id,name,full_name,region,avatar_url,purchased_at} ->
          customer_id, customer_name, customer_full_name,
          customer_region, customer_avatar_url, purchased_at
      spid -> seller_product_id
      seller.{id,name} -> seller_id, seller_name
      created_at (epoch) -> created_at (ISO)
    """
    if not isinstance(d, dict):
        return None
    cid = d.get("id")
    if cid is None:
        return None

    created_by = d.get("created_by") or {}
    seller = d.get("seller") or {}
    images = d.get("images") or []

    return {
        "comment_id": _str_or_none(cid),
        "customer_id": _str_or_none(d.get("customer_id") or created_by.get("id")),
        "customer_name": _str_or_none(created_by.get("name")),
        "customer_full_name": _str_or_none(created_by.get("full_name")),
        "customer_region": _str_or_none(created_by.get("region")),
        "customer_avatar_url": _str_or_none(created_by.get("avatar_url")),
        "rating": _coerce_int(d.get("rating")),
        "title": _str_or_none(d.get("title")),
        "content": _str_or_none(d.get("content")) or "",
        "thank_count": _coerce_int(d.get("thank_count")),
        "score": (
            float(d.get("score"))
            if isinstance(d.get("score"), (int, float))
            else None
        ),
        "status": _str_or_none(d.get("status")),
        "is_photo": (len(images) > 0) if images is not None else d.get("is_photo"),
        "created_at": _epoch_to_iso(d.get("created_at")),
        "created_at_text": _str_or_none(
            d.get("timeline", {}).get("created_at_text") if isinstance(d.get("timeline"), dict) else None
        ),
        "purchased_at": _epoch_to_iso(
            d.get("purchased_at") or created_by.get("purchased_at")
        ),
        "seller_product_id": _str_or_none(d.get("spid")),
        "seller_id": _str_or_none(seller.get("id")),
        "seller_name": _str_or_none(seller.get("name")),
    }


def parse_reviews_api(
    blob: dict,
    *,
    product_id: str = "",
    page_no: int = 1,
    position_start: int = 1,
) -> list[dict[str, Any]]:
    """Parse the body of `https://tiki.vn/api/v2/reviews?...`.

    Returns flat wide-row dicts with `platform`, `product_id`, `page_no`,
    `position`, `crawled_at` filled in.
    """
    if not isinstance(blob, dict):
        return []
    items = blob.get("data") or []
    if not isinstance(items, list):
        return []
    crawled = _utcnow().isoformat()
    out: list[dict[str, Any]] = []
    pos = position_start
    seen: set[str] = set()
    for raw in items:
        r = _flatten_review_from_api(raw)
        if r is None or not r["comment_id"]:
            continue
        if r["comment_id"] in seen:
            continue
        seen.add(r["comment_id"])
        r.update({
            "platform": Platform.TIKI.value,
            "product_id": product_id,
            "page_no": page_no,
            "position": pos,
            "crawled_at": crawled,
        })
        out.append(r)
        pos += 1
    return out
