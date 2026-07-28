"""Parse Lazada search-results JSON into `Product` models.

Same machinery as `product_parser`; kept as a thin alias so the
keyword pipeline reads clean.
"""

from __future__ import annotations

from .product_parser import parse_products_json

parse_search_json = parse_products_json
