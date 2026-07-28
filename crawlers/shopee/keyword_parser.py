"""Parse Shopee search-results JSON into `Product` models.

Search endpoint: `/api/v4/search/search` with `keyword`, `page`,
`limit` parameters. Response shape: `{"items": [...], "total_count": N}`.
Same machinery as `product_parser`; kept as a thin alias for clarity.
"""

from __future__ import annotations

from .product_parser import parse_products_json

# Re-export under a search-specific name.
parse_search_json = parse_products_json
