# Hướng dẫn sử dụng Tiki Crawling Framework

## 1. Cài đặt môi trường

```powershell
cd D:\temp\data-crawler\data-crawler
python -m venv .venv
.venv\Scripts\activate
python.exe -m pip install --upgrade pip
pip install -r requirements.txt
```

Sau đó cài Playwright browser:

```powershell
playwright install chromium
```

## 2. Các chế độ chạy

Tất cả chạy qua `python main.py --mode <chế độ>`:

| Mode | Lệnh | Làm gì | Output |
|---|---|---|---|
| `menu` | `python main.py --mode menu` | Chỉ crawl cây danh mục 3 cấp | `outputs/tiki_menu_3_levels.csv` |
| `menu_products` | `python main.py --mode "menu -> products"` | Crawl menu + sản phẩm theo từng danh mục | nhiều file trong `outputs/` |
| `products_from_menu` | `python main.py --mode products_from_menu` | Đọc file menu có sẵn để crawl sản phẩm | `outputs/tiki_products.csv` |
| `comments_from_products` | `python main.py --mode comments_from_products` | Đọc file sản phẩm có sẵn để crawl bình luận | `outputs/tiki_comments.csv` |
| `full` | `python main.py --mode full` | Chạy cả 3 bước: menu → products → comments | nhiều file |
| `keyword` | `python main.py --mode keyword --keywords "Iphone,SamSung"` | Tìm theo từ khóa rồi crawl top comments | theo từ khóa |

## 3. Các tuỳ chọn CLI

- `--headless` / bỏ trống: chạy trình duyệt có/không giao diện (mặc định là headless)
- `--keywords "kw1,kw2"`: danh sách từ khóa cho mode `keyword`
- `--input-file "path/to/file.csv"`: file input cho 2 mode `products_from_menu` và `comments_from_products`
- `--output-dir "thư_mục_tuỳ_chỉnh"`: đổi thư mục xuất (mặc định `outputs/`)

## 4. Các ví dụ cụ thể

### Crawl đầy đủ

```powershell
python main.py --mode full
```

### Resume từ file đã có (chạy tiếp từ kết quả trước)

```powershell
# Lần đầu: crawl menu
python main.py --mode menu

# Lần sau: tận dụng menu để crawl sản phẩm
python main.py --mode products_from_menu --input-file "outputs/tiki_menu_3_levels.csv"

# Tiếp: crawl bình luận từ sản phẩm đã có
python main.py --mode comments_from_products --input-file "outputs/tiki_products.csv"
```

### Tìm sản phẩm theo từ khóa

```powershell
python main.py --mode keyword --keywords "Iphone 15"
```

## 5. Cấu hình nâng cao qua biến môi trường

Tất cả đọc từ env vars (theo `config/settings.py`):

| Biến | Mặc định | Ý nghĩa |
|---|---|---|
| `TIKI_LOG_LEVEL` | `INFO` | Cấp độ log |
| `TIKI_BROWSER_HEADLESS` | `true` | Chạy ẩn/hiện trình duyệt |
| `TIKI_BROWSER_TIMEOUT` | `15000` | Timeout (ms) |
| `TIKI_HTTP_TIMEOUT` | `30` | HTTP timeout (giây) |
| `TIKI_HTTP_RETRIES` | `3` | Số lần retry HTTP |
| `TIKI_REQUEST_DELAY_MIN` | `0.5` | Rate limit tối thiểu (giây) |
| `TIKI_REQUEST_DELAY_MAX` | `2.0` | Rate limit tối đa (giây) |
| `TIKI_MAX_PAGES` | `None` | Giới hạn số trang |
| `TIKI_MAX_CATEGORIES` | `None` | Giới hạn số danh mục |
| `TIKI_MAX_PRODUCTS` | `None` | Giới hạn số sản phẩm |
| `TIKI_PRODUCT_OUTPUT_FORMAT` | `csv` | `csv` / `parquet` / `xlsx` |
| `TIKI_RANKING_WEIGHT_RATING` | `0.4` | Trọng số ranking theo rating |
| `TIKI_RANKING_WEIGHT_REVIEWS` | `0.4` | Trọng số ranking theo số review |
| `TIKI_RANKING_WEIGHT_SOLD` | `0.2` | Trọng số ranking theo số lượng bán |

### Ví dụ giới hạn crawl

```powershell
$env:TIKI_MAX_PAGES = "5"
$env:TIKI_MAX_CATEGORIES = "3"
$env:TIKI_PRODUCT_OUTPUT_FORMAT = "parquet"
python main.py --mode menu_products
```

## 6. Workflow khuyến nghị khi bắt đầu

1. **Bước 1**: Chạy `python main.py --mode menu` để có file `tiki_menu_3_levels.csv`
2. **Bước 2**: Mở file CSV kiểm tra — chỉnh tay nếu muốn lọc danh mục
3. **Bước 3**: `python main.py --mode products_from_menu --input-file "outputs/tiki_menu_3_levels.csv"`
4. **Bước 4**: `python main.py --mode comments_from_products --input-file "outputs/tiki_products.csv"`

Cách chia bước như vậy giúp bạn **dừng/resume** giữa chừng và **kiểm tra** dữ liệu sau mỗi tầng, thay vì chạy `full` một lần — tránh mất thời gian nếu lỗi xảy ra ở bước sau.

## 7. Output nằm ở đâu

- File kết quả: `outputs/` (CSV / Parquet / XLSX)
- Log: `logs/tiki_crawl.log`

Bạn chỉ cần mở `outputs/*.csv` bằng Excel/Pandas để xem dữ liệu đã crawl được.

## 8. Cấu trúc project

```
project/
├── config/         # Cấu hình & hằng số
├── core/           # Thành phần lõi: browser, http_client, retry, storage, logger
├── crawlers/       # Các crawler: menu, product, comment, keyword
├── services/       # Business logic: category, product, comment, ranking
├── pipelines/      # 6 pipeline độc lập
├── models/         # Pydantic models
├── outputs/        # Kết quả crawl
├── logs/           # File log
├── main.py         # Entrypoint CLI
├── requirements.txt
└── README.md
```

## 9. Mẹo & lưu ý

- **Lần đầu chạy chậm**: Playwright cần tải browser và Tiki có thể chặn nếu request quá nhanh. Đừng giảm `TIKI_REQUEST_DELAY_MIN/MAX` xuống quá thấp.
- **Bị block / IP bị rate-limit**: Tăng `TIKI_REQUEST_DELAY_MIN/MAX` và `TIKI_HTTP_RETRIES`.
- **Muốn crawl nhanh hơn**: Chạy `headless` (mặc định), giảm số danh mục / trang qua các biến env ở trên.
- **Dữ liệu CSV lớn**: Chuyển sang `parquet` để tiết kiệm dung lượng (`TIKI_PRODUCT_OUTPUT_FORMAT=parquet`).
- **Chạy nhiều lần cùng mode**: Các pipeline đã có sẵn logic dedup theo `category_id + product_id` nên chạy lại sẽ không trùng.