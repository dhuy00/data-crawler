# Plan — Multi-Platform Vietnam E-Commerce Crawler

> Status: **completed** (Phase 0–6 đã xong, xem `progress.md` để biết chi tiết và ghi chú thực tế).

## 1. Bối cảnh & mục tiêu

Project cũ (`data-crawler`) chỉ crawl **Tiki.vn** với menu 3 cấp, sản phẩm, bình luận và ranking từ khóa. Mục tiêu của project mới là **tái sử dụng toàn bộ techstack & kinh nghiệm** đã có, nhưng mở rộng sang nhiều sàn và nhiều ngành hàng.

### Yêu cầu chức năng
1. Crawl dữ liệu từ **4 sàn**: Tiki, Shopee, Lazada, Sendo.
2. Hỗ trợ **nhiều ngành hàng** (mặc định: Điện thoại, Laptop, Thời trang nam, Thời trang nữ, Mỹ phẩm, Đồ gia dụng — người dùng có thể cấu hình).
3. Cho mỗi sàn × mỗi ngành, hỗ trợ các chế độ:
   - `menu` — menu danh mục 3 cấp.
   - `products` — danh sách sản phẩm theo danh mục.
   - `comments` — bình luận / đánh giá cho từng sản phẩm.
   - `keyword` — tìm theo từ khóa, lấy top sản phẩm + top bình luận.
   - `full` — menu → products → comments.
4. Cho phép **chạy pipeline chung** trên nhiều sàn cùng lúc (vd. `--platforms tiki,shopee --category "dien-thoai"`).
5. Dữ liệu đầu ra:
   - **CSV** cho mỗi sàn × ngành (định dạng giống project cũ).
   - **SQLite** lưu dữ liệu normalized (một DB chung, schema thống nhất).
   - **JSON Lines** cho dữ liệu thô (hỗ trợ streaming, dễ debug).
6. Logging chuẩn với `loguru` + retry với `tenacity` + rate-limit per-domain.
7. Đảm bảo **CLI đơn giản**, ví dụ:
   - `python main.py --platforms tiki,shopee --mode full --category "dien-thoai"`
   - `python main.py --platform shopee --mode keyword --keywords "iphone,airpods"`

### Yêu cầu phi chức năng
- **Techstack giữ nguyên**: `playwright`, `requests`, `pandas`, `pydantic`, `tenacity`, `pyarrow`, `tqdm`, `loguru`, `python-dotenv`, `pytest`.
- **Python ≥ 3.10**.
- Code phải chạy được trên **Windows** (PowerShell) như project cũ.
- Mỗi sàn phải là một **plugin độc lập**, thêm sàn mới không sửa core pipeline.
- Tuân thủ `robots.txt`, có `User-Agent` đặt trong `.env`, có delay giữa request.
- Có test mức **unit + smoke** cho từng adapter sàn.

### Phạm vi ngoài (out-of-scope)
- Không login, không bypass CAPTCHA, không crawl dữ liệu cá nhân.
- Không cung cấp giao diện web (chỉ CLI + file outputs).
- Không dựng Airflow / scheduler — để chạy thủ công hoặc `cron`.

---

## 2. Sơ đồ kiến trúc (Plugin-based Multi-Crawler)

```
                    ┌──────────────────────────────┐
                    │            main.py           │   CLI argparse
                    └─────────────┬────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────────┐
                    │  pipelines/ (orchestrator)    │   menu / products / comments /
                    │                              │   keyword / full
                    └─────────────┬────────────────┘
                                  │  gọi qua interface chung
                                  ▼
                    ┌──────────────────────────────┐
                    │  crawlers/<platform>/        │   Plugin layer — mỗi sàn
                    │  (base_crawler + adapters)   │   implement cùng interface
                    └─────────────┬────────────────┘
                                  │
       ┌──────────────┬───────────┼───────────────┬───────────────┐
       ▼              ▼           ▼               ▼               ▼
  ┌─────────┐   ┌──────────┐ ┌─────────┐   ┌──────────┐   (thêm sàn sau)
  │  tiki   │   │  shopee  │ │ lazada  │   │  sendo   │
  └─────────┘   └──────────┘ └─────────┘   └──────────┘

   Shared bên dưới:
   - core/        (http_client, browser, retry_handler, logger, storage)
   - services/    (ranking, comment_validator, category_lookup)
   - models/      (Pydantic: Product, Comment, Category, Platform enum)
   - config/      (settings, constants, .env loader)
```

### Nguyên tắc plugin
- `crawlers/base.py` định nghĩa abstract class:
  - `async fetch_menu(level: int) -> list[Category]`
  - `async fetch_products(category_url: str, page: int) -> list[Product]`
  - `async fetch_comments(product_id: str, page: int) -> list[Comment]`
  - `async search(keyword: str, page: int) -> list[Product]`
- Mỗi sàn có thư mục con `crawlers/<platform>/` chứa `<platform>_crawler.py` và `_parsers.py` (parse HTML/JSON).
- Pipeline chỉ làm việc với `base.BaseCrawler` — **không phụ thuộc sàn cụ thể**.

