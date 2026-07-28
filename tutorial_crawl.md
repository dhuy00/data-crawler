# Tutorial — Crawl dữ liệu với data-crawler

Hướng dẫn từng bước để cài đặt, chạy, và mở rộng crawler. Sau khi đọc xong bạn sẽ biết:

1. Cách cài môi trường.
2. Cách chạy từng mode cho từng sàn.
3. Cách crawl **nhiều sàn cùng lúc** (multi-platform).
4. Cách đọc output CSV / SQLite / JSONL.
5. Cách thêm 1 sàn mới (plugin).

Tham khảo: `plan.md` (thiết kế tổng thể), `progress.md` (nhật ký triển khai), `README.md` (tóm tắt nhanh), `test_turtorial.md` (hướng dẫn test chi tiết).

---

## 1. Môi trường

**Yêu cầu**: Python ≥ 3.10, Windows PowerShell hoặc bash.

```powershell
cd data-crawler
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

# Chỉ cần khi 1 sàn nào đó trigger Playwright fallback
.venv\Scripts\python.exe -m playwright install chromium
```

**File `.env`** (tùy chọn): copy từ `.env.example` rồi chỉnh User-Agent nếu muốn.

```powershell
copy .env.example .env
```

---

## 2. Các khái niệm cốt lõi

- **Pipeline** = 1 chuỗi bước (`menu` → `products` → `comments`).
- **Platform** = 1 sàn TMĐT (`tiki`, `shopee`, `lazada`, `sendo`).
- **Mode** = loại pipeline (`menu`, `products_from_menu`, `comments_from_products`, `keyword`, `full`).
- **Crawler** = class Python implement `BaseCrawler`, đăng ký qua `@register(Platform.X)`.
- **3 dạng output**: CSV (bảng), SQLite (DB normalized), JSONL (raw, mỗi dòng 1 object).

Mỗi run tạo thư mục con dạng `<platform>_<mode>_<YYYYMMDD_HHMMSS>/`.

---

## 3. Chạy từng sàn

### 3.1 Tiki

```powershell
# Menu (19 categories từ seed)
.venv\Scripts\python.exe main.py --platform tiki --mode menu --output-dir outputs/tiki/menu

# Keyword: tìm "iphone", lấy 10 SP + 10 review đầu
.venv\Scripts\python.exe main.py --platform tiki --mode keyword --keywords "iphone"

# Full end-to-end: menu → products → comments
.venv\Scripts\python.exe main.py --platform tiki --mode full
```

### 3.2 Shopee

```powershell
# Menu (18 categories từ seed)
.venv\Scripts\python.exe main.py --platform shopee --mode menu

# Keyword
.venv\Scripts\python.exe main.py --platform shopee --mode keyword --keywords "iphone" --no-comments
```

> **Ghi chú thực tế**: API công khai của Shopee hay đổi. Khi gặp lỗi 404, crawler log warning và fallback Playwright. Xem `progress.md` để biết endpoint nào đã từng hoạt động.

### 3.3 Lazada

```powershell
.venv\Scripts\python.exe main.py --platform lazada --mode menu
.venv\Scripts\python.exe main.py --platform lazada --mode keyword --keywords "tai-nghe"
```

### 3.4 Sendo

```powershell
.venv\Scripts\python.exe main.py --platform sendo --mode menu
.venv\Scripts\python.exe main.py --platform sendo --mode keyword --keywords "iphone"
```

---

## 4. Chạy nhiều sàn (multi-platform)

Chỉ áp dụng cho mode **`full`** và **`keyword`**. Các mode khác chạy đơn lẻ per sàn.

```powershell
# Cả 4 sàn, keyword "iphone", bỏ comments
.venv\Scripts\python.exe main.py --platforms tiki,shopee,lazada,sendo --mode keyword --keywords "iphone" --no-comments

# 2 sàn, lấy comments
.venv\Scripts\python.exe main.py --platforms tiki,shopee --mode keyword --keywords "iphone,airpods"

# Full pipeline cho 2 sàn
.venv\Scripts\python.exe main.py --platforms tiki,shopee --mode full
```

