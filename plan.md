# Plan cho bài lab Tiki Comment Crawling

## 1. Requirement

- Hiểu mục tiêu của dự án: crawl dữ liệu từ Tiki.vn gồm menu, sản phẩm và bình luận.
- Chạy được ít nhất một pipeline chính từ CLI.
- Xuất được kết quả ra các file đầu ra trong thư mục outputs/.
- Có thể dùng các mode:
  - menu
  - menu -> products
  - products_from_menu
  - comments_from_products
  - full
  - keyword
- Đảm bảo môi trường Python đã cài đủ thư viện từ requirements.txt.

## 2. Các bước cần thiết để thực hiện

### Bước 1: Chuẩn bị môi trường
- Tạo môi trường ảo Python.
- Cài đặt dependencies:
  - python -m venv .venv
  - .venv\Scripts\activate
  - python.exe -m pip install --upgrade pip
  - pip install -r requirements.txt

### Bước 2: Đọc hiểu cấu trúc dự án
- Xem các file chính:
  - main.py
  - README.md
  - requirements.txt
  - pipelines/*.py
  - crawlers/*.py
  - services/*.py
  - models/*.py
  - config/settings.py

### Bước 3: Xác định mode chạy
- Chọn mode phù hợp với mục tiêu:
  - menu: chỉ crawl danh mục
  - full: crawl menu -> sản phẩm -> bình luận
  - keyword: crawl theo từ khóa

### Bước 4: Thực hiện crawl dữ liệu
- Chạy pipeline bằng lệnh:
  - python main.py --mode menu
  - python main.py --mode full
  - python main.py --mode keyword --keywords "Iphone"

### Bước 5: Kiểm tra kết quả đầu ra
- Mở thư mục outputs/ để xem các file xuất ra:
  - tiki_menu_3_levels.csv
  - tiki_products.csv
  - tiki_comments.csv
  - keyword_top_*.csv
  - keyword_comments_*.csv

### Bước 6: Xử lý lỗi nếu có
- Nếu chạy lỗi, kiểm tra:
  - thư viện chưa cài
  - mạng / proxy / firewall
  - cấu hình trong config/settings.py
  - lỗi từ API của Tiki

### Bước 7: Ghi chú và tối ưu hóa
- Ghi lại các lệnh chạy thành công.
- Ghi lại các file đầu ra tạo được.
- Nếu cần, điều chỉnh tham số như từ khóa, output dir, giới hạn crawl.

## 3. Kết quả mong đợi

- Có thể chạy được ít nhất một pipeline thành công.
- Các file dữ liệu được tạo trong outputs/.
- Người thực hiện hiểu được luồng crawl: menu -> products -> comments.
