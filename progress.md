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
- [ ] Phase 0 — Foundation (core/, models/, registry).
- [ ] Phase 1 — Tiki crawler (di chuyển từ project cũ).
- [ ] Phase 2 — Shopee crawler.
- [ ] Phase 3 — Lazada crawler.
- [ ] Phase 4 — Sendo crawler.
- [ ] Phase 5 — Multi-platform pipelines + ranking chéo sàn.
- [ ] Phase 6 — Polish (README, tests, docs).

### Files hiện có trên nhánh
```
.gitignore    (đã có từ trước)
plan.md       (mới)
progress.md   (mới — file này)
```

### Ghi chú kỹ thuật ban đầu
- Tốc độ crawl sẽ phụ thuộc vào rate-limit của từng sàn. Bắt đầu với conservative: 1–2 req/s/sàn, semaphore = 3.
- Shopee là khó nhất (JS render, anti-bot); cân nhắc dùng public API trước, fallback Playwright.
- Lazada review API thường yêu cầu productId dạng số — cần mapper từ URL → ID.
- Sendo API đơn giản nhất trong 4 sàn (theo khảo sát sơ bộ), làm trước để có đà.
- Đã xác nhận project cũ chạy được pipeline `full` end-to-end — Phase 0 chỉ cần refactor cho generic, không viết lại từ đầu.

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