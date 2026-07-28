"""Unit tests for Shopee parsers and crawler registration."""

from __future__ import annotations

from datetime import datetime

import pytest

from crawlers.shopee import comment_parser, keyword_parser, menu_parser, product_parser
from crawlers.shopee.shopee_crawler import ShopeeCrawler
from models import Category, Comment, Platform, Product
from models.platform import Platform as PlatformEnum
from services.platform_registry import get_registry


# -------------------------------------------------------------- helpers

def _shopee_item(
    itemid: str = "1001",
    shopid: str = "2002",
    name: str = "iPhone 15 Pro Max",
    price: int = 25_900_000,  # hundredths
    rating: float = 4.8,
    review_count: int = 42,
    sold: int = 1200,
    catid: str = "84",
) -> dict:
    return {
        "item_basic": {
            "itemid": itemid,
            "shopid": shopid,
            "name": name,
            "price": price,
            "price_before_discount": price + 5_000_000,
            "url": f"https://shopee.vn/product/{shopid}/{itemid}",
        },
        "item_rating": {
            "rating_star": rating,
            "rating_count": review_count,
            "historical_sold": sold,
        },
        "catid": catid,
        "categories": [{"catid": "84", "display_name": "Điện thoại"}],
    }


def _shopee_rating(
    cmtid: str = "9001",
    productid: str = "1001",
    author: str = "khachhang01",
    rating: int = 5,
    comment: str = "Giao hàng nhanh, đóng gói cẩn thận.",
    ctime: str = "1700000000",
) -> dict:
    return {
        "cmtid": cmtid,
        "productid": productid,
        "author_username": author,
        "rating": rating,
        "comment": comment,
        "ctime": ctime,
    }


# ----------------------------------------------------------- products


def test_parse_products_json_unwraps_items_list() -> None:
    payload = {"items": [_shopee_item()], "total_count": 1}
    products = product_parser.parse_products_json(payload)
    assert len(products) == 1
    p = products[0]
    assert isinstance(p, Product)
    assert p.platform == Platform.SHOPEE
    assert p.product_id == "2002_1001"
    assert p.name == "iPhone 15 Pro Max"
    assert p.price == pytest.approx(259.0)  # 25_900_000 / 100_000
    assert p.rating == pytest.approx(4.8)
    assert p.review_count == 42
    assert p.sold_count == 1200
    assert p.category_path == "Điện thoại"
    assert p.url == "https://shopee.vn/product/2002/1001"
    assert isinstance(p.crawled_at, datetime)


def test_parse_products_json_handles_data_items_wrapper() -> None:
    payload = {"data": {"items": [_shopee_item(itemid="2"), _shopee_item(itemid="3")]}}
    products = product_parser.parse_products_json(payload)
    assert len(products) == 2
    assert {p.product_id for p in products} == {"2002_2", "2002_3"}


def test_parse_products_json_handles_bare_list() -> None:
    products = product_parser.parse_products_json([_shopee_item(itemid="5")])
    assert len(products) == 1
    assert products[0].product_id == "2002_5"


def test_parse_products_json_dedups_by_product_id() -> None:
    products = product_parser.parse_products_json(
        {"items": [_shopee_item(itemid="9"), _shopee_item(itemid="9")]}
    )
    assert len(products) == 1


def test_parse_products_json_skips_items_without_name() -> None:
    bad = {"item_basic": {"itemid": "1", "shopid": "2", "price": 1000}}
    products = product_parser.parse_products_json({"items": [bad]})
    assert products == []


def test_parse_products_json_skips_items_without_id() -> None:
    bad = {"item_basic": {"name": "x", "price": 1000}}
    products = product_parser.parse_products_json({"items": [bad]})
    assert products == []


def test_parse_products_json_handles_non_dict_input() -> None:
    assert product_parser.parse_products_json("nope") == []
    assert product_parser.parse_products_json(42) == []
    assert product_parser.parse_products_json(None) == []


def test_parse_products_json_tolerates_garbage_prices() -> None:
    bad = _shopee_item()
    bad["item_basic"]["price"] = None
    bad["item_basic"]["price_before_discount"] = ""
    products = product_parser.parse_products_json({"items": [bad]})
    assert len(products) == 1
    assert products[0].price is None
    assert products[0].original_price is None


def test_parse_products_json_url_fallback_when_missing() -> None:
    item = _shopee_item(itemid="99", shopid="55")
    item["item_basic"]["url"] = ""
    products = product_parser.parse_products_json({"items": [item]})
    assert products[0].url == "https://shopee.vn/product/55/99"


