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
- [ ] Phase 1 — Tiki crawler (di chuyển từ project cũ).
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