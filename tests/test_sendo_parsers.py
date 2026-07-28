"""Unit tests for Sendo parsers and crawler registration."""

from __future__ import annotations

import pytest

from crawlers.sendo import comment_parser, keyword_parser, menu_parser, product_parser
from crawlers.sendo.sendo_crawler import SendoCrawler
from models import Category, Comment, Platform, Product
from models.platform import Platform as PlatformEnum
from services.platform_registry import get_registry


# -------------------------------------------------------------- helpers

def _sendo_item(
    id: str = "111222",
    name: str = "Áo thun nam",
    final_price: float = 99_000.0,
    market_price: float = 199_000.0,
    rating: float = 4.5,
    review_count: int = 12,
    sold: int = 250,
) -> dict:
    return {
        "id": id,
        "name": name,
        "final_price": final_price,
        "market_price": market_price,
        "price": final_price,
        "rating": rating,
        "review_count": review_count,
        "sold_quantity": sold,
        "category_name": "Thời trang nam",
        "url": f"https://www.sendo.vn/product/{id}.htm",
    }


def _sendo_review(
    rid: str = "fb_001",
    pid: str = "111222",
    author: str = "khachb",
    rating: int = 4,
    content: str = "Vải đẹp, mặc thoải mái.",
    created_at: str = "2026-07-10",
) -> dict:
    return {
        "id": rid,
        "product_id": pid,
        "customerName": author,
        "rating": rating,
        "content": content,
        "createdAt": created_at,
    }


# ----------------------------------------------------------- products


def test_parse_products_json_data_wrapper() -> None:
    payload = {"data": [_sendo_item()]}
    out = product_parser.parse_products_json(payload)
    assert len(out) == 1
    p = out[0]
    assert isinstance(p, Product)
    assert p.platform == Platform.SENDO
    assert p.product_id == "111222"
    assert p.name == "Áo thun nam"
    assert p.price == 99_000.0
    assert p.original_price == 199_000.0
    assert p.rating == pytest.approx(4.5)
    assert p.review_count == 12
    assert p.sold_count == 250
    assert p.category_path == "Thời trang nam"
    assert p.url == "https://www.sendo.vn/product/111222.htm"


def test_parse_products_json_result_inner_data_wrapper() -> None:
    payload = {"result": {"data": [_sendo_item(id="1"), _sendo_item(id="2")]}}
    out = product_parser.parse_products_json(payload)
    assert {p.product_id for p in out} == {"1", "2"}


def test_parse_products_json_bare_list() -> None:
    out = product_parser.parse_products_json([_sendo_item(id="9")])
    assert out[0].product_id == "9"


def test_parse_products_json_dedups() -> None:
    out = product_parser.parse_products_json(
        {"data": [_sendo_item(id="1"), _sendo_item(id="1")]}
    )
    assert len(out) == 1


def test_parse_products_json_skips_missing_id() -> None:
    assert product_parser.parse_products_json({"data": [{"name": "x"}]}) == []


def test_parse_products_json_skips_missing_name() -> None:
    assert product_parser.parse_products_json({"data": [{"id": "1"}]}) == []


def test_parse_products_json_prices_when_only_price_present() -> None:
    item = _sendo_item()
    item.pop("final_price")
    item.pop("market_price")
    out = product_parser.parse_products_json({"data": [item]})
    assert out[0].price == 99_000.0
    assert out[0].original_price is None


def test_parse_products_json_invalid_price_returns_none() -> None:
    item = _sendo_item()
    item["final_price"] = "NaN"
    item["market_price"] = ""
    out = product_parser.parse_products_json({"data": [item]})
    assert len(out) == 1
    assert out[0].price is None
    assert out[0].original_price is None


def test_parse_products_json_url_fallback() -> None:
    item = _sendo_item(id="42")
    item["url"] = ""
    out = product_parser.parse_products_json({"data": [item]})
    assert out[0].url == "https://www.sendo.vn/product/42.htm"


def test_parse_products_json_url_protocol_relative() -> None:
    item = _sendo_item()
    item["url"] = "//foo.com/x"
    out = product_parser.parse_products_json({"data": [item]})
    assert out[0].url == "https://foo.com/x"


