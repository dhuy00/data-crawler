"""Unit tests for Lazada parsers and crawler registration."""

from __future__ import annotations

from datetime import datetime

import pytest

from crawlers.lazada import comment_parser, keyword_parser, menu_parser, product_parser
from crawlers.lazada.lazada_crawler import LazadaCrawler
from models import Category, Comment, Platform, Product
from models.platform import Platform as PlatformEnum
from services.platform_registry import get_registry


# -------------------------------------------------------------- helpers

def _lazada_item(
    id: str = "123456",
    name: str = "Tai nghe Bluetooth",
    price: str = "259.00",
    original_price: str = "399.00",
    rating: float = 4.7,
    review_count: int = 88,
    sold: int = 1500,
) -> dict:
    return {
        "id": id,
        "name": name,
        "price": price,
        "originalPrice": original_price,
        "ratingScore": rating,
        "review": review_count,
        "soldCount": sold,
        "productUrl": f"https://www.lazada.vn/products/p{id}.html",
        "pdtCategoryName": "Electronics/Audio",
    }


def _lazada_review(
    rid: str = "abc123",
    pid: str = "123456",
    user: str = "khach_a",
    rating: int = 5,
    content: str = "Sản phẩm tốt.",
    submit_time: str = "2026-07-01 10:00:00",
) -> dict:
    return {
        "reviewId": rid,
        "productId": pid,
        "userName": user,
        "rating": rating,
        "reviewContent": content,
        "submitTime": submit_time,
    }


# ----------------------------------------------------------- products


def test_parse_products_json_products_wrapper() -> None:
    payload = {"products": [_lazada_item()]}
    out = product_parser.parse_products_json(payload)
    assert len(out) == 1
    p = out[0]
    assert isinstance(p, Product)
    assert p.platform == Platform.LAZADA
    assert p.product_id == "123456"
    assert p.name == "Tai nghe Bluetooth"
    assert p.price == 259.0
    assert p.original_price == 399.0
    assert p.rating == pytest.approx(4.7)
    assert p.review_count == 88
    assert p.sold_count == 1500
    assert p.category_path == "Electronics/Audio"
    assert p.url == "https://www.lazada.vn/products/p123456.html"
    assert isinstance(p.crawled_at, datetime)


def test_parse_products_json_data_items_inner_wrapper() -> None:
    payload = {"data": {"items": [_lazada_item(id="1"), _lazada_item(id="2")]}}
    out = product_parser.parse_products_json(payload)
    assert {p.product_id for p in out} == {"1", "2"}


def test_parse_products_json_bare_list() -> None:
    out = product_parser.parse_products_json([_lazada_item(id="9")])
    assert len(out) == 1
    assert out[0].product_id == "9"


def test_parse_products_json_dedups() -> None:
    out = product_parser.parse_products_json(
        {"products": [_lazada_item(id="1"), _lazada_item(id="1")]}
    )
    assert len(out) == 1


def test_parse_products_json_skips_missing_id() -> None:
    bad = {"name": "x", "price": "1.00"}
    assert product_parser.parse_products_json({"products": [bad]}) == []


def test_parse_products_json_skips_missing_name() -> None:
    bad = {"id": "1", "price": "1.00"}
    assert product_parser.parse_products_json({"products": [bad]}) == []


def test_parse_products_json_handles_int_price() -> None:
    item = _lazada_item()
    item["price"] = 199
    item["originalPrice"] = 299
    out = product_parser.parse_products_json({"products": [item]})
    assert out[0].price == 199.0
    assert out[0].original_price == 299.0


def test_parse_products_json_invalid_price_raises_returns_none() -> None:
    item = _lazada_item()
    item["price"] = "not-a-number"
    item["originalPrice"] = ""
    out = product_parser.parse_products_json({"products": [item]})
    assert len(out) == 1
    assert out[0].price is None
    assert out[0].original_price is None


def test_parse_products_json_url_fallback() -> None:
    item = _lazada_item(id="42")
    item["productUrl"] = ""
    out = product_parser.parse_products_json({"products": [item]})
    assert out[0].url == "https://www.lazada.vn/products/p42.html"


def test_parse_products_json_url_protocol_relative() -> None:
    item = _lazada_item()
    item["productUrl"] = "//foo.com/x"
    out = product_parser.parse_products_json({"products": [item]})
    assert out[0].url == "https://foo.com/x"


def test_parse_products_json_category_from_nested_list() -> None:
    item = _lazada_item(id="1")
    item["pdtCategoryName"] = ""
    item["categories"] = [{"name": "A"}, {"name": "B"}]
    out = product_parser.parse_products_json({"products": [item]})
    assert out[0].category_path == "A > B"


