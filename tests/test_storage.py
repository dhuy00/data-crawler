"""Tests for core/storage.py — CSV + SQLite + JSONL writers."""

from __future__ import annotations

import sqlite3

from models import Category, Comment, Platform, Product

from core.storage import Storage


def _sample_product(pid: str = "P1") -> Product:
    return Product(
        platform=Platform.SHOPEE,
        product_id=pid,
        name="iPhone 15",
        price=20_000_000,
        rating=4.5,
        review_count=10,
        url="https://shopee.vn/product/" + pid,
    )


def _sample_category(cid: str = "C1") -> Category:
    return Category(
        platform=Platform.TIKI,
        category_id=cid,
        name="Điện tử",
        level=1,
        url="https://tiki.vn/" + cid,
    )


def _sample_comment(cid: str = "CM1") -> Comment:
    return Comment(
        platform=Platform.SENDO,
        product_id="P1",
        comment_id=cid,
        content="good",
        rating=5,
    )


def test_save_products_writes_csv_jsonl_and_db(tmp_output_dir):
    storage = Storage(tmp_output_dir, run_id="r1")

    n = storage.save_products([_sample_product("P1"), _sample_product("P2")])

    assert n == 2
    csv_path = storage.csv_path("products")
    jsonl_path = storage.jsonl_path("products")
    assert csv_path.exists()
    assert jsonl_path.exists()

    with sqlite3.connect(storage.db_path) as conn:
        rows = conn.execute("SELECT platform, product_id FROM products").fetchall()
    assert sorted(rows) == [("shopee", "P1"), ("shopee", "P2")]


def test_save_products_empty_is_noop(tmp_output_dir):
    storage = Storage(tmp_output_dir, run_id="r1")
    assert storage.save_products([]) == 0
    assert not storage.csv_path("products").exists()


def test_save_products_idempotent(tmp_output_dir):
    """Saving the same product twice must not crash and must not duplicate."""
    storage = Storage(tmp_output_dir, run_id="r1")
    storage.save_products([_sample_product("P1")])
    storage.save_products([_sample_product("P1")])

    with sqlite3.connect(storage.db_path) as conn:
        rows = conn.execute("SELECT COUNT(*) FROM products").fetchall()
    assert rows[0][0] == 1


def test_save_categories_and_comments(tmp_output_dir):
    storage = Storage(tmp_output_dir, run_id="r1")

    assert storage.save_categories([_sample_category("C1")]) == 1
    assert storage.save_comments([_sample_comment("CM1")]) == 1

    with sqlite3.connect(storage.db_path) as conn:
        cat = conn.execute("SELECT name FROM categories WHERE category_id='C1'").fetchall()
        cmt = conn.execute("SELECT content FROM comments WHERE comment_id='CM1'").fetchall()
    assert cat[0][0] == "Điện tử"
    assert cmt[0][0] == "good"


def test_record_run(tmp_output_dir):
    storage = Storage(tmp_output_dir, run_id="r1")
    storage.record_run({
        "run_id": "r1",
        "mode": "full",
        "platforms": ["shopee", "tiki"],
        "category": "dien-thoai",
        "keywords": [],
        "started_at": "2026-07-27T10:00:00",
        "finished_at": "2026-07-27T10:05:00",
        "product_count": 12,
        "comment_count": 50,
        "output_dir": str(tmp_output_dir),
    })
    with sqlite3.connect(storage.db_path) as conn:
        row = conn.execute("SELECT mode, product_count FROM runs").fetchone()
    assert row == ("full", 12)
