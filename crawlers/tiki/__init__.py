"""Tiki adapter package — crawler + parsers.

The crawler implements `BaseCrawler` for `Platform.TIKI`. Menu is sourced
from a curated static seed (see `menu_seed.py`) and refreshed on demand
via `BrowserManager`. Per-category listings and reviews are parsed from
Tiki's HTML pages via `__NEXT_DATA__` extraction in `*_parser.py`.
"""

from .tiki_crawler import TikiCrawler
from .menu_seed import TIKI_MENU_SEED, find_seed_category

__all__ = ["TikiCrawler", "TIKI_MENU_SEED", "find_seed_category"]