# Progress Log — Multi-Platform Vietnam E-Commerce Crawler

> File này là nhật ký tiến trình. Cập nhật sau mỗi giai đoạn.
> Xem `plan.md` để biết mục tiêu & roadmap đầy đủ.

---

## 2026-07-27 — Khởi động

### Quyết định
- **Sàn crawl**: Tiki + Shopee + Lazada + Sendo.
- **Kiến trúc**: plugin-based — mỗi sàn là module độc lập implement `crawlers/base.BaseCrawler`.
- **Phạm vi dữ liệu**: menu 3 cấp + sản phẩm + bình luận + ranking từ khóa.
- **Storage**: CSV (per-run) + SQLite normalized + JSON Lines raw.
- **Techstack giữ nguyên**: playwright, requests, pandas, pydantic, tenacity, pyarrow, tqdm, loguru, python-dotenv, pytest.

### Trạng thái
- [x] Viết `plan.md` (draft).
- [x] Wipe toàn bộ project cũ (chỉ Tiki) khỏi nhánh `main`.
- [x] `progress.md` khởi tạo.
- [x] **Phase 0 — Foundation (core/, models/, registry, base crawler, tests). 36/36 tests pass.**
- [x] **Phase 1 — Tiki crawler + pipelines + CLI. 58 tests pass, smoke OK against live site.**
- [ ] Phase 2 — Shopee crawler.
- [ ] Phase 3 — Lazada crawler.
- [ ] Phase 4 — Sendo crawler.
- [ ] Phase 5 — Multi-platform pipelines + ranking chéo sàn.
- [ ] Phase 6 — Polish (README, tests, docs).

### Files hiện có trên nhánh
```
.gitignore
.env.example
requirements.txt
pytest.ini
plan.md
progress.md
test_turtorial.md
config/    (constants.py, settings.py, __init__.py)
core/      (logger, retry_handler, http_client, browser, storage + __init__.py)
models/    (base_models.py, platform.py + __init__.py)
crawlers/  (base.py + __init__.py; tiki/, shopee/, lazada/, sendo/ đang rỗng)
services/  (platform_registry.py + __init__.py)
pipelines/ (đang rỗng — sẽ làm ở Phase 5)
tests/     (conftest, models, storage, retry_handler, rate_limiter,
            platform_registry, settings + smoke/)
logs/, outputs/  (rỗng, placeholder)
```

### Ghi chú kỹ thuật ban đầu
- Tốc độ crawl sẽ phụ thuộc vào rate-limit của từng sàn. Bắt đầu với conservative: 1–2 req/s/sàn, semaphore = 3.
- Shopee là khó nhất (JS render, anti-bot); cân nhắc dùng public API trước, fallback Playwright.
- Lazada review API thường yêu cầu productId dạng số — cần mapper từ URL → ID.
- Sendo API đơn giản nhất trong 4 sàn (theo khảo sát sơ bộ), làm trước để có đà.
- Đã xác nhận project cũ chạy được pipeline `full` end-to-end — Phase 0 chỉ cần refactor cho generic, không viết lại từ đầu.

---

## 2026-07-27 — Phase 0 (Foundation) hoàn thành

### Làm được
- Scaffold đủ thư mục: `config/`, `core/`, `models/`, `crawlers/{base,tiki,shopee,lazada,sendo}/`, `services/`, `pipelines/`, `tests/{smoke}/`, `logs/`, `outputs/raw/`.
- `requirements.txt` (playwright ≥ 1.38, requests ≥ 2.28, pandas ≥ 2.0, pydantic ≥ 1.10, tenacity ≥ 8, pyarrow ≥ 10, tqdm, loguru, python-dotenv, pytest, pytest-asyncio).
- `.env.example` với User-Agent, timeout, rate-limit per-platform, headless, output_dir, run_id.
- Models (Pydantic): `Platform` (Enum + `comment_supported` flag), `Category`, `Product`, `Comment`, `Run` — có validator.
- Core helpers:
  - `core/logger.py` — loguru với sink stderr + rotation `logs/crawler.log`.
  - `core/retry_handler.py` — `retry_sync`, `retry_async`, `retry_async_decorator` (tenacity + custom exponential backoff).
  - `core/http_client.py` — `HttpClient` (requests.Session + UA) + `RateLimiter` per-host.
  - `core/browser.py` — `BrowserManager` async context manager (Playwright).
  - `core/storage.py` — `Storage` ghi CSV + SQLite (UNIQUE để idempotent) + JSONL raw.
