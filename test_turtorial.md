# test_turtorial.md — Hướng dẫn test dự án data-crawler

> Tên file giữ nguyên `test_turtorial.md` theo yêu cầu (chính tả "turtorial" được giữ để không phá tên đã thống nhất với người dùng).

File này hướng dẫn cài đặt môi trường, chạy toàn bộ test, chạy test riêng lẻ, và smoke test thủ công cho Phase 0 (Foundation).

---

## 1. Chuẩn bị môi trường

### 1.1 Yêu cầu
- Python **≥ 3.10** (đã test trên 3.12).
- PowerShell (Windows) hoặc bash (POSIX).

### 1.2 Tạo virtualenv & cài dependencies

```powershell
cd <repo-root>          # thư mục data-crawler
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Trên bash / macOS:
```bash
cd <repo-root>
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

### 1.3 (Tuỳ chọn) Cài Playwright browsers

Phase 0 chưa cần Playwright, nhưng Phase 1+ sẽ dùng. Cài trước luôn:

```powershell
.venv\Scripts\python.exe -m playwright install chromium
```

### 1.4 File `.env`

Phase 0 không bắt buộc (mọi settings có default), nhưng để sẵn sàng cho các phase sau:

```powershell
Copy-Item .env.example .env
# Sửa .env nếu muốn đổi User-Agent, output dir, ...
```

`.env` đã được gitignore — không commit.

---

## 2. Chạy toàn bộ test

### 2.1 Lệnh nhanh

```powershell
.venv\Scripts\python.exe -m pytest
```

Kết quả mong đợi ở Phase 0:
```
============================= 36 passed in ~1s ==============================
```

### 2.2 Verbose (thấy từng test case)

```powershell
.venv\Scripts\python.exe -m pytest -v
```

### 2.3 Stop ngay khi fail (hữu ích khi refactor)

```powershell
.venv\Scripts\python.exe -m pytest -x
```

### 2.4 Chạy với coverage

Cài thêm `pytest-cov`:
```powershell
.venv\Scripts\python.exe -m pip install pytest-cov
.venv\Scripts\python.exe -m pytest --cov=. --cov-report=term-missing
```

---

## 3. Chạy test theo file / theo nhóm

| Mục đích | Lệnh |
|---|---|
| Test models (Pydantic + Platform enum) | `pytest tests/test_models.py -v` |
| Test storage (CSV + SQLite + JSONL) | `pytest tests/test_storage.py -v` |
| Test retry (sync + async) | `pytest tests/test_retry_handler.py -v` |
| Test rate limiter | `pytest tests/test_rate_limiter.py -v` |
| Test registry + BaseCrawler | `pytest tests/test_platform_registry.py -v` |
| Test settings / config | `pytest tests/test_settings.py -v` |
| Một test cụ thể | `pytest tests/test_models.py::TestPlatform::test_values_are_lowercase -v` |
| Chạy theo marker (nếu có) | `pytest -m smoke` |

---

## 4. Smoke test thủ công

Smoke test dùng để chạy nhanh từng module mà không cần framework — giúp kiểm tra import path & hành vi cơ bản.

### 4.1 Kiểm tra import toàn project

```powershell
.venv\Scripts\python.exe -c "import core, models, config, services, crawlers; print('All packages import OK')"
```

### 4.2 Tạo storage mẫu + ghi dữ liệu giả

```powershell
.venv\Scripts\python.exe -c "
from pathlib import Path
from core import Storage
from models import Product, Platform

out = Path('outputs/smoke_test'); out.mkdir(parents=True, exist_ok=True)
s = Storage(out, run_id='smoke')

prods = [Product(platform=Platform.TIKI, product_id='P1', name='Test', price=100)]
s.save_products(prods)
print('CSV:', s.csv_path('products'))
print('DB :', s.db_path)
"
```

Kiểm tra output:
```powershell
Get-ChildItem outputs/smoke_test
```

Mong đợi:
- `products_smoke.csv`
- `raw/products_smoke.jsonl`
- `crawler.db`

Đọc SQLite nhanh:
```powershell
.venv\Scripts\python.exe -c "
import sqlite3
conn = sqlite3.connect('outputs/smoke_test/crawler.db')
print(conn.execute('SELECT platform, product_id, name FROM products').fetchall())
"
```

### 4.3 Test retry bằng tay

