"""Parse Tiki search results for the keyword pipeline.

Same machinery as `product_parser`, but includes a thin alias for clarity
in pipeline code: `parse_search_html(html)` -> list[Product].
"""

from __future__ import annotations

from .product_parser import parse_products_html

# Re-export the HTML parser under a search-specific name.
parse_search_html = parse_products_html