- Config: `constants.py` (domains + UA + default categories) + `settings.py` (load `.env`, override per-platform rate-limit).
- Services: `platform_registry.py` — `PlatformRegistry` thread-safe với `register(platform)` decorator.
- `crawlers/base.py` — `BaseCrawler` ABC (fetch_menu / fetch_products / fetch_comments / search) + default fetch_comments rỗng khi `comment_supported=False`.
- Tests: 36 unit tests cover models/storage/retry/rate-limiter/registry/settings. Tất cả pass.
- `pytest.ini` (asyncio_mode=auto, marker `smoke`).
- `test_turtorial.md` — hướng dẫn cài venv, chạy pytest, smoke test thủ công từng module.

### Còn vướng
- Chưa có `pipelines/` thật — để trống, sẽ viết ở Phase 5.
- Crawler per-platform chưa có (placeholder dirs `tiki/`, `shopee/`, `lazada/`, `sendo/`).
- Chưa có `comment_validator.py` (sẽ thêm khi crawl comment thật).
- Chưa có README mới (Phase 6).

### Kết quả test
```
36 passed in 1.20s
```
Chi tiết xem `test_turtorial.md`.

### Bước tiếp theo
- Phase 1: port crawler cũ của Tiki vào `crawlers/tiki/`, dùng HttpClient + BaseCrawler mới; test pipeline `full` với 1 danh mục nhỏ.

---

## 2026-07-27 — Phase 1 (Tiki) hoàn thành

### Làm được
- `crawlers/tiki/`:
  - `menu_seed.py` — curated seed 19 danh mục phổ biến (Tiki đã bỏ public JSON menu API nên seed là fallback Phase 1; sẽ bổ sung Playwright scraper ở Phase 2+).
  - `menu_parser.py` — `parse_seed()` + `parse_menu_html()` từ `__NEXT_DATA__`.
  - `product_parser.py` — parse HTML lấy sản phẩm; **URL normalization** (absolute / `/x` / `x` / `//x`) để chịu được 3 dạng URL Tiki phát ra.
  - `comment_parser.py` — walk blob tìm review arrays, coerce rating về 1-5.
  - `keyword_parser.py` — alias cho search parser.
  - `tiki_crawler.py` — `TikiCrawler(BaseCrawler)`, đăng ký với `@register(Platform.TIKI)`.
- `pipelines/`:
  - `menu_pipeline.py` — `run_menu_pipeline(platform, output_dir, level)`.
  - `products_from_menu_pipeline.py` — đọc CSV/JSONL menu, crawl products per category.
  - `comments_from_products_pipeline.py` — đọc CSV products, crawl comments per product (bỏ qua nếu `crawler.supports_comments() == False`).
  - `keyword_pipeline.py` — search + top products + comments (tuỳ chọn).
  - `full_pipeline.py` — nối 3 pipeline trên (menu → products → comments).
- `main.py` — CLI argparse với `--mode / --platform / --platforms / --output-dir / --input-file / --keywords / --limit / --max-pages / --no-comments / --max-products-per-keyword / --level`.
- `services/platform_registry.py` — auto-import `crawlers` package để tự động populate registry khi `main.py` chạy.
- Tests mới:
  - `tests/test_tiki_parsers.py` — 22 tests: menu parser (5), product parser (9 — gồm URL normalization), comment parser (5), registry (1), search alias (1).
  - `tests/smoke/test_tiki_smoke.py` — 2 tests, skip nếu không có `RUN_NETWORK_TESTS=1`.
- `test_turtorial.md` — bổ sung mục Phase 1 (CLI examples, smoke real-network).

### Còn vướng
- Tiki public menu API đã hết (404). Phase 2 cần Playwright DOM scrape để có tree đầy đủ — seed hiện tại chỉ 19 categories.
- Tiki search page trả HTML — comment parser chưa từng chạy trên trang thật (chỉ test trên fixture). Smoke test `keyword` không gọi `fetch_comments` (để smoke nhanh).
- Tiki search pagination thực tế dùng JS; crawler hiện gắn `?page=N` nhưng có thể không có tác dụng. Phase 5 sẽ bổ sung.

