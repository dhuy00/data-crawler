# Tiki Crawling Framework (Refactored)

This project is a production-ready, modular crawling framework for Tiki.vn.
It organizes code into reusable services, crawlers, and pipelines.

Features
- Playwright-based menu crawler (async & API accelerated)
- HTTP-based product and comment crawlers with retry and rate limiting
- Keyword search crawler
- Standalone pipelines: `menu`, `menu -> products`, `products_from_menu`, `comments_from_products`, `full`, `keyword`
- Ranking service with weighted scoring
- Pydantic models for validation
- Export to CSV/XLSX/Parquet (saved by default in `outputs/`)
- Logging with loguru

## Quick start
```powershell
python -m venv .venv
.venv\Scripts\activate
python.exe -m pip install --upgrade pip
pip install -r requirements.txt
```

# Run examples

## 1. Menu pipeline (`menu`)
Crawls menu hierarchy (categories) only and saves to `outputs/tiki_menu_3_levels.csv`:
```powershell
python main.py --mode menu
```

## 2. Menu -> Products pipeline (`menu -> products`)
Crawls menu hierarchy and product listings per category, saving to `outputs/`:
```powershell
python main.py --mode "menu -> products"
# or
python main.py --mode menu_products
```

## 3. Products from Menu file (`products_from_menu`)
Crawls product listings using a previously saved menu/categories file (`outputs/tiki_menu_3_levels.csv`):
```powershell
python main.py --mode products_from_menu
# Or with a custom category file
python main.py --mode products_from_menu --input-file "outputs/tiki_menu_3_levels.csv"
```

## 4. Comments from Products file (`comments_from_products`)
Crawls comments using a previously saved products file (`outputs/tiki_products.csv`):
```powershell
python main.py --mode comments_from_products
# Or with a custom product file
python main.py --mode comments_from_products --input-file "outputs/custom_products.csv"
```

## 5. Full pipeline (`full`)
Crawls menu, products, and product comments:
```powershell
python main.py --mode full
```

## 6. Keyword pipeline (`keyword`)
Searches products by keywords and crawls top comments:
```powershell
python main.py --mode keyword --keywords "Iphone"
```

## Custom output directory
By default, all pipeline results are saved in the `outputs/` folder. You can override the output folder using `--output-dir`:
```powershell
python main.py --mode products_from_menu --output-dir "custom_outputs"
```

# Project structure
```
project/
├── config/
├── core/
├── crawlers/
├── services/
├── pipelines/
│   ├── full_pipeline.py
│   ├── keyword_pipeline.py
│   ├── menu_pipeline.py
│   ├── menu_products_pipeline.py
│   ├── products_from_menu_pipeline.py
│   └── comments_from_products_pipeline.py
├── models/
├── outputs/
├── main.py
├── requirements.txt
└── README.md
```

Notes
- Adjust configuration via environment variables or `config/settings.py`.
- This framework is designed for teaching and demoing production-ready crawling patterns.

License
MIT