```powershell
.venv\Scripts\python.exe -c "
import asyncio
from core.retry_handler import retry_async

calls = {'n': 0}
async def flaky():
    calls['n'] += 1
    if calls['n'] < 3:
        raise RuntimeError('boom')
    return 'ok'

print(asyncio.run(retry_async(flaky, max_attempts=5, initial_wait=0.0, max_wait=0.0)))
print('called', calls['n'], 'times')
"
```

Mong đợi: `ok` rồi `called 3 times`.

### 4.4 Test rate limiter

```powershell
.venv\Scripts\python.exe -c "
import time
from core.http_client import RateLimiter

rl = RateLimiter(requests_per_second=2)  # 0.5s mỗi request cùng host
rl.wait('https://shopee.vn/x')
t0 = time.monotonic()
rl.wait('https://shopee.vn/y')
print('waited', round(time.monotonic() - t0, 3), 's')
"
```

Mong đợi: ~0.5s (chấp nhận sai số nhỏ).

### 4.5 Test BaseCrawler

```powershell
.venv\Scripts\python.exe -c "
import asyncio
from crawlers.base import BaseCrawler
from models import Platform

class Stub(BaseCrawler):
    platform = Platform.TIKI
    async def fetch_menu(self, level=3): return []
    async def fetch_products(self, url, page=1, page_size=20): return []
    async def search(self, kw, page=1, page_size=20): return []

c = Stub()
print(c.describe())
print('supports comments:', c.supports_comments())
print('empty fetch_comments (returns empty):', asyncio.run(c.fetch_comments('P1')))
"
```

Mong đợi:
```
{'platform': 'tiki', 'comment_supported': 'True', 'class': 'Stub'}
supports comments: True
empty fetch_comments (returns empty): []
```

### 4.6 Test platform registry

```powershell
.venv\Scripts\python.exe -c "
from services.platform_registry import PlatformRegistry, register
from crawlers.base import BaseCrawler
from models import Platform

class Dummy(BaseCrawler):
    platform = Platform.SHOPEE
    async def fetch_menu(self, level=3): return []
    async def fetch_products(self, url, page=1, page_size=20): return []
    async def search(self, kw, page=1, page_size=20): return []

reg = PlatformRegistry()
register_decorator = register(Platform.SHOPEE)
register_decorator(Dummy)

print('available:', [p.value for p in reg.available()])
print('shopee supports comments:', reg.get(Platform.SHOPEE).supports_comments())
"
```

---

## 5. Smoke test với network (chỉ Phase 1+)

Hiện tại **không có** smoke test nào của Phase 0 chạm mạng — toàn bộ là unit test.

Các phase sau (1–4) sẽ thêm `tests/smoke/<platform>_smoke.py` dùng để ping thật. Khi đó, chạy bằng:

```powershell
$env:RUN_NETWORK_TESTS = "1"
.venv\Scripts\python.exe -m pytest -m smoke -v
```

Mặc định smoke bị **skip** (an toàn khi CI không có internet).

---

## 6. Troubleshooting

| Vấn đề | Nguyên nhân | Cách xử lý |
|---|---|---|
| `ModuleNotFoundError: No module named 'core'` | Chưa cd vào repo root hoặc chưa activate venv | `cd <repo-root>` + `.\.venv\Scripts\Activate.ps1` |
| `ImportError: attempted relative import beyond top-level package` | Chạy file test trực tiếp (`python tests/test_x.py`) | Luôn chạy qua `python -m pytest` |
| `UnicodeDecodeError` khi đọc CSV/JSONL | File được ghi UTF-8 BOM | Dùng `encoding="utf-8"` (Storage đã làm) |
| `pydantic.ValidationError` không mong muốn | Field đang bị strict | Đọc lại docstring của model trong `models/base_models.py` |
| Test chậm / treo | Có smoke test chạm mạng mà quên `RUN_NETWORK_TESTS=0` | Check `tests/smoke/`, hoặc chạy `pytest -m "not smoke"` |
| `pytest` không tìm thấy test | Thiếu `pytest.ini` | File `pytest.ini` đã có sẵn ở repo root |
| Lỗi permission khi tạo `.venv` | Đang ở thư mục read-only | Chọn thư mục khác, hoặc dùng quyền admin |

---

## 7. Checklist trước khi commit

Sau khi sửa code, trước khi commit:

```powershell
.venv\Scripts\python.exe -m pytest -v
```

Nếu **36 passed** → an toàn commit. Nếu có fail → fix trước, không commit code đỏ.