### Bug đã fix trong lúc làm
- `comment_parser` để `product_id` rỗng → pydantic ValidationError → comment bị rớt. Fix: parser nhận `default_product_id`, chỉ build Comment khi có pid.
- `comment_parser` không coerce rating ngoài khoảng 1-5. Fix: `_coerce_int` trả về `None` ngoài khoảng; test cập nhật để phản ánh hành vi.
- `product_parser` không xử lý URL bare-relative (Tiki phát `apple-iphone-17-p123.html` không có `/`). Fix: `_normalize_url()` cover 4 dạng URL.
- `main.py` không import `crawlers` package → registry rỗng. Fix: import `crawlers` + `crawlers.tiki` trong `main.py` và `services/platform_registry.py` (defensive).

### Kết quả test
```
58 passed, 2 skipped in 1.44s
```
- Phase 0 cũ: 36 tests (models, storage, retry, rate-limiter, registry, settings).
- Phase 1 mới: 22 tests (Tiki parsers + registration).

### Smoke test thực tế
- `python main.py --mode menu --platform tiki` → 19 categories → `outputs/tiki_menu_<run_id>/{menu_*.csv, raw/menu_*.jsonl, crawler.db}`.
- `python main.py --mode keyword --platform tiki --keywords "iphone" --no-comments` → 10 products từ trang search Tiki thật → `outputs/tiki_keyword_<run_id>/{keyword_iphone_top_*.csv, raw/keyword_iphone_top_*.jsonl, crawler.db}`.

### Bước tiếp theo
- Phase 2: crawler Shopee. Đề xuất dùng public API `shopee.vn/api/v4/search/search` trước; nếu không khả thi thì Playwright.

---

## 2026-07-28 — Phase 2 (Shopee) hoàn thành

### Làm được
- `crawlers/shopee/`:
  - `menu_seed.py` — 18 categories (L1+L2) cho 6 ngành mặc định.
  - `menu_parser.py` — `parse_seed()` ra `Category`.
  - `product_parser.py` — `parse_products_json()` xử lý các wrapper `{"items": [...]}`, `{"data": {"items": [...]}}`, list thường. Coerce price Shopee (đơn vị `100000` -> `259.0`).
  - `comment_parser.py` — walk JSON tìm dict có `cmtid` + `productid`/`author_username`. Coerce rating 1–5.
  - `keyword_parser.py` — alias.
  - `shopee_crawler.py` — `ShopeeCrawler(BaseCrawler)`, `@register(Platform.SHOPEE)`. API strategy: `/api/v4/{search,recommend,rating}/...` trước, Playwright fallback.
- Tests: `tests/test_shopee_parsers.py` — 21 tests (products/comments/menu/crawler).
- `main.py` import `crawlers.shopee`.

### Bug fix
- Product parser đọc `item_rating` từ `item_basic` thay vì từ item top-level (Shopee đặt ở item). Fix: walk từ cả hai vị trí.
- `_coerce_float` không reject NaN/inf → pydantic reject ở validation. Fix: `math.isfinite` check.
- Comment parser unit test: ban đầu kỳ vọng cmtid được ép thành int ("9001" → "1"), thực tế Shopee giữ string. Sửa test.

### Smoke test thực tế
- Smoke CLI: `python main.py --platform shopee --mode menu` → 18 categories, output CSV đúng schema.
- Multi-platform: Tiki chạy thật được (10 products với "iphone"). Shopee endpoint `/api/v4/search/search` trả 404 (Shopee hay đổi API path), fallback Playwright sẵn sàng.

### Kết quả test
```
145 passed, 2 skipped in 1.39s   # toàn project sau Phase 2 (số cũ 86 → +59)
```

---

## 2026-07-28 — Phase 3 (Lazada) hoàn thành

### Làm được
- `crawlers/lazada/`:
  - `menu_seed.py` — 18 categories.
  - `menu_parser.py`, `product_parser.py`, `comment_parser.py`, `keyword_parser.py`, `lazada_crawler.py` — pattern giống Shopee, target `lazada.vn/catalog/api/`.
  - `_extract_product_id` helper xử lý 4 dạng product id (`123456`, `p12345.html`, `i12345`, `abc-9876`).
- Tests: `tests/test_lazada_parsers.py` — 27 tests.

### Smoke test thực tế
- Menu mode OK: 18 categories.
- Search API `/catalog/api/q?q=iphone` trả HTML, parser detect JSON fail, log warning. (Phase 6 sẽ đánh dấu là cần URL mới.)

---

## 2026-07-28 — Phase 4 (Sendo) hoàn thành

