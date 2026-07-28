"""Curated menu seed for Sendo Vietnam."""

from __future__ import annotations

SENDO_MENU_SEED: list[tuple[int, str, str, str | None, str]] = [
    # Điện thoại
    (1, "dien-thoai",      "Điện thoại & Tablet",       None,
     "https://www.sendo.vn/dien-thoai"),
    (2, "dt-smartphone",   "Smartphone",                "dien-thoai",
     "https://www.sendo.vn/dien-thoai/smartphone"),
    (2, "dt-phu-kien",     "Phụ kiện điện thoại",       "dien-thoai",
     "https://www.sendo.vn/dien-thoai/phu-kien"),
    # Laptop
    (1, "laptop",          "Laptop & Máy tính",         None,
     "https://www.sendo.vn/laptop-may-tinh"),
    (2, "lt-laptop",       "Laptop",                    "laptop",
     "https://www.sendo.vn/laptop-may-tinh/laptop"),
    (2, "lt-phu-kien",     "Phụ kiện máy tính",         "laptop",
     "https://www.sendo.vn/laptop-may-tinh/phu-kien"),
    # Thời trang nam
    (1, "thoi-trang-nam",  "Thời trang nam",            None,
     "https://www.sendo.vn/thoi-trang-nam"),
    (2, "tt-nam-ao",       "Áo nam",                    "thoi-trang-nam",
     "https://www.sendo.vn/thoi-trang-nam/ao"),
    (2, "tt-nam-quan",     "Quần nam",                  "thoi-trang-nam",
     "https://www.sendo.vn/thoi-trang-nam/quan"),
    # Thời trang nữ
    (1, "thoi-trang-nu",   "Thời trang nữ",             None,
     "https://www.sendo.vn/thoi-trang-nu"),
    (2, "tt-nu-ao",        "Áo nữ",                     "thoi-trang-nu",
     "https://www.sendo.vn/thoi-trang-nu/ao"),
    (2, "tt-nu-vay",       "Váy nữ",                    "thoi-trang-nu",
     "https://www.sendo.vn/thoi-trang-nu/vay-dam"),
    # Mỹ phẩm
    (1, "my-pham",         "Mỹ phẩm & Sắc đẹp",        None,
     "https://www.sendo.vn/my-pham"),
    (2, "mp-trang-diem",   "Trang điểm",                "my-pham",
     "https://www.sendo.vn/my-pham/trang-diem"),
    (2, "mp-cham-soc-da",  "Chăm sóc da",               "my-pham",
     "https://www.sendo.vn/my-pham/cham-soc-da"),
    # Đồ gia dụng
    (1, "do-gia-dung",     "Đồ gia dụng",               None,
     "https://www.sendo.vn/do-gia-dung"),
    (2, "dg-bep",          "Đồ dùng nhà bếp",           "do-gia-dung",
     "https://www.sendo.vn/do-gia-dung/nha-bep"),
    (2, "dg-noi-that",     "Nội thất",                  "do-gia-dung",
     "https://www.sendo.vn/do-gia-dung/noi-that"),
]
