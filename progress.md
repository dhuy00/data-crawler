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

## Nhật ký tiếp theo
> Mỗi lần hoàn thành phase, ghi thêm 1 block ngày mới vào dưới đây theo mẫu:
>
> ```
> ## YYYY-MM-DD — <tóm tắt phase>
>
> ### Làm được
> - ...
>
> ### Còn vướng
> - ...
>
> ### Bước tiếp theo
> - ...
> ```