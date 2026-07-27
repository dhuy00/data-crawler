"""Static constants — domain URLs, default UAs, default category slugs.

Anything that needs `Settings` indirection belongs in `settings.py`, not here.
"""

from __future__ import annotations

from models.platform import Platform


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

PLATFORM_DOMAINS: dict[Platform, str] = {
    Platform.TIKI: "https://tiki.vn",
    Platform.SHOPEE: "https://shopee.vn",
    Platform.LAZADA: "https://www.lazada.vn",
    Platform.SENDO: "https://www.sendo.vn",
}

# Default category slugs each pipeline can run against. Phases 1-4 will
# populate concrete crawl paths for each of these on each platform.
DEFAULT_CATEGORIES: dict[str, str] = {
    "dien-thoai": "Điện thoại",
    "laptop": "Laptop",
    "thoi-trang-nam": "Thời trang nam",
    "thoi-trang-nu": "Thời trang nữ",
    "my-pham": "Mỹ phẩm",
    "do-gia-dung": "Đồ gia dụng",
}
