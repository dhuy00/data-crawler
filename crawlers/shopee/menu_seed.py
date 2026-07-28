"""Curated menu seed for Shopee.

Shopee has no public category-tree API. The slug/URL pairs below cover
the same six default categories used elsewhere in this project. Live
refinement via Playwright is on the Phase 2+ roadmap.
"""

from __future__ import annotations

# Each entry: (level, slug, name, parent_slug, url_path)
# Level 1 = top category (we don't include the synthetic root).
SHOPEE_MENU_SEED: list[tuple[int, str, str, str | None, str]] = [
    # Điện thoại
    (1, "dien-thoai",         "Điện thoại & Phụ kiện", None,
     "https://shopee.vn/dien-thoai-phu-kien-cat"),
    (2, "dt-dien-thoai",      "Điện thoại thông minh", "dien-thoai",
     "https://shopee.vn/dien-thoai-cat"),
    (2, "dt-phu-kien",        "Phụ kiện điện thoại",   "dien-thoai",
     "https://shopee.vn/phu-kien-dien-thoai-cat"),
    # Laptop
    (1, "laptop",             "Laptop & Máy tính",     None,
     "https://shopee.vn/may-tinh-laptop-cat"),
    (2, "lt-laptop",          "Laptop",                "laptop",
     "https://shopee.vn/laptop-cat"),
    (2, "lt-phu-kien",        "Phụ kiện máy tính",     "laptop",
     "https://shopee.vn/phu-kien-may-tinh-cat"),
    # Thời trang nam
    (1, "thoi-trang-nam",     "Thời trang nam",        None,
     "https://shopee.vn/thoi-trang-nam-cat"),
    (2, "tt-nam-ao",          "Áo nam",                "thoi-trang-nam",
     "https://shopee.vn/ao-nam-cat"),
    (2, "tt-nam-quan",        "Quần nam",              "thoi-trang-nam",
     "https://shopee.vn/quan-nam-cat"),
    # Thời trang nữ
    (1, "thoi-trang-nu",      "Thời trang nữ",         None,
     "https://shopee.vn/thoi-trang-nu-cat"),
    (2, "tt-nu-ao",           "Áo nữ",                 "thoi-trang-nu",
     "https://shopee.vn/ao-nu-cat"),
    (2, "tt-nu-vay",          "Váy nữ",                "thoi-trang-nu",
     "https://shopee.vn/vay-nu-cat"),
    # Mỹ phẩm
    (1, "my-pham",            "Mỹ phẩm & Sắc đẹp",    None,
     "https://shopee.vn/my-pham-cat"),
    (2, "mp-trang-diem",      "Trang điểm",            "my-pham",
     "https://shopee.vn/trang-diem-cat"),
    (2, "mp-cham-soc-da",     "Chăm sóc da",           "my-pham",
     "https://shopee.vn/cham-soc-da-cat"),
    # Đồ gia dụng
    (1, "do-gia-dung",        "Đồ gia dụng",           None,
     "https://shopee.vn/do-gia-dung-cat"),
    (2, "dg-bep",             "Đồ dùng nhà bếp",       "do-gia-dung",
     "https://shopee.vn/do-dung-nha-bep-cat"),
    (2, "dg-noi-that",        "Nội thất",              "do-gia-dung",
     "https://shopee.vn/noi-that-cat"),
]