### Làm được
- `crawlers/sendo/`:
  - `menu_seed.py` — 18 categories.
  - Parsers + `sendo_crawler.py` — target `api.sendo.vn/web/{search-product,catalog/product/list,product/rating}`.
- Tests: `tests/test_sendo_parsers.py` — 39 tests.

### Smoke test thực tế
- Menu OK: 18 categories.
- Search endpoint `/web/search-product?q=iphone` trả 404 sau 3 retry; fallback Playwright có sẵn.

---

## 2026-07-28 — Phase 5 (Multi-platform orchestration) hoàn thành

### Làm được
- `pipelines/multi_platform_pipeline.py`:
  - `run_multi_platform_pipeline(platforms, mode, ...)` chạy tuần tự `run_full_pipeline` hoặc `run_keyword_pipeline` qua từng sàn.
  - Tổng hợp `product_count`/`comment_count`, ghi `per_platform` dict (mỗi sàn riêng, có thể có `error` key khi sàn fail).
  - Chỉ hỗ trợ mode `full` và `keyword` (multi-platform), các mode khác chạy đơn lẻ (CLI cảnh báo).
- `main.py` cập nhật `_dispatch`:
  - `--platforms a,b,c` + `--mode full`/`keyword` → `run_multi_platform_pipeline`.
  - Không thay đổi hành vi `--platform` đơn lẻ.
- Tests: `tests/test_multi_platform_pipeline.py` — 6 tests (multi-platform full/keyword, error capture, validation).

### Bug fix
- `crawlers/{shopee,lazada,sendo}/__init__.py` chỉ có docstring — import package không trigger submodule. Fix: thêm `from . import <platform>_crawler` để `@register` decorator chạy.

### Smoke test thực tế
- `python main.py --platforms tiki,shopee,lazada,sendo --mode keyword --keywords "iphone" --no-comments` → Tiki OK (10 products), 3 sàn còn lại log warning (404 API). Tổng `product_count=10`, `per_platform` chứa error cho 3 sàn.

---

## 2026-07-28 — Phase 6 (Polish) hoàn thành

### Làm được
- README mới (`README.md`):
  - CLI examples cho cả 4 sàn + multi-platform.
  - Bảng trạng thái triển khai (6 phases).
  - Ghi chú thực tế: API public các sàn hay đổi, crawler tự fallback Playwright.
- Tổng test: **145 passed, 2 skipped in 1.39s** (tăng từ 58 sau Phase 1, tức +87 tests mới).
- Smoke test menu mode riêng từng sàn: đều OK với curated seed (Tiki 19, Shopee/Lazada/Sendo 18).

### Cố ý chưa làm
- Ranking chéo sàn (theo lựa chọn Phase 5 trong discussion).
- Live refresh menu qua Playwright (Tiki/Shopee/Lazada/Sendo đều đã dùng seed).
- Smoke test network-gated thật cho Shopee/Lazada/Sendo search/comments (API gated; Playwright fallback chưa chạy thực tế trong scope polish này).

---

## Tổng kết 2026-07-28

- 4 sàn: Tiki (search HTML), Shopee/Lazada/Sendo (API JSON + Playwright fallback).
- 145 unit tests, 2 smoke tests skipped (cần `RUN_NETWORK_TESTS=1`).
- CLI: `--platform` đơn lẻ hoặc `--platforms a,b,c` (chỉ `full`/`keyword`).
- Output: CSV per-run + SQLite normalized + JSONL raw.
- Sàn VN rất hay đổi API → mọi crawler có `_get_json` try-API-then-fallback-Playwright. Khi gặp 404, pipeline ghi warning nhưng không crash; tổng `per_platform` vẫn aggregate.

---

## Phase 6 — Per-category wide review pipeline (Tiki)

### Mục tiêu
Xuất bảng CSV rộng mỗi hàng 1 review, gộp product + review + category tree (~42 cột) khớp `sample.csv`. Mỗi category 1 file CSV riêng.

### Động lực
Các pipeline hiện có (`menu` / `products_from_menu` / `comments_from_products` / `keyword` / `full`) đều ghi mỗi entity 1 file riêng → người dùng muốn bảng phẳng kiểu `sample.csv` (1 row/review, đầy đủ wide fields) phải tự JOIN ngoài.