def test_parse_search_json_alias() -> None:
    a = product_parser.parse_products_json({"products": [_lazada_item()]})
    b = keyword_parser.parse_search_json({"products": [_lazada_item()]})
    assert [p.product_id for p in a] == [p.product_id for p in b]


def test_parse_products_json_garbage_input() -> None:
    assert product_parser.parse_products_json("nope") == []
    assert product_parser.parse_products_json(42) == []
    assert product_parser.parse_products_json(None) == []


def test_parse_products_json_rating_in_dict() -> None:
    item = _lazada_item()
    item["ratingScore"] = None
    item["rating"] = {"average": 4.2}
    out = product_parser.parse_products_json({"products": [item]})
    assert out[0].rating == pytest.approx(4.2)


# ----------------------------------------------------------- comments


def test_parse_comments_json_walks_model_items() -> None:
    payload = {
        "model": {
            "items": [_lazada_review(), _lazada_review(rid="r2")],
            "total": 2,
        }
    }
    out = comment_parser.parse_comments_json(payload, product_id="123456")
    assert len(out) == 2
    assert all(isinstance(c, Comment) for c in out)
    assert {c.comment_id for c in out} == {"abc123", "r2"}
    assert out[0].author == "khach_a"
    assert out[0].rating == 5
    assert out[0].product_id == "123456"
    assert out[0].content == "Sản phẩm tốt."


def test_parse_comments_json_out_of_range_rating() -> None:
    payload = {"items": [_lazada_review(rating=8)]}
    out = comment_parser.parse_comments_json(payload, product_id="1")
    assert out[0].rating is None


def test_parse_comments_json_drops_missing_rid() -> None:
    payload = {"items": [{"reviewContent": "ok", "rating": 4, "productId": "1"}]}
    assert comment_parser.parse_comments_json(payload, product_id="1") == []


def test_parse_comments_json_drops_when_no_productid() -> None:
    payload = {"items": [{"reviewId": "1", "reviewContent": "x", "rating": 5}]}
    assert comment_parser.parse_comments_json(payload, product_id="") == []


def test_parse_comments_json_dedups_by_rid() -> None:
    payload = {"items": [_lazada_review(), _lazada_review()]}
    out = comment_parser.parse_comments_json(payload, product_id="1")
    assert len(out) == 1


def test_parse_comments_html_extracts_initial_state() -> None:
    html = (
        '<html><script>window.__INITIAL_STATE__ = {"items":['
        + '{"reviewId":"1","productId":"9","userName":"a",'
        + '"rating":5,"reviewContent":"ok","submitTime":"2026"}'
        + ']};</script></html>'
    )
    out = comment_parser.parse_comments_html(html, product_id="9")
    assert len(out) == 1
    assert out[0].product_id == "9"
    assert out[0].rating == 5


# ----------------------------------------------------------- menu


def test_menu_seed_yields_categories() -> None:
    cats = menu_parser.parse_seed()
    assert len(cats) >= 10
    assert all(isinstance(c, Category) for c in cats)
    assert all(c.platform == Platform.LAZADA for c in cats)


def test_menu_seed_urls_lazada_vn() -> None:
    for c in menu_parser.parse_seed():
        assert c.url.startswith("https://www.lazada.vn/")


# ----------------------------------------------------------- crawler


def test_lazada_crawler_registered() -> None:
    assert PlatformEnum.LAZADA in get_registry()
    crawler = get_registry().get(PlatformEnum.LAZADA)
    assert isinstance(crawler, LazadaCrawler)
    assert crawler.platform == Platform.LAZADA


def test_crawler_fetch_menu_seed() -> None:
    import asyncio
    cats = asyncio.run(LazadaCrawler().fetch_menu())
    assert len(cats) >= 10
    assert all(c.platform == Platform.LAZADA for c in cats)


def test_crawler_fetch_menu_level_1() -> None:
    import asyncio
    cats = asyncio.run(LazadaCrawler().fetch_menu(level=1))
    assert all(c.level == 1 for c in cats)


def test_crawler_describe() -> None:
    info = LazadaCrawler().describe()
    assert info["platform"] == "lazada"
    assert info["comment_supported"] == "True"


def test_extract_product_id_handles_common_forms() -> None:
    c = LazadaCrawler()
    assert c._extract_product_id("123456") == "123456"
    assert c._extract_product_id("p12345.html") == "12345"
    assert c._extract_product_id("i999") == "999"
    assert c._extract_product_id("abc-9876") == "9876"
    assert c._extract_product_id("xxxxx") == "xxxxx"
