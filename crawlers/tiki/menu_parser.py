"""Parse Tiki menu data into the canonical `Category` model.

Two input shapes are supported:
1. A flat list of dicts (the static seed in `menu_seed.py`).
2. The HTML of a Tiki listing page that embeds a `__NEXT_DATA__` JSON blob.

For the live HTML path, we extract the embedded JSON and pull the category
breadcrumb if present. If the blob does not contain category info (which is
common on the home page), we return an empty list — the caller falls back
to the static seed.
"""

from __future__ import annotations

import json
import re
from typing import Iterable

from models import Category, Platform

_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.DOTALL
)


def parse_seed(rows: Iterable[dict]) -> list[Category]:
    """Convert the static seed rows into Category objects (Platform.TIKI)."""
    out: list[Category] = []
    for row in rows:
        try:
            out.append(
                Category(
                    platform=Platform.TIKI,
                    category_id=str(row["id"]),
                    name=row["name"],
                    parent_id=str(row["parent_id"]) if row.get("parent_id") is not None else None,
                    level=int(row["level"]),
                    url=row["url"],
                )
            )
        except Exception:  # noqa: BLE001 — defensive: skip malformed rows
            continue
    return out


def parse_menu_html(html: str, *, page_url: str = "") -> list[Category]:
    """Try to extract breadcrumb categories from a Tiki HTML page.

    Returns an empty list when the page does not embed enough structure
    (home page, error pages, etc.). Callers should fall back to the seed.
    """
    m = _NEXT_DATA_RE.search(html or "")
    if not m:
        return []
    try:
        blob = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []

    found: list[Category] = []
    # Breadcrumbs are usually under props.pageProps.breadcrumb
    bc = (
        blob.get("props", {}).get("pageProps", {}).get("breadcrumb")
        or blob.get("props", {}).get("pageProps", {}).get("data", {}).get("breadcrumb")
    )
    if isinstance(bc, list):
        for i, item in enumerate(bc, start=1):
            if not isinstance(item, dict):
                continue
            name = item.get("text") or item.get("name") or ""
            url = item.get("href") or item.get("url") or page_url
            cat_id = item.get("category_id") or item.get("id") or str(i)
            if not name or not url:
                continue
            found.append(
                Category(
                    platform=Platform.TIKI,
                    category_id=str(cat_id),
                    name=name,
                    parent_id=str(bc[i - 2]["category_id"]) if i > 1 and isinstance(bc[i - 2], dict) else None,
                    level=i,
                    url=url,
                )
            )
    return found