---

## 3. Cấu trúc thư mục dự kiến

```
data-crawler/
├── main.py                       # CLI entry
├── requirements.txt
├── README.md
├── plan.md                       # file này
├── progress.md                   # log tiến độ
├── .env.example
├── .gitignore                    # đã có
│
├── config/
│   ├── constants.py              # domain, user-agent, rate-limit
│   └── settings.py               # load từ .env
│
├── core/
│   ├── http_client.py            # requests + tenacity retry
│   ├── browser.py                # playwright wrapper
│   ├── retry_handler.py
│   ├── logger.py
│   └── storage.py                # CSV/SQLite/JSONL writer
│
├── models/
│   ├── base_models.py            # Category, Product, Comment (Pydantic)
│   └── platform.py               # enum Platform
│
├── crawlers/
│   ├── base.py                   # BaseCrawler abstract
│   ├── tiki/
│   │   ├── tiki_crawler.py
│   │   ├── menu_parser.py
│   │   ├── product_parser.py
│   │   └── comment_parser.py
│   ├── shopee/
│   │   ├── shopee_crawler.py
│   │   └── parsers.py
│   ├── lazada/
│   │   ├── lazada_crawler.py
│   │   └── parsers.py
│   └── sendo/
│       ├── sendo_crawler.py
│       └── parsers.py
│
├── services/
│   ├── platform_registry.py      # ánh xạ Platform → BaseCrawler
│   ├── ranking_service.py
│   ├── comment_validator.py
│   └── category_service.py
│
├── pipelines/
│   ├── menu_pipeline.py
│   ├── products_from_menu_pipeline.py
│   ├── comments_from_products_pipeline.py
│   ├── menu_products_pipeline.py
│   ├── keyword_pipeline.py
│   └── full_pipeline.py
│
├── tests/
│   ├── test_models.py
│   ├── test_storage.py
│   ├── test_ranking.py
│   └── smoke/<platform>_smoke.py
│
├── logs/                         # để trống, được tạo khi chạy
└── outputs/                      # để trống, được tạo khi chạy
```

---

## 4. Mô hình dữ liệu (Pydantic)

```python
class Platform(str, Enum):
    TIKI = "tiki"
    SHOPEE = "shopee"
    LAZADA = "lazada"
    SENDO = "sendo"

class Category(BaseModel):
    platform: Platform
    category_id: str
    name: str
    parent_id: str | None
    level: int            # 1, 2, 3
    url: str

class Product(BaseModel):
    platform: Platform
    product_id: str
    name: str
    price: float | None
    original_price: float | None
    rating: float | None
    review_count: int | None
    sold_count: int | None
    category_path: str    # "Điện tử > Điện thoại > iPhone"
    url: str
    crawled_at: datetime

class Comment(BaseModel):
    platform: Platform
    product_id: str
    comment_id: str
    author: str
    rating: int | None
    content: str
    created_at: str
    crawled_at: datetime
```

Validation nằm trong `core/comment_validator.py` (lọc quảng cáo, lọc emoji-only, độ dài tối thiểu…).

---

## 5. Storage schema

### CSV (per-run)
- `outputs/<platform>_<category>_<run_id>_menu.csv`
- `outputs/<platform>_<category>_<run_id>_products.csv`
- `outputs/<platform>_<category>_<run_id>_comments.csv`
- `outputs/<platform>_<keyword>_<run_id>_keyword_top.csv`
- `outputs/<platform>_<keyword>_<run_id>_keyword_comments.csv`

### SQLite (`outputs/crawler.db`)
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT, product_id TEXT, name TEXT,
    price REAL, original_price REAL,
    rating REAL, review_count INTEGER, sold_count INTEGER,
    category_path TEXT, url TEXT, crawled_at TEXT,
    UNIQUE(platform, product_id)
);

CREATE TABLE categories (
    platform TEXT, category_id TEXT, parent_id TEXT,
    name TEXT, level INTEGER, url TEXT,
    PRIMARY KEY (platform, category_id)
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT, product_id TEXT, comment_id TEXT,
    author TEXT, rating INTEGER, content TEXT,
    created_at TEXT, crawled_at TEXT,
    UNIQUE(platform, comment_id)
);

CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    mode TEXT, platform TEXT, category TEXT,
    started_at TEXT, finished_at TEXT,
    product_count INTEGER, comment_count INTEGER
);
```

### JSON Lines (raw)
- `outputs/raw/<platform>_<run_id>_menu.jsonl`
- `outputs/raw/<platform>_<run_id>_products.jsonl`
- `outputs/raw/<platform>_<run_id>_comments.jsonl`

---

## 6. CLI design

```
python main.py \
  --platforms tiki,shopee \
  --mode full \
  --category "dien-thoai" \
  --output-dir outputs/2026-07-27_dien-thoai \
  --headless
