"""Curated menu seed for Lazada Vietnam."""

from __future__ import annotations

LAZADA_MENU_SEED: list[tuple[int, str, str, str | None, str]] = [
    # Điện thoại
    (1, "dien-thoai",      "Điện thoại & Tablet",       None,
     "https://www.lazada.vn/dien-thoai-di-dong/"),
    (2, "dt-smartphone",   "Smartphone",                "dien-thoai",
     "https://www.lazada.vn/dien-thoai-smartphone/"),
    (2, "dt-phu-kien",     "Phụ kiện điện thoại",       "dien-thoai",
     "https://www.lazada.vn/phu-kien-dien-thoai/"),
    # Laptop
    (1, "laptop",          "Laptop & Máy tính",         None,
     "https://www.lazada.vn/may-tinh-laptop/"),
    (2, "lt-laptop",       "Laptop",                    "laptop",
     "https://www.lazada.vn/laptop/"),
    (2, "lt-phu-kien",     "Phụ kiện máy tính",         "laptop",
     "https://www.lazada.vn/phu-kien-may-tinh/"),
    # Thời trang nam
    (1, "thoi-trang-nam",  "Thời trang nam",            None,
     "https://www.lazada.vn/thoi-trang-nam/"),
    (2, "tt-nam-ao",       "Áo nam",                    "thoi-trang-nam",
     "https://www.lazada.vn/ao-nam/"),
    (2, "tt-nam-quan",     "Quần nam",                  "thoi-trang-nam",
     "https://www.lazada.vn/quan-nam/"),
    # Thời trang nữ
    (1, "thoi-trang-nu",   "Thời trang nữ",             None,
     "https://www.lazada.vn/thoi-trang-nu/"),
    (2, "tt-nu-ao",        "Áo nữ",                     "thoi-trang-nu",
     "https://www.lazada.vn/ao-nu/"),
    (2, "tt-nu-dam",       "Đầm & váy",                 "thoi-trang-nu",
     "https://www.lazada.vn/dam-vay/"),
    # Mỹ phẩm
    (1, "my-pham",         "Mỹ phẩm & Sắc đẹp",        None,
     "https://www.lazada.vn/my-pham/"),
    (2, "mp-trang-diem",   "Trang điểm",                "my-pham",
     "https://www.lazada.vn/trang-diem/"),
    (2, "mp-cham-soc-da",  "Chăm sóc da",               "my-pham",
     "https://www.lazada.vn/cham-soc-da/"),
    # Đồ gia dụng
    (1, "do-gia-dung",     "Đồ gia dụng",               None,
     "https://www.lazada.vn/do-gia-dung/"),
    (2, "dg-bep",          "Đồ dùng nhà bếp",           "do-gia-dung",
     "https://www.lazada.vn/do-dung-nha-bep/"),
    (2, "dg-noi-that",     "Nội thất",                  "do-gia-dung",
     "https://www.lazada.vn/noi-that/"),
]
