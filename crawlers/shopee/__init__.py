"""Shopee crawler package — Phase 2.

Public API strategy: try Shopee's undocumented JSON endpoints first
(`/api/v4/...`), fall back to Playwright DOM scraping on schema drift
or non-JSON response. Menu comes from a curated seed (Shopee has no
public category tree endpoint).
"""

from . import shopee_crawler  # noqa: F401  triggers @register(Platform.SHOPEE)