```

| Flag | Mô tả |
|---|---|
| `--platforms` | danh sách sàn, phẩy. Mặc định: `tiki,shopee,lazada,sendo` |
| `--mode` | `menu` \| `products` \| `comments` \| `keyword` \| `full` |
| `--category` | slug ngành (file `config/categories.yaml`) |
| `--keywords` | danh sách từ khóa cho `keyword` mode |
| `--input-file` | CSV sản phẩm/danh mục có sẵn (cho `products_from_menu`, `comments_from_products`) |
| `--output-dir` | thư mục output, mặc định `outputs/<timestamp>` |
| `--headless` | chạy Playwright ẩn |
| `--limit` | giới hạn số sản phẩm/sàn (debug) |
| `--dry-run` | chỉ parse 1 trang mỗi sàn để smoke test |

---

## 7. Các bước thực thi (roadmap)

### Phase 0 — Foundation (estimated 1–2 ngày)
1. Khởi tạo lại cấu trúc thư mục theo mục 3.
2. Viết lại `core/` (`http_client`, `browser`, `retry_handler`, `logger`, `storage`) — giữ logic cũ, refactor cho generic.
3. Viết `models/base_models.py` + `services/platform_registry.py`.
4. Khai báo `requirements.txt` đầy đủ + `.env.example`.
5. `pytest` cho `core/` và `models/`.

### Phase 1 — Tiki (giữ nguyên) (1 ngày)
- Di chuyển crawler/parsers của project cũ vào `crawlers/tiki/`.
- Đảm bảo chạy pipeline `full` cho Tiki vẫn ra đúng schema như cũ.
- Test smoke: 1 danh mục nhỏ.

### Phase 2 — Shopee (2–3 ngày)
- Reverse-engineer endpoint công khai (vd. `shopee.vn/api/v4/search/search_products`).
- Implement `crawlers/shopee/`:
  - `search(keyword)` → top N sản phẩm.
  - `fetch_products(category_id, page)` → list sản phẩm.
  - `fetch_comments(item_id, page)` → review.
- Viết parser chịu schema drift (Shopee hay đổi key).
- Thêm rate-limit & retry riêng cho Shopee.

### Phase 3 — Lazada (2–3 ngày)
- Endpoint: `lazada.vn/catalog/` + API nội bộ.
- Menu 3 cấp lấy từ trang `lazada.vn/...`.
- Crawl sản phẩm + rating `count`.
- Bình luận nếu Lazada có public API; nếu không → ghi nhận hạn chế vào `progress.md`.

### Phase 4 — Sendo (1–2 ngày)
- Sendo có public API `api.sendo.vn/web/...` cho search.
- Menu cây dễ hơn Shopee/Lazada.
- Comments nếu không có → bỏ qua mode `comments` cho Sendo, ghi vào CLI.

### Phase 5 — Pipelines tổng hợp (1–2 ngày)
- `multi_full_pipeline()` chạy nhiều sàn song song (`asyncio.gather` + semaphore).
- `ranking_service` mở rộng: ranking chéo sàn cho cùng keyword (vd. "iphone 15" → sản phẩm nào hot nhất trên Tiki vs Shopee).
- Output CSV theo sàn + SQLite chung.
- Test integration với 1 keyword & 1 category.

### Phase 6 — Polish (1 ngày)
- README mới với ví dụ từng sàn + tổng hợp.
- `.env.example` đầy đủ: user-agent, proxy (optional), rate-limit.
- Test suite: unit + smoke.
- Tag version `v0.1.0`.

---

## 8. Rủi ro & giảm thiểu

| Rủi ro | Tác động | Giảm thiểu |
|---|---|---|
| Sàn đổi HTML/JSON structure | Parser vỡ, mất dữ liệu | Tách `_parsers.py` riêng, có fixture test, dễ patch. |
| Bị block IP khi crawl nhiều | Pipeline dừng | Rate-limit per-domain, retry exponential, optional proxy. |
| Pháp lý / ToS | Vi phạm | Tôn trọng robots.txt, không login, dùng dữ liệu công khai, document điều kiện. |
| Comment API không public | Một số sàn không crawl được comment | Đánh dấu `comment_supported=False` trong registry, CLI cảnh báo. |
| Code từ project cũ có lệch chuẩn | Tăng effort refactor | Phase 0 viết test cho core trước khi đưa vào. |

---

## 9. Tiêu chí hoàn thành

- [x] `python main.py --platform tiki --mode full --category "dien-thoai"` chạy thành công, ra CSV + SQLite + JSONL.
- [x] `python main.py --platforms tiki,shopee --mode keyword --keywords "iphone"` chạy thành công (Tiki thật OK; Shopee fallback Playwright khi API gated).
- [x] Thêm được sàn mới chỉ bằng cách tạo thư mục `crawlers/<name>/` + đăng ký trong `platform_registry.py` (không sửa core).
- [x] `pytest` pass toàn bộ unit + smoke test (145 passed, 2 skipped network-gated).
- [x] README.md có hướng dẫn chạy cho từng sàn.

---

## 10. Tham chiếu

- Project gốc: xem lịch sử git trước khi wipe (commit `94845da`).
- Techstack: `requirements.txt` của project cũ (sẽ tái sử dụng nguyên xi).
- Báo cáo tiến độ: xem `progress.md`.
