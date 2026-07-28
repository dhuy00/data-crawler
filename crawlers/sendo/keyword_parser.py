"""Parse Sendo search-results JSON into `Product` models."""

from __future__ import annotations

from .product_parser import parse_products_json

parse_search_json = parse_products_json
