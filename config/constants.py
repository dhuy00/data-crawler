"""
Constants for Tiki crawling framework.
"""

# ==========================================
# HTTP HEADERS
# ==========================================
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://tiki.vn/",
    "Origin": "https://tiki.vn",
}

# ==========================================
# XPATHS FOR SELENIUM/PLAYWRIGHT
# ==========================================
MENU_LEVEL_1_XPATH = '//div[contains(@class,"hagwli")]//a[@href]'
MENU_LEVEL_2_3_XPATH = '//a[contains(@href,"/c")]'

# ==========================================
# CATEGORY FILTERING RULES
# ==========================================
CATEGORY_MIN_NAME_LENGTH = 1
CATEGORY_MAX_NAME_LENGTH = 60
CATEGORY_REQUIRED_PATH_SEGMENT = "/c"
CATEGORY_EXCLUDE_PARAMS = ["from="]

# ==========================================
# OUTPUT FORMATS
# ==========================================
SUPPORTED_EXPORT_FORMATS = ["csv", "parquet", "xlsx"]
DEFAULT_EXPORT_FORMAT = "csv"

# ==========================================
# PAGINATION DEFAULTS
# ==========================================
DEFAULT_PAGE_NUMBER = 1
DEFAULT_COMMENT_PAGE_SIZE = 20
DEFAULT_PRODUCT_PAGE_SIZE = 40

# ==========================================
# RETRY CONFIGURATION
# ==========================================
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 1.0
RETRY_WAIT_MULTIPLIER = 1

# ==========================================
# RANKING ALGORITHM
# ==========================================
RANKING_SCORE_FORMULA = "weighted_sum"  # weighted_sum, normalized, etc.
DEFAULT_TOP_N = 50

# ==========================================
# TIME DELAYS (seconds)
# ==========================================
RANDOM_DELAY_MIN = 0.2
RANDOM_DELAY_MAX = 0.8
CATEGORY_LOAD_DELAY = 0.5
SUBCATEGORY_LOAD_DELAY = 0.1
BROWSER_NAVIGATION_WAIT = 500  # milliseconds

# ==========================================
# REGEX PATTERNS
# ==========================================
CATEGORY_ID_PATTERN = r"/c(\d+)"
PRODUCT_ID_PATTERN = r"/p(\d+)"
PRICE_CLEANUP_PATTERN = r"[^\d.]"

# ==========================================
# DEDUPLICATION KEYS
# ==========================================
PRODUCT_DEDUP_KEYS = ["category_id", "product_id", "seller_product_id"]
COMMENT_DEDUP_KEYS = ["comment_id"]
CATEGORY_DEDUP_KEYS = ["lv1_name", "lv2_name", "lv3_name"]

# ==========================================
# API PARAMETERS
# ==========================================
PRODUCT_API_PARAMS = {
    "include": "advertisement",
    "aggregations": 2,
    "trackity_id": "",
    "urlKey": "",
}

SEARCH_API_PARAMS = {
    "include": "advertisement",
}

REVIEW_API_PARAMS = {
    "include": "comments,contribute_info,attribute_vote_summary",
    "sort": "score|desc,id|desc,stars|all",
}

# ==========================================
# ERROR MESSAGES
# ==========================================
MENU_NOT_FOUND_ERROR = "Menu data not found. Please run menu crawler first."
PRODUCT_NOT_FOUND_ERROR = "No products found in the specified category."
COMMENT_NOT_FOUND_ERROR = "No comments found for the specified product."

# ==========================================
# DATA VALIDATION
# ==========================================
MIN_RATING = 0.0
MAX_RATING = 5.0
MIN_REVIEW_COUNT = 0
MIN_QUANTITY_SOLD = 0

# Comment validation thresholds
MIN_COMMENT_CONTENT_LENGTH = 3  # Minimum characters in comment content
MAX_COMMENT_CONTENT_LENGTH = 10000  # Maximum to detect spam
MIN_COMMENT_TITLE_LENGTH = 3  # Minimum comment title length
MAX_COMMENT_TITLE_LENGTH = 200  # Maximum comment title length

# Comment quality filters
ENABLE_STRICT_COMMENT_VALIDATION = True  # Enable strict validation by default
FILTER_SELLER_RESPONSES = True  # Filter out seller reply comments
FILTER_SPAM_COMMENTS = True  # Filter comments matching spam patterns