def test_parse_products_json_normalizes_protocol_relative_url() -> None:
    item = _shopee_item()
    item["item_basic"]["url"] = "//shopee.vn/foo"
    products = product_parser.parse_products_json({"items": [item]})
    assert products[0].url == "https://shopee.vn/foo"


def test_parse_search_json_alias_returns_same_as_products() -> None:
    payload = {"items": [_shopee_item()]}
    a = product_parser.parse_products_json(payload)
    b = keyword_parser.parse_search_json(payload)
    assert [p.product_id for p in a] == [p.product_id for p in b]


# ----------------------------------------------------------- comments


def test_parse_comments_json_walks_payload() -> None:
    payload = {"data": {"ratings": [_shopee_rating(), _shopee_rating(cmtid="2")]}}
    out = comment_parser.parse_comments_json(payload, product_id="1001")
    assert len(out) == 2
    assert all(isinstance(c, Comment) for c in out)
    assert {c.comment_id for c in out} == {"9001", "2"}
    assert out[0].author == "khachhang01"
    assert out[0].rating == 5
    assert out[0].product_id == "1001"


def test_parse_comments_json_drops_out_of_range_rating() -> None:
    payload = {"items": [_shopee_rating(rating=7)]}
    out = comment_parser.parse_comments_json(payload, product_id="1001")
    assert len(out) == 1
    assert out[0].rating is None


def test_parse_comments_json_drops_missing_cmtid() -> None:
    payload = {"items": [{"comment": "x", "rating": 4}]}
    assert comment_parser.parse_comments_json(payload, product_id="x") == []


def test_parse_comments_json_uses_dict_productid_when_default_empty() -> None:
    """Default product_id arg may be empty; if dict has productid, parser uses it."""
    payload = {"items": [_shopee_rating()]}
    out = comment_parser.parse_comments_json(payload, product_id="")
    assert len(out) == 1
    assert out[0].product_id == "1001"


def test_parse_comments_json_drops_when_no_productid_anywhere() -> None:
    payload = {"items": [{"cmtid": "1", "comment": "x", "rating": 4}]}
    out = comment_parser.parse_comments_json(payload, product_id="")
    assert out == []


def test_parse_comments_json_dedups_by_cmtid() -> None:
    payload = {"items": [_shopee_rating(), _shopee_rating()]}
    out = comment_parser.parse_comments_json(payload, product_id="1001")
    assert len(out) == 1


def test_parse_comments_html_extracts_initial_state() -> None:
    html = (
        '<html><script>window.__INITIAL_STATE__ = {"data":{"ratings":['
        + '{"cmtid":"1","productid":"9","author_username":"a","rating":5,"comment":"ok","ctime":1}'
        + ']}};</script></html>'
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
    assert all(c.platform == Platform.SHOPEE for c in cats)
    assert all(c.level in (1, 2) for c in cats)  # only L1+L2 in seed


def test_menu_seed_has_balanced_levels() -> None:
    cats = menu_parser.parse_seed()
    by_level = {1: 0, 2: 0, 3: 0}
    for c in cats:
        by_level[c.level] += 1
    assert by_level[1] >= 4
    assert by_level[2] >= 4


def test_menu_seed_urls_are_absolute() -> None:
    cats = menu_parser.parse_seed()
    for c in cats:
        assert c.url.startswith("https://shopee.vn/")


# ----------------------------------------------------------- crawler


def test_shopee_crawler_registered() -> None:
    assert PlatformEnum.SHOPEE in get_registry()
    crawler = get_registry().get(PlatformEnum.SHOPEE)
    assert isinstance(crawler, ShopeeCrawler)
    assert crawler.platform == Platform.SHOPEE
    assert crawler.comment_supported is True


def test_crawler_fetch_menu_returns_seed() -> None:
    crawler = ShopeeCrawler()
    import asyncio

    cats = asyncio.run(crawler.fetch_menu())
    assert len(cats) >= 10
    assert all(c.platform == Platform.SHOPEE for c in cats)


def test_crawler_fetch_menu_level_2_filters() -> None:
    crawler = ShopeeCrawler()
    import asyncio

    cats = asyncio.run(crawler.fetch_menu(level=1))
    assert all(c.level == 1 for c in cats)


def test_crawler_describe() -> None:
    info = ShopeeCrawler().describe()
    assert info["platform"] == "shopee"
    assert info["comment_supported"] == "True"


@pytest.mark.parametrize("invalid_url", ["", None, "no-field"])
def test_shopee_crawler_parser_invalid_handled(invalid_url) -> None:
    """Sanity check: non-dict inputs to parsers are tolerated."""
    assert product_parser.parse_products_json(invalid_url) == []
    assert comment_parser.parse_comments_json(invalid_url) == []
