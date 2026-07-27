"""Tests for models/base_models.py and models/platform.py."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from models import Category, Comment, Platform, Product


class TestPlatform:
    def test_values_are_lowercase(self):
        for p in Platform:
            assert p.value == p.value.lower()

    def test_parse_accepts_enum(self):
        assert Platform.parse(Platform.TIKI) is Platform.TIKI

    def test_parse_accepts_string(self):
        assert Platform.parse("shopee") is Platform.SHOPEE

    def test_parse_rejects_unknown(self):
        with pytest.raises(ValueError):
            Platform.parse("ebay")

    def test_comment_supported(self):
        assert Platform.TIKI.comment_supported is True
        assert Platform.LAZADA.comment_supported is False


class TestCategory:
    def test_valid_category(self):
        c = Category(
            platform=Platform.TIKI,
            category_id="1",
            name="Điện tử",
            level=1,
            url="https://tiki.vn/dien-tu",
        )
        assert c.level == 1
        assert c.parent_id is None

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError):
            Category(
                platform=Platform.TIKI,
                category_id="1",
                name="X",
                level=1,
                url="not-a-url",
            )

    def test_level_bounds(self):
        with pytest.raises(ValidationError):
            Category(
                platform=Platform.TIKI,
                category_id="1",
                name="X",
                level=4,
                url="https://tiki.vn/x",
            )


class TestProduct:
    def test_valid_product(self):
        p = Product(
            platform=Platform.SHOPEE,
            product_id="P1",
            name="  iPhone 15  Pro  ",
            price=20_000_000,
        )
        assert p.name == "iPhone 15 Pro"  # whitespace collapsed

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            Product(
                platform=Platform.SHOPEE,
                product_id="P1",
                name="x",
                price=-1,
            )

    def test_rating_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            Product(
                platform=Platform.SHOPEE,
                product_id="P1",
                name="x",
                rating=6,
            )


class TestComment:
    def test_valid_comment(self):
        c = Comment(
            platform=Platform.SENDO,
            product_id="P1",
            comment_id="C1",
            content="ok",
            rating=5,
        )
        assert c.rating == 5
        assert c.crawled_at is not None

    def test_rating_required_in_1_to_5(self):
        with pytest.raises(ValidationError):
            Comment(
                platform=Platform.SENDO,
                product_id="P1",
                comment_id="C1",
                rating=10,
            )
