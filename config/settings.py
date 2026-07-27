"""
Configuration settings for Tiki crawling framework.

Loads from environment variables with sensible defaults.
"""
import os
from pathlib import Path
from typing import Optional


class Settings:
    """Central configuration object for crawling framework."""

    # ==========================================
    # BASIC SETTINGS
    # ==========================================
    PROJECT_ROOT = Path(__file__).parent.parent
    OUTPUT_DIR = PROJECT_ROOT / "outputs"
    RAW_OUTPUT_DIR = OUTPUT_DIR
    PROCESSED_OUTPUT_DIR = OUTPUT_DIR / "processed"
    ANALYTICS_OUTPUT_DIR = OUTPUT_DIR / "analytics_ready"

    # ==========================================
    # LOGGING SETTINGS
    # ==========================================
    LOG_LEVEL = os.getenv("TIKI_LOG_LEVEL", "INFO")
    LOG_FILE = PROJECT_ROOT / "logs" / "tiki_crawl.log"

    # ==========================================
    # BROWSER SETTINGS
    # ==========================================
    BROWSER_HEADLESS = os.getenv("TIKI_BROWSER_HEADLESS", "true").lower() == "true"
    BROWSER_TIMEOUT = int(os.getenv("TIKI_BROWSER_TIMEOUT", "15000"))  # milliseconds
    BROWSER_VIEWPORT_WIDTH = int(os.getenv("TIKI_BROWSER_VIEWPORT_WIDTH", "1920"))
    BROWSER_VIEWPORT_HEIGHT = int(os.getenv("TIKI_BROWSER_VIEWPORT_HEIGHT", "1080"))
    BROWSER_USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]

    # ==========================================
    # HTTP CLIENT SETTINGS
    # ==========================================
    HTTP_TIMEOUT = int(os.getenv("TIKI_HTTP_TIMEOUT", "30"))
    HTTP_RETRIES = int(os.getenv("TIKI_HTTP_RETRIES", "3"))
    HTTP_BACKOFF_FACTOR = float(os.getenv("TIKI_HTTP_BACKOFF_FACTOR", "1.0"))

    # ==========================================
    # RATE LIMITING
    # ==========================================
    REQUEST_DELAY_MIN = float(os.getenv("TIKI_REQUEST_DELAY_MIN", "0.5"))
    REQUEST_DELAY_MAX = float(os.getenv("TIKI_REQUEST_DELAY_MAX", "2.0"))

    # ==========================================
    # MENU CRAWLER SETTINGS
    # ==========================================
    MENU_OUTPUT_FORMAT = os.getenv("TIKI_MENU_OUTPUT_FORMAT", "csv")  # csv, parquet, xlsx
    MENU_OUTPUT_FILE = os.getenv("TIKI_MENU_OUTPUT_FILE", "tiki_menu_3_levels")

    # ==========================================
    # PRODUCT CRAWLER SETTINGS
    # ==========================================
    PRODUCT_LIMIT_PER_PAGE = int(os.getenv("TIKI_PRODUCT_LIMIT_PER_PAGE", "40"))
    PRODUCT_MAX_PAGES = None
    PRODUCT_MAX_CATEGORIES = None
    PRODUCT_SAVE_EVERY_N_CATEGORIES = int(os.getenv("TIKI_SAVE_EVERY_CATEGORIES", "20"))
    PRODUCT_OUTPUT_FORMAT = os.getenv("TIKI_PRODUCT_OUTPUT_FORMAT", "csv")
    PRODUCT_OUTPUT_FILE = os.getenv("TIKI_PRODUCT_OUTPUT_FILE", "tiki_products")

    # Parse optional env vars
    _max_pages = os.getenv("TIKI_MAX_PAGES")
    if _max_pages:
        PRODUCT_MAX_PAGES = int(_max_pages)

    _max_categories = os.getenv("TIKI_MAX_CATEGORIES")
    if _max_categories:
        PRODUCT_MAX_CATEGORIES = int(_max_categories)

    # ==========================================
    # COMMENT CRAWLER SETTINGS
    # ==========================================
    COMMENT_LIMIT_PER_PAGE = int(os.getenv("TIKI_COMMENT_LIMIT_PER_PAGE", "20"))
    COMMENT_MAX_PAGES = None
    COMMENT_MAX_PRODUCTS = None
    COMMENT_SAVE_EVERY_N_PRODUCTS = int(os.getenv("TIKI_SAVE_EVERY_PRODUCTS", "20"))
    COMMENT_OUTPUT_FORMAT = os.getenv("TIKI_COMMENT_OUTPUT_FORMAT", "csv")
    COMMENT_OUTPUT_FILE = os.getenv("TIKI_COMMENT_OUTPUT_FILE", "tiki_comments")

    # Parse optional env vars
    _max_comment_pages = os.getenv("TIKI_MAX_COMMENT_PAGES")
    if _max_comment_pages:
        COMMENT_MAX_PAGES = int(_max_comment_pages)

    _max_products = os.getenv("TIKI_MAX_PRODUCTS")
    if _max_products:
        COMMENT_MAX_PRODUCTS = int(_max_products)

    # ==========================================
    # KEYWORD CRAWLER SETTINGS
    # ==========================================
    KEYWORD_MAX_PRODUCTS = int(os.getenv("TIKI_KEYWORD_MAX_PRODUCTS", "100"))

    # ==========================================
    # RANKING SERVICE SETTINGS
    # ==========================================
    RANKING_WEIGHT_RATING = float(os.getenv("TIKI_RANKING_WEIGHT_RATING", "0.4"))
    RANKING_WEIGHT_REVIEWS = float(os.getenv("TIKI_RANKING_WEIGHT_REVIEWS", "0.4"))
    RANKING_WEIGHT_SOLD = float(os.getenv("TIKI_RANKING_WEIGHT_SOLD", "0.2"))

    # ==========================================
    # TIKI API ENDPOINTS
    # ==========================================
    TIKI_BASE_URL = "https://tiki.vn"
    TIKI_MENU_URL = "https://tiki.vn/"
    TIKI_PRODUCT_API_URL = "https://tiki.vn/api/personalish/v1/blocks/listings"
    TIKI_REVIEW_API_URL = "https://tiki.vn/api/v2/reviews"
    TIKI_SEARCH_API_URL = "https://tiki.vn/api/v2/products"

    # ==========================================
    # EXPORT SETTINGS
    # ==========================================
    EXPORT_INCLUDE_RAW = os.getenv("TIKI_EXPORT_INCLUDE_RAW", "true").lower() == "true"
    EXPORT_INCLUDE_PROCESSED = os.getenv("TIKI_EXPORT_INCLUDE_PROCESSED", "true").lower() == "true"
    EXPORT_INCLUDE_ANALYTICS = os.getenv("TIKI_EXPORT_INCLUDE_ANALYTICS", "true").lower() == "true"


# Create singleton instance
settings = Settings()
