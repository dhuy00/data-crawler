"""Static Tiki menu seed.

Tiki's public JSON menu endpoint (`/api/v2/menu`, `/ajax-navigation/category`)
is no longer reachable as of mid-2026. To keep Phase 1 shippable without a
live network probe, we ship a small curated tree of common parent categories
with their public URLs. Crawlers that need a deeper tree should use
`BrowserManager` and parse the live DOM (TODO Phase 2+).

Structure: a flat list of dicts with `id, name, url, parent_id, level`.
"""

from __future__ import annotations

from typing import Optional

TIKI_MENU_SEED: list[dict] = [
    # Level 1
    {"id": 1, "name": "Đồ Chơi - Mẹ & Bé", "url": "https://tiki.vn/me-va-be", "parent_id": None, "level": 1},
    {"id": 2, "name": "Điện Thoại - Máy Tính Bảng", "url": "https://tiki.vn/dien-thoai-may-tinh-bang", "parent_id": None, "level": 1},
    {"id": 3, "name": "Laptop - Thiết bị IT", "url": "https://tiki.vn/laptop-may-vi-tinh", "parent_id": None, "level": 1},
    {"id": 4, "name": "Thời trang nam", "url": "https://tiki.vn/thoi-trang-nam", "parent_id": None, "level": 1},
    {"id": 5, "name": "Thời trang nữ", "url": "https://tiki.vn/thoi-trang-nu", "parent_id": None, "level": 1},
    {"id": 6, "name": "Mỹ phẩm - Làm đẹp", "url": "https://tiki.vn/my-pham-lam-dep", "parent_id": None, "level": 1},
    {"id": 7, "name": "Đồ gia dụng", "url": "https://tiki.vn/do-gia-dung", "parent_id": None, "level": 1},
    {"id": 8, "name": "Nhà sách - Tiki Books", "url": "https://tiki.vn/nha-sach-tiki", "parent_id": None, "level": 1},

    # Level 2 under Điện Thoại
    {"id": 100, "name": "Điện thoại Smartphone", "url": "https://tiki.vn/dien-thoai-smartphone", "parent_id": 2, "level": 2},
    {"id": 101, "name": "Máy tính bảng", "url": "https://tiki.vn/may-tinh-bang", "parent_id": 2, "level": 2},
    {"id": 102, "name": "Phụ kiện điện thoại", "url": "https://tiki.vn/phu-kien-dien-thoai", "parent_id": 2, "level": 2},

    # Level 2 under Laptop
    {"id": 200, "name": "Laptop", "url": "https://tiki.vn/laptop", "parent_id": 3, "level": 2},
    {"id": 201, "name": "Laptop Gaming", "url": "https://tiki.vn/laptop-gaming", "parent_id": 3, "level": 2},
    {"id": 202, "name": "Phụ kiện laptop", "url": "https://tiki.vn/phu-kien-laptop", "parent_id": 3, "level": 2},

    # Level 2 under Thời trang nữ
    {"id": 400, "name": "Đầm nữ", "url": "https://tiki.vn/dam", "parent_id": 5, "level": 2},
    {"id": 401, "name": "Áo nữ", "url": "https://tiki.vn/ao-nu", "parent_id": 5, "level": 2},
    {"id": 402, "name": "Quần nữ", "url": "https://tiki.vn/quan-nu", "parent_id": 5, "level": 2},

    # Level 2 under Đồ gia dụng
    {"id": 700, "name": "Đồ dùng nhà bếp", "url": "https://tiki.vn/do-dung-nha-bep", "parent_id": 7, "level": 2},
    {"id": 701, "name": "Đồ dùng phòng ngủ", "url": "https://tiki.vn/do-dung-phong-ngu", "parent_id": 7, "level": 2},
]


def find_seed_category(name_or_url: str) -> Optional[dict]:
    """Look up a seed category by name or URL (case-insensitive)."""
    needle = name_or_url.strip().lower()
    for cat in TIKI_MENU_SEED:
        if cat["name"].lower() == needle or cat["url"].lower() == needle:
            return cat
    return None


def seed_children(parent_id: int) -> list[dict]:
    """Return categories whose parent_id == parent_id."""
    return [c for c in TIKI_MENU_SEED if c["parent_id"] == parent_id]
