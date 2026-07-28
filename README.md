# Multi-Platform Vietnam E-Commerce Crawler

Crawler dữ liệu sản phẩm + bình luận từ **4 sàn TMĐT Việt Nam**: Tiki, Shopee, Lazada, Sendo. Kiến trúc **plugin-based**: thêm sàn mới chỉ cần tạo `crawlers/<platform>/` + đăng ký với `@register`, không sửa core pipeline.

Xem `plan.md` cho thiết kế tổng thể và `progress.md` cho nhật ký triển khai.

---

## 1. Cài đặt nhanh

```powershell
cd data-crawler
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium   # chỉ cần khi crawler Playwright fallback chạy
```

---

## 2. CLI — chạy pipeline

Mọi câu lệnh đều dạng:

```powershell
.venv\Scripts\python.exe main.py --mode <mode> [--platform X | --platforms a,b,c] [flags]
```

### Modes

| Mode | Mô tả |
|---|---|
| `menu` | Trả menu danh mục dạng seed (Tiki 19, Shopee/Lazada/Sendo 18 mỗi sàn). |
| `products_from_menu` | Đọc CSV menu, crawl products từng danh mục. |
| `comments_from_products` | Đọc CSV products, crawl comments từng SP. |
| `keyword` | Search theo từ khóa + lấy top N products (mặc định 10) + tuỳ chọn comments. |
| `full` | `menu` → `products` → `comments` cho 1 sàn. |

### Flags chính

| Flag | Ý nghĩa |
|---|---|
| `--platform` | Tên 1 sàn (`tiki` / `shopee` / `lazada` / `sendo`). Mặc định `tiki`. |
| `--platforms` | Danh sách sàn phẩy (chỉ dùng với `full` và `keyword`). |
| `--keywords` | Từ khoá (cho `keyword`, phẩy-phân-cách). |
| `--output-dir` | Thư mục output, mặc định `outputs/`. |
| `--limit` | Giới hạn categories/products. |
| `--max-pages` | Số trang tối đa mỗi category. |
| `--max-products-per-keyword` | Top N cho từng keyword. |
| `--no-comments` | Bỏ qua crawl comments. |
| `--input-file` | CSV/JSONL input (cho `products_from_menu` / `comments_from_products`). |
| `--level` | Độ sâu menu (1–3, mặc định 3). |

### Ví dụ

```powershell
# Menu 1 sàn
.venv\Scripts\python.exe main.py --platform shopee --mode menu --output-dir outputs/menu

# Search theo từ khoá, lấy 10 SP + comments
.venv\Scripts\python.exe main.py --platform tiki --mode keyword --keywords "iphone,airpods"

# Multi-platform keyword: chạy tuần tự qua 4 sàn
.venv\Scripts\python.exe main.py --platforms tiki,shopee,lazada,sendo --mode keyword --keywords "iphone" --no-comments

# Full pipeline cho Tiki (menu → products → comments)
.venv\Scripts\python.exe main.py --platform tiki --mode full
```

---

## 3. Output

Mỗi pipeline run tạo thư mục con dạng `<platform>_<mode>_<YYYYMMDD_HHMMSS>/`:

```
outputs/
├── tiki_keyword_20260728_120020/
│   ├── keyword_iphone_top_20260728_120020.csv      # top products
│   ├── raw/keyword_iphone_top_20260728_120020.jsonl # raw JSON Lines
│   └── crawler.db                                   # SQLite normalized
└── shopee_keyword_20260728_120020/
    └── ...
```

3 dạng output: **CSV per-run** (mỗi file 1 bảng), **SQLite normalized** (`outputs/crawler.db`, schema ở `plan.md` §5), **JSON Lines raw** (mỗi dòng 1 object). UNIQUE constraint ở SQLite đảm bảo idempotent — chạy lại không trùng dòng.

---

## 4. Kiến trúc (tóm tắt)

```
main.py  →  pipelines/  →  crawlers/<platform>/  →  core/, models/
                                  ↑
                          BaseCrawler (interface)
                          @register(Platform)
```

- **`crawlers/base.py`** — ABC với `fetch_menu / fetch_products / fetch_comments / search`. Mỗi sàn chỉ cần implement interface.
- **`crawlers/<platform>/`** — Plugin layer (Tiki/Shopee/Lazada/Sendo). Mỗi thư mục: `<platform>_crawler.py` + parsers (`menu_parser`, `product_parser`, `comment_parser`, `keyword_parser`).
- **`pipelines/`** — Orchestrator. `multi_platform_pipeline.py` chạy tuần tự qua nhiều sàn (Phase 5).
- **`core/`** — Helpers chung: `HttpClient` (+ per-host `RateLimiter`), `BrowserManager` (Playwright), `Storage` (CSV+SQLite+JSONL), `logger`, `retry_handler`.
- **`models/`** — Pydantic: `Product`, `Comment`, `Category`, `Run`, `Platform` enum.

Để thêm sàn mới: tạo `crawlers/<name>/<name>_crawler.py` + parsers, thêm vào `models/platform.py` enum, không sửa core.

---

## 5. Tests

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

- **Unit**: 145 tests cover models, storage, retry, rate-limiter, registry, settings, parsers cho 4 sàn, multi-platform pipeline.
- **Smoke**: 2 tests ở `tests/smoke/` (skip nếu thiếu `RUN_NETWORK_TESTS=1`).

---

## 6. Trạng thái triển khai

| Phase | Trạng thái | Tests |
|---|---|---|
| Phase 0 — Foundation | ✅ | 36 |
| Phase 1 — Tiki crawler | ✅ | +22 |
| Phase 2 — Shopee crawler | ✅ | +21 |
| Phase 3 — Lazada crawler | ✅ | +27 |
| Phase 4 — Sendo crawler | ✅ | +39 |
| Phase 5 — Multi-platform | ✅ | +6 |
| Phase 6 — Polish | ✅ | (docs) |

**Tổng: 145 tests pass, 2 skipped (network-gated).**

### Ghi chú thực tế (2026-07-28)

- Tiki seed menu = 19 categories; các sàn khác seed = 18 categories (L1+L2).
- Public API của Shopee/Lazada/Sendo hay đổi — nếu gặp 404 crawler tự fallback Playwright (xem `crawlers/<sàn>/<sàn>_crawler.py`).
- Ranking chéo sàn (`plan.md` §7 Phase 5) **đã cố ý bỏ** theo lựa chọn triển khai.
- Comments cho Shopee/Lazada/Sendo dùng Playwright fallback nếu API gated.

Xem `progress.md` cho nhật ký chi tiết từng phase.