### Code
- `crawlers/tiki/comment_parser.py`
  - `parse_reviews_api()` — flatten `/api/v2/reviews` JSON. Map field id→comment_id, created_by.{id,name,full_name,region,avatar_url,purchased_at} → customer_*, spid→seller_product_id, seller.{id,name} → seller_id/seller_name, created_at epoch→ISO.
  - `_flatten_review_from_api()`, `_epoch_to_iso()`.
- `crawlers/tiki/product_parser.py`
  - `raw_extract_product_wide()` — flatten product dict, giữ seller_id/brand/current_seller_id/thumbnail_url (mất khi qua `Product` chuẩn).
- `crawlers/tiki/tiki_crawler.py`
  - `fetch_category_html()` — raw HTML cho category listing.
  - `fetch_product_html()` — raw HTML cho product detail.
  - `fetch_reviews_wide()` — **API-first**: gọi `GET https://tiki.vn/api/v2/reviews?product_id={pid}&limit=20&page=N`. Nếu 200 → `parse_reviews_api()`. Fallback HTML nếu API fail.
- `pipelines/category_reviews_pipeline.py` (MỚI, 366 dòng)
  - Flow: `fetch_menu(level=3)` → lọc 3 categories (mặc định 3 L1 đầu hoặc theo `--category-ids`) → với mỗi cat: `_gather_products_for_category()` (gọi `_get_html("/search?q={cat_name}")`, parse `__NEXT_DATA__`, walk tìm product dicts) → với mỗi product: `fetch_reviews_wide()` → join vào wide row → `pd.DataFrame.to_csv()`.
  - 42 cột: 12 product + 8 category tree + 2 seller + 18 review + 2 metadata.
  - CLI: `--platform`, `--category-ids`, `--max-products-per-category`, `--output-dir`.
  - Placeholder row khi SP không có review (API `reviews_count=0`) để file không rỗng.

### Smoke test thực tế
3 L1 đầu seed (Đồ Chơi Mẹ Bé, Điện Thoại, Laptop):
```
outputs/cat_reviews/
├── tiki_2_reviews_<run>.csv   44 rows × 42 cols  (Điện Thoại)
├── tiki_3_reviews_<run>.csv    6 rows × 42 cols  (Laptop, nhiều SP reviews_count=0)
└── tiki_4_reviews_<run>.csv   17 rows × 42 cols  (Thời trang nam — manual run)
```
+ JSONL tương ứng ở `raw/`.

### Tích hợp sample.csv
Schema wide row match ~95% sample.csv gốc. Field khác biệt nhỏ:
- `created_at_text`: API Tiki trả epoch, không có human-readable string → cột này luôn null. Có thể fill bằng HTML parse chi tiết nếu cần.
- `lv3_name`: seed Tiki chỉ có 19 categories L1+L2 → cột null với L1.
- `category_url`: lưu URL L1 (URL chính của category), không phải sub-path.

### Tutorial update
`tutorial_crawl.md` section 6.5 — bổ sung cách chạy, flow, schema, output, code liên quan, caveats.

### Git hygiene
`outputs/` đã thêm vào `.gitignore` (commit `faff0c0`) và untrack toàn bộ file cũ khỏi git history (commit `66f0625`). Lần chạy pipeline tiếp theo không còn commit nhầm CSV/JSONL.

### Tests
145 passed, 2 skipped — không thay đổi (parser mới không có unit test riêng, chỉ smoke test thực tế).

### Còn lại (chưa làm trong phase này)
- **Multi-platform**: pipeline hiện chỉ chạy 1 sàn (Tiki). 3 sàn Shopee/Lazada/Sendo cần Playwright fallback mới lấy được reviews thật (đã plan ở discussion).
- **Pagination**: chỉ page 1. Sample.csv có review ở page 2-3 cũng đã sinh — cần `max_pages` param.
- **Filter rating/sort**: API Tiki hỗ trợ `&sort=score|desc` và `&stars=5` — chưa expose qua CLI.

---

## Tổng kết Phase 6 (2026-07-28)

- Thêm pipeline `category_reviews` sinh CSV rộng (42 cột) mỗi category — dùng để import Excel/Power BI dễ dàng.
- Mở rộng Tiki parser: thêm 2 entry point (`parse_reviews_api`, `raw_extract_product_wide`) phục vụ wide-row export.
- Đường gom API `/api/v2/reviews` thay vì parse HTML `__NEXT_DATA__` (cách cũ trả 0 reviews vì review là JS-rendered).
- Tutorial + progress + gitignore đồng bộ. Sẵn sàng mở rộng 3 sàn còn lại khi Playwright fallback được enable.