"""Unit tests for the Tiki parsers.

We don't hit the network — each parser is exercised against an inline
HTML fixture (a `__NEXT_DATA__` blob) that mimics the shape Tiki uses.
"""

from __future__ import annotations

import json

from crawlers.tiki.comment_parser import parse_comments_html
from crawlers.tiki.keyword_parser import parse_search_html
from crawlers.tiki.menu_parser import parse_menu_html, parse_seed
from crawlers.tiki.menu_seed import TIKI_MENU_SEED, find_seed_category
from crawlers.tiki.product_parser import parse_products_html, parse_products_json
from models import Platform


# ----------------------------------------------------------------- helpers


def _wrap_next_data(payload: dict) -> str:
    """Wrap a dict in the Tiki page's <script id=__NEXT_DATA__> envelope."""
    return f'<html><head><script id="__NEXT_DATA__" type="application/json">{json.dumps(payload)}</script></head><body></body></html>'


# ----------------------------------------------------------------- menu

class TestMenuParser:
    def test_parse_seed_yields_all_categories(self):
        cats = parse_seed(TIKI_MENU_SEED)
        assert len(cats) == len(TIKI_MENU_SEED)
        for c in cats:
            assert c.platform is Platform.TIKI
            assert 1 <= c.level <= 3

    def test_find_seed_category_by_name(self):
        result = find_seed_category("Laptop - Thiết bị IT")
        assert result is not None
        assert result["id"] == 3

    def test_find_seed_category_unknown(self):
        assert find_seed_category("khong-ton-tai") is None

    def test_parse_menu_html_empty_when_no_next_data(self):
        assert parse_menu_html("<html>no data</html>") == []

    def test_parse_menu_html_extracts_breadcrumb(self):
        payload = {
            "props": {
                "pageProps": {
                    "breadcrumb": [
                        {"category_id": 1, "text": "Đồ gia dụng", "href": "https://tiki.vn/do-gia-dung"},
                        {"category_id": 700, "text": "Đồ dùng nhà bếp", "href": "https://tiki.vn/do-dung-nha-bep"},
                    ]
                }
            }
        }
        cats = parse_menu_html(_wrap_next_data(payload))
        assert len(cats) == 2
        assert cats[0].name == "Đồ gia dụng"
        assert cats[1].name == "Đồ dùng nhà bếp"
        assert cats[1].level == 2
        assert cats[0].platform is Platform.TIKI


# --------------------------------------------------------------- products


class TestProductParser:
    def test_parses_minimal_product_dict(self):
        payload = {
            "props": {"pageProps": {"data": {"searchResult": {
                "products": [
                    {"id": 1, "name": "iPhone 15", "price": 20000000, "url_path": "/iphone-15"}
                ]
            }}}}
        }
        prods = parse_products_html(_wrap_next_data(payload))
        assert len(prods) == 1
        p = prods[0]
        assert p.platform is Platform.TIKI
        assert p.product_id == "1"
        assert p.name == "iPhone 15"
        assert p.price == 20000000
        assert p.url == "https://tiki.vn/iphone-15"

    def test_skips_items_missing_id_or_name(self):
        payload = {"props": {"pageProps": {"data": [
            {"id": 1, "name": "ok", "price": 1, "url_path": "/x"},
            {"name": "no id", "price": 1, "url_path": "/x"},   # rejected
            {"id": 2},                                          # rejected (no name/url/price)
        ]}}}
        prods = parse_products_html(_wrap_next_data(payload))
        assert [p.product_id for p in prods] == ["1"]

    def test_recurses_into_nested_lists(self):
        payload = {"props": {"pageProps": {"deep": [
            {"nested": [
                {"id": 99, "name": "deep product", "price": 100, "url_path": "/deep"}
            ]}
        ]}}}
        prods = parse_products_html(_wrap_next_data(payload))
        assert len(prods) == 1 and prods[0].product_id == "99"

    def test_dedups_repeated_products(self):
        payload = {"props": {"pageProps": {"data": [
            {"id": 5, "name": "x", "price": 10, "url_path": "/x"},
            {"id": 5, "name": "x", "price": 10, "url_path": "/x"},
        ]}}}
        prods = parse_products_html(_wrap_next_data(payload))
        assert len(prods) == 1

    def test_handles_malformed_json(self):
        html = '<html><script id="__NEXT_DATA__">not-json</script></html>'
        assert parse_products_html(html) == []

    def test_empty_html_returns_empty(self):
        assert parse_products_html("") == []

    def test_parse_products_json_list(self):
        items = [{"id": 7, "name": "a", "price": 100, "url_path": "/a"}]
        prods = parse_products_json(items)
        assert len(prods) == 1 and prods[0].product_id == "7"

    def test_parse_products_json_wrapped(self):
        payload = {"data": [{"id": 8, "name": "b", "price": 200, "url_path": "/b"}]}
        prods = parse_products_json(payload)
        assert len(prods) == 1 and prods[0].product_id == "8"

    def test_category_path_from_categories_list(self):
        payload = {"props": {"pageProps": {"data": [
            {"id": 1, "name": "x", "price": 1, "url_path": "/x",
             "categories": {"name": ["Điện tử", "Điện thoại"]}}
        ]}}}
        prods = parse_products_html(_wrap_next_data(payload))
        assert prods[0].category_path == "Điện tử > Điện thoại"

    def test_normalizes_bare_relative_url(self):
        """Tiki emits URLs without a leading slash — must resolve to tiki.vn."""
        payload = {"props": {"pageProps": {"data": [
            {"id": 1, "name": "x", "price": 1,
             "url_path": "apple-iphone-17-pro-max-p278628866.html?spid=278630786"}
        ]}}}
        prods = parse_products_html(_wrap_next_data(payload))
        assert prods[0].url == "https://tiki.vn/apple-iphone-17-pro-max-p278628866.html?spid=278630786"

    def test_normalizes_protocol_relative_url(self):
        payload = {"props": {"pageProps": {"data": [
            {"id": 1, "name": "x", "price": 1, "url_path": "//tiki.vn/foo"}
        ]}}}
        prods = parse_products_html(_wrap_next_data(payload))
        assert prods[0].url == "https://tiki.vn/foo"


# --------------------------------------------------------------- comments


class TestCommentParser:
    def test_parses_basic_review(self):
        payload = {
            "props": {"pageProps": {"reviews": [
                {"id": "r1", "content": "good", "customer_name": "An", "rating": 5, "created_at": "2026-01-01"}
            ]}}
        }
        cs = parse_comments_html(_wrap_next_data(payload), product_id="P1")
        assert len(cs) == 1
        assert cs[0].platform is Platform.TIKI
        assert cs[0].product_id == "P1"
        assert cs[0].author == "An"
        assert cs[0].rating == 5

    def test_falls_back_to_product_id_when_missing(self):
        payload = {
            "props": {"pageProps": {"data": {"product": {
                "reviews": [{"id": "r1", "content": "ok", "rating": 4}]
            }}}}
        }
        cs = parse_comments_html(_wrap_next_data(payload), product_id="ABC")
        assert len(cs) == 1 and cs[0].product_id == "ABC"

    def test_rejects_review_outside_rating_range(self):
        """Out-of-range ratings are coerced to None, but the comment is still kept."""
        payload = {"props": {"pageProps": {"reviews": [
            {"id": "r1", "content": "bad", "rating": 10},
            {"id": "r2", "content": "ok", "rating": 0},
            {"id": "r3", "content": "good", "rating": 4},
        ]}}}
        cs = parse_comments_html(_wrap_next_data(payload), product_id="P1")
        assert len(cs) == 3
        by_id = {c.comment_id: c for c in cs}
        assert by_id["r1"].rating is None  # coerced out-of-range
        assert by_id["r2"].rating is None
        assert by_id["r3"].rating == 4

    def test_handles_empty_or_broken_pages(self):
        assert parse_comments_html("") == []
        assert parse_comments_html("<html>no data</html>") == []

    def test_search_alias_is_same_function(self):
        from crawlers.tiki.product_parser import parse_products_html
        assert parse_search_html is parse_products_html


# --------------------------------------------------------------- registry


class TestTikiCrawlerRegistration:
    def test_tiki_crawler_is_registered(self):
        from services.platform_registry import get_registry
        reg = get_registry()
        assert Platform.TIKI in reg
        from crawlers.tiki.tiki_crawler import TikiCrawler
        assert isinstance(reg.get(Platform.TIKI), TikiCrawler)