**Output**: thư mục riêng cho mỗi sàn (vd. `tiki_keyword_xxx/`, `shopee_keyword_xxx/`) + log tổng hợp `platforms=[...] product_count=N`. Nếu 1 sàn fail, các sàn khác vẫn chạy tiếp, error ghi vào `per_platform[<sàn>].error`.

---

## 5. Đọc kết quả

### CSV
```powershell
# Mở bằng Excel / pandas
.venv\Scripts\python.exe -c "import pandas as pd; print(pd.read_csv('outputs/tiki_keyword_*/keyword_iphone_top_*.csv').head())"
```

### SQLite
```powershell
.venv\Scripts\python.exe -c "
import sqlite3, pandas as pd
con = sqlite3.connect('outputs/tiki_keyword_*/crawler.db')
print(pd.read_sql('SELECT * FROM products LIMIT 5', con))
print(pd.read_sql('SELECT * FROM comments LIMIT 5', con))
"
```

Schema ở `plan.md` §5. Bảng chính: `products`, `categories`, `comments`, `runs`. UNIQUE constraint `(platform, product_id)` đảm bảo idempotent.

### JSON Lines (raw)
```powershell
# Mỗi dòng là 1 JSON object — dễ grep, load streaming
Get-Content outputs/tiki_keyword_*/raw/keyword_iphone_top_*.jsonl -TotalCount 3
```

---

## 6. Tùy chọn hữu ích

| Flag | Ý nghĩa | Ví dụ |
|---|---|---|
| `--limit N` | Giới hạn categories/products crawl | `--limit 5` |
| `--max-pages N` | Số trang tối đa mỗi category | `--max-pages 3` |
| `--max-products-per-keyword N` | Top N cho keyword mode | `--max-products-per-keyword 20` |
| `--no-comments` | Bỏ crawl comments | (flag không cần value) |
| `--level 1\|2\|3` | Độ sâu menu | `--level 2` |
| `--input-file PATH` | CSV/JSONL input (cho `products_from_menu`, `comments_from_products`) | `--input-file outputs/menu.csv` |
| `--output-dir PATH` | Thư mục output | `--output-dir outputs/2026-07-28` |

---

## 6.5. Pipeline đặc biệt — `category_reviews` (3 file CSV mỗi category)

Pipeline tiêu chuẩn (mục 3–4) ghi **mỗi entity 1 file**: 1 file products, 1 file comments/1 SP, 1 file menu. Có 1 case riêng cần **mỗi category 1 file CSV gộp product + review wide-row**: đó là `category_reviews_pipeline`.

### Khi nào dùng

Khi bạn cần xuất bảng phẳng kiểu `sample.csv` — mỗi hàng là 1 review, mỗi hàng đầy đủ thông tin product + review + category tree. Phù hợp để import Excel/Power BI/Tableau.

### Cách chạy

```powershell
# Mặc định: 3 L1 đầu, 5 SP/category, 20 reviews/SP, output `outputs/cat_reviews/`
.venv\Scripts\python.exe -m pipelines.category_reviews_pipeline --platform tiki

# Chỉ định categories cụ thể (id từ menu seed) + số SP/category
.venv\Scripts/ python.exe -m pipelines.category_reviews_pipeline --platform tiki --category-ids 2,3,4 --max-products-per-category 3 --output-dir outputs/cat_reviews
```

### Flow

1. `crawler.fetch_menu(level=3)` → 19 categories (seed Tiki).
2. Lọc 3 categories (mặc định 3 L1 đầu; hoặc theo `--category-ids`).
3. Với mỗi category, gọi `crawler.search(category_name)` → parse `__NEXT_DATA__` lấy raw product dicts (giữ `seller_id`, `brand`, ...).
4. Với mỗi product, gọi `crawler.fetch_reviews_wide()` → gọi `GET /api/v2/reviews?product_id={pid}` trực tiếp → parse JSON.
5. Join product + review + category vào **1 dict wide** rồi append row vào CSV.

### Output schema (42 cột)