def test_parse_products_json_category_fallback_to_id() -> None:
    item = _sendo_item(id="1")
    item.pop("category_name")
    out = product_parser.parse_products_json({"data": [item]})
    # No `category_id` provided in fixture, should yield empty string
    assert out[0].category_path == ""


def test_parse_products_json_garbage_inputs() -> None:
    assert product_parser.parse_products_json(None) == []
    assert product_parser.parse_products_json(123) == []
    assert product_parser.parse_products_json("hi") == []


def test_parse_search_json_alias_matches_products() -> None:
    a = product_parser.parse_products_json({"data": [_sendo_item()]})
    b = keyword_parser.parse_search_json({"data": [_sendo_item()]})
    assert [p.product_id for p in a] == [p.product_id for p in b]


# ----------------------------------------------------------- comments


def test_parse_comments_json_walks_feedBacks() -> None:
    payload = {"data": {"feedBacks": [_sendo_review(), _sendo_review(rid="r2")]}}
    out = comment_parser.parse_comments_json(payload, product_id="111222")
    assert len(out) == 2
    assert all(isinstance(c, Comment) for c in out)
    assert {c.comment_id for c in out} == {"fb_001", "r2"}
    assert out[0].author == "khachb"
    assert out[0].rating == 4
    assert out[0].product_id == "111222"
    assert out[0].content == "Vải đẹp, mặc thoải mái."


def test_parse_comments_json_out_of_range_rating() -> None:
    payload = {"data": [_sendo_review(rating=10)]}
    out = comment_parser.parse_comments_json(payload, product_id="1")
    assert out[0].rating is None


def test_parse_comments_json_drops_missing_id() -> None:
    payload = {"data": [{"content": "ok", "rating": 5, "product_id": "1"}]}
    assert comment_parser.parse_comments_json(payload, product_id="1") == []


def test_parse_comments_json_drops_when_no_productid() -> None:
    payload = {"data": [{"id": "x", "content": "y", "rating": 4}]}
    assert comment_parser.parse_comments_json(payload, product_id="") == []


def test_parse_comments_json_uses_default_productid() -> None:
    payload = {"data": [{"id": "1", "content": "ok", "rating": 5}]}
    out = comment_parser.parse_comments_json(payload, product_id="99")
    assert out[0].product_id == "99"


def test_parse_comments_json_dedups_by_id() -> None:
    payload = {"data": [_sendo_review(), _sendo_review()]}
    out = comment_parser.parse_comments_json(payload, product_id="1")
    assert len(out) == 1


def test_parse_comments_html_extracts_initial_state() -> None:
    html = (
        '<html><script>window.__INITIAL_STATE__ = {"items":['
        + '{"id":"1","product_id":"9","customerName":"a","rating":5,'
        + '"content":"ok","createdAt":"2026"}'
        + ']};</script></html>'
    )
    out = comment_parser.parse_comments_html(html, product_id="9")
    assert len(out) == 1
    assert out[0].product_id == "9"


# ----------------------------------------------------------- menu


def test_menu_seed_yields_categories() -> None:
    cats = menu_parser.parse_seed()
    assert len(cats) >= 10
    assert all(isinstance(c, Category) for c in cats)
    assert all(c.platform == Platform.SENDO for c in cats)


def test_menu_seed_urls_are_sendo() -> None:
    for c in menu_parser.parse_seed():
        assert c.url.startswith("https://www.sendo.vn/")


# ----------------------------------------------------------- crawler


def test_sendo_crawler_registered() -> None:
    assert PlatformEnum.SENDO in get_registry()
    crawler = get_registry().get(PlatformEnum.SENDO)
    assert isinstance(crawler, SendoCrawler)
    assert crawler.platform == Platform.SENDO


def test_crawler_fetch_menu_seed() -> None:
    import asyncio
    cats = asyncio.run(SendoCrawler().fetch_menu())
    assert len(cats) >= 10
    assert all(c.platform == Platform.SENDO for c in cats)


def test_crawler_fetch_menu_level_2() -> None:
    import asyncio
    cats = asyncio.run(SendoCrawler().fetch_menu(level=2))
    assert all(c.level <= 2 for c in cats)


def test_crawler_describe() -> None:
    info = SendoCrawler().describe()
    assert info["platform"] == "sendo"
    assert info["comment_supported"] == "True"
