"""Lazada crawler package — Phase 3.

Strategy mirrors Shopee: public API first (`/catalog/` JSON endpoint
that underlies the search results page), Playwright DOM fallback on
schema drift or non-JSON response. Comment API (`/pdp/review/...`) is
gated; we accept whatever the public path returns, otherwise Playwright
HTML scrape.
"""

from . import lazada_crawler  # noqa: F401  triggers @register(Platform.LAZADA)