```
1-12   Product:      product_id, seller_product_id, product_name, product_url,
                     product_price, product_original_price, product_rating_average,
                     product_review_count, product_sold_count, product_thumbnail_url,
                     product_brand, product_categories_id
13-20  Category tree: category_id, category_url, category_name, category_level,
                     category_parent_id, lv1_name, lv2_name, lv3_name
21-22  Seller:       seller_id, seller_name
23-40  Review:       comment_id, comment_page, comment_position, customer_id,
                     customer_name, customer_full_name, customer_region,
                     customer_avatar_url, rating, title, content, thank_count,
                     score, status, is_photo, created_at, created_at_text,
                     purchased_at
41-42  Metadata:     platform, crawled_at
```

### Output files

```
outputs/cat_reviews/
├── tiki_2_reviews_<run_id>.csv    # ~44 rows × 42 cols (Điện Thoại)
├── tiki_3_reviews_<run_id>.csv    # ~6 rows × 42 cols  (Laptop)
├── tiki_4_reviews_<run_id>.csv    # ~17 rows × 42 cols (Thời trang nam)
└── raw/
    ├── tiki_2_reviews_<run_id>.jsonl
    ├── tiki_3_reviews_<run_id>.jsonl
    └── tiki_4_reviews_<run_id>.jsonl
```

Mỗi product có thể không có review (API Tiki trả `reviews_count=0` cho vài SP) — khi đó pipeline vẫn ghi 1 placeholder row chỉ chứa thông tin product (các cột review = null) để file không rỗng.

### Code liên quan

| File | Vai trò |
|---|---|
| `pipelines/category_reviews_pipeline.py` | Pipeline end-to-end 3 categories. |
| `crawlers/tiki/comment_parser.py` | `parse_reviews_api()` — flatten `/api/v2/reviews` JSON. |
| `crawlers/tiki/tiki_crawler.py` | `fetch_reviews_wide()` — gọi API + fallback HTML. |
| `crawlers/tiki/product_parser.py` | `raw_extract_product_wide()` — flatten product dict. |

### Caveats

- **Cột `category_url`**: là URL L1 (`me-va-be`, `dien-thoai-may-tinh-bang`...) vì pipeline chọn categories ở L1.
- **`created_at` ISO, `created_at_text` trống**: Tiki API trả epoch seconds, không có human-readable string. Nếu cần `created_at_text`, phải parse từ HTML chi tiết.
- **Laptop (id=3) ít rows**: nhiều SP search "Laptop" trả `reviews_count=0` từ API → placeholder row only.

---

## 7. Thêm sàn mới (plugin)

Mục tiêu: thêm `tiktokshop` (hay bất kỳ sàn nào) mà không sửa core. Làm theo 6 bước:

### Bước 1: thêm vào enum

`models/platform.py`:
```python
class Platform(str, Enum):
    TIKI = "tiki"
    SHOPEE = "shopee"
    LAZADA = "lazada"
    SENDO = "sendo"
    TIKTOKSHOP = "tiktokshop"   # ← thêm dòng này
```

### Bước 2: thêm domain

`config/constants.py`:
```python
PLATFORM_DOMAINS: dict[Platform, str] = {
    ...
    Platform.TIKTOKSHOP: "https://shop.tiktok.vn",
}
```

### Bước 3: tạo package

```
crawlers/tiktokshop/
├── __init__.py          # from . import tiktokshop_crawler  (để trigger @register)
├── menu_seed.py         # curated categories
├── menu_parser.py
├── product_parser.py
├── comment_parser.py
├── keyword_parser.py
└── tiktokshop_crawler.py
```

### Bước 4: implement crawler

`crawlers/tiktokshop/tiktokshop_crawler.py`:
```python
from core.http_client import HttpClient
from crawlers.base import BaseCrawler
from models import Category, Comment, Platform, Product
from services.platform_registry import register

from .menu_parser import parse_seed
from .menu_seed import TIKTOKSHOP_MENU_SEED
from .product_parser import parse_products_json
from .comment_parser import parse_comments_json


@register(Platform.TIKTOKSHOP)
class TiktokshopCrawler(BaseCrawler):
    platform = Platform.TIKTOKSHOP
    comment_supported = True   # False nếu không có public comment API
    BASE_URL = "https://shop.tiktok.vn"

    def __init__(self, http_client=None, rate_per_second=1.0):
        super().__init__()
        self.http = http_client or HttpClient()

    async def fetch_menu(self, level=3):
        all_seeded = parse_seed(TIKTOKSHOP_MENU_SEED)
        return all_seeded if level >= 3 else [c for c in all_seeded if c.level <= level]

    async def fetch_products(self, category_url, page=1, page_size=20):
        # Your JSON/HTML scraping logic here
        ...

    async def search(self, keyword, page=1, page_size=20):
        ...
```

### Bước 5: đăng ký import ở main.py

`main.py`:
```python
import crawlers.tiktokshop  # noqa: F401
```

### Bước 6: test

```powershell
.venv\Scripts\python.exe main.py --platform tiktokshop --mode menu
.venv\Scripts\python.exe -m pytest tests/test_tiktokshop_parsers.py -v
```

---

## 8. Troubleshooting

| Lỗi | Nguyên nhân | Cách xử lý |
|---|---|---|
| `No crawler registered for platform 'X'` | Chưa import `crawlers.X` trong `main.py` và `crawlers/X/__init__.py` | Thêm `from . import X_crawler` vào `__init__.py` + import `crawlers.X` trong `main.py`. |
| `HTTP 404` cho Shopee/Lazada/Sendo | Sàn đổi API path | Sửa endpoint trong `<sàn>_crawler.py`, hoặc Playwright fallback sẽ tự kích hoạt. |
| `ValidationError: price` với NaN | `_coerce_float` chưa check NaN/inf | Đã fix trong 3 parsers (shopee/lazada/sendo); nếu tự viết crawler hãy dùng `math.isfinite`. |
| `Playwright not installed` | Chưa cài browser | `.venv\Scripts\python.exe -m playwright install chromium`. |
| Multi-platform không chạy song song | **By design** — Phase 5 chọn sequential để giữ đơn giản. Đổi sang `asyncio.gather` nếu cần (tự modify `multi_platform_pipeline.py`). |
| Smoke test skip | Không có `RUN_NETWORK_TESTS=1` | Có 2 smoke tests ở `tests/smoke/`; skip là hành vi bình thường. |

---

## 9. Cấu trúc thư mục (tóm tắt)

```
data-crawler/
├── main.py                       # CLI entry
├── config/                       # constants, settings
├── core/                         # http_client, browser, storage, retry, logger
├── models/                       # Pydantic: Product, Comment, Category, Platform
├── crawlers/
│   ├── base.py                   # BaseCrawler (ABC)
│   ├── tiki/                     # Phase 1
│   ├── shopee/                   # Phase 2
│   ├── lazada/                   # Phase 3
│   └── sendo/                    # Phase 4
├── services/
│   └── platform_registry.py      # @register(Platform.X)
├── pipelines/
│   ├── menu_pipeline.py
│   ├── products_from_menu_pipeline.py
│   ├── comments_from_products_pipeline.py
│   ├── keyword_pipeline.py
│   ├── full_pipeline.py
│   └── multi_platform_pipeline.py   # Phase 5
├── tests/                        # 145 unit + 2 smoke
├── outputs/                      # mỗi run = 1 subfolder
├── plan.md progress.md           # design + nhật ký
└── tutorial_crawl.md             # file này
```

---

## 10. Workflow đề xuất cho người mới

1. **Khám phá**: chạy `python main.py --platform tiki --mode menu` (Tiki ổn định nhất).
2. **Smoke keyword**: `python main.py --platform tiki --mode keyword --keywords "iphone" --no-comments`.
3. **Full 1 sàn**: `python main.py --platform tiki --mode full`.
4. **Multi**: `python main.py --platforms tiki,shopee --mode keyword --keywords "iphone" --no-comments`.
5. **Đọc output**: mở CSV / `outputs/<run>/crawler.db` / `raw/*.jsonl`.
6. **Tùy biến**: thêm flag, sửa parser, hoặc viết crawler cho sàn mới (mục 7).
