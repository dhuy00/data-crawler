"""Sendo crawler package — Phase 4.

Strategy: use the public Sendo API at `api.sendo.vn/web/...`. It
returns well-formed JSON for search, categories, and product detail.
Comments come from the same review endpoint used internally. Playwright
fallback exists for rare drift.
"""

from . import sendo_crawler  # noqa: F401  triggers @register(Platform.SENDO)
