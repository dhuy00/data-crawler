"""Persistent storage helpers — CSV, SQLite, JSON Lines.

`Storage` is a single object the pipeline owns for the duration of a run.
It writes to:
- CSV (per-entity, per-run), one file per logical table.
- SQLite (one DB per output_dir), schema defined in plan.md §5.
- JSONL (raw, one file per entity, <output_dir>/raw/).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

import pandas as pd

from models import Category, Comment, Product
from .logger import logger


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    product_id TEXT NOT NULL,
    name TEXT NOT NULL,
    price REAL,
    original_price REAL,
    rating REAL,
    review_count INTEGER,
    sold_count INTEGER,
    category_path TEXT,
    url TEXT,
    crawled_at TEXT,
    UNIQUE(platform, product_id)
);
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    category_id TEXT NOT NULL,
    parent_id TEXT,
    name TEXT NOT NULL,
    level INTEGER NOT NULL,
    url TEXT,
    UNIQUE(platform, category_id)
);
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    product_id TEXT NOT NULL,
    comment_id TEXT NOT NULL,
    author TEXT,
    rating INTEGER,
    content TEXT,
    created_at TEXT,
    crawled_at TEXT,
    UNIQUE(platform, comment_id)
);
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    mode TEXT NOT NULL,
    platforms TEXT NOT NULL,
    category TEXT,
    keywords TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    product_count INTEGER DEFAULT 0,
    comment_count INTEGER DEFAULT 0,
    output_dir TEXT
);
CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform);
CREATE INDEX IF NOT EXISTS idx_comments_product ON comments(platform, product_id);
"""


class Storage:
    """File + DB writer for one pipeline run.

    The instance is cheap: it just holds paths and a sqlite3 connection cache.
    All public methods are sync so callers can `await` them from async pipelines.
    """

    def __init__(self, output_dir: str | Path, run_id: str | None = None):
        self.output_dir = Path(output_dir)
        self.run_id = run_id or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        (self.output_dir / "raw").mkdir(parents=True, exist_ok=True)
        self.db_path = self.output_dir / "crawler.db"
        self._init_schema()

    # ------------------------------------------------------------------ paths

    def csv_path(self, name: str) -> Path:
        return self.output_dir / f"{name}_{self.run_id}.csv"

    def jsonl_path(self, name: str) -> Path:
        return self.output_dir / "raw" / f"{name}_{self.run_id}.jsonl"

    # ----------------------------------------------------------------- sqlite

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path))
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA_SQL)

    # --------------------------------------------------------------- products

    def save_products(
        self,
        products: Iterable[Product],
        *, file_tag: str = "products",
    ) -> int:
        items = list(products)
        if not items:
            return 0
        df = pd.DataFrame([_product_to_row(p) for p in items])
        df.to_csv(self.csv_path(file_tag), index=False, encoding="utf-8")
        with self.jsonl_path(file_tag).open("a", encoding="utf-8") as fh:
            for p in items:
                fh.write(p.model_dump_json() + "\n")
        with self._conn() as conn:
            for row in df.to_dict("records"):
                conn.execute(
                    "INSERT OR IGNORE INTO products ("
                    "platform, product_id, name, price, original_price, "
                    "rating, review_count, sold_count, category_path, url, crawled_at"
                    ") VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        row["platform"],
                        row["product_id"],
                        row["name"],
                        row["price"],
                        row["original_price"],
                        row["rating"],
                        row["review_count"],
                        row["sold_count"],
                        row["category_path"],
                        row["url"],
                        row["crawled_at"],
                    ),
                )
        logger.info(f"Saved {len(items)} products -> {self.csv_path(file_tag).name}")
        return len(items)

    # -------------------------------------------------------------- categories

    def save_categories(
        self,
        categories: Iterable[Category],
        *, file_tag: str = "menu",
    ) -> int:
        items = list(categories)
        if not items:
            return 0
        df = pd.DataFrame([_category_to_row(c) for c in items])
        df.to_csv(self.csv_path(file_tag), index=False, encoding="utf-8")
        with self.jsonl_path(file_tag).open("a", encoding="utf-8") as fh:
            for c in items:
                fh.write(c.model_dump_json() + "\n")
        with self._conn() as conn:
            for row in df.to_dict("records"):
                conn.execute(
                    "INSERT OR IGNORE INTO categories ("
                    "platform, category_id, parent_id, name, level, url"
                    ") VALUES (?,?,?,?,?,?)",
                    (
                        row["platform"],
                        row["category_id"],
                        row["parent_id"],
                        row["name"],
                        row["level"],
                        row["url"],
                    ),
                )
        logger.info(f"Saved {len(items)} categories -> {self.csv_path(file_tag).name}")
        return len(items)

    # ---------------------------------------------------------------- comments

    def save_comments(
        self,
        comments: Iterable[Comment],
        *, file_tag: str = "comments",
    ) -> int:
        items = list(comments)
        if not items:
            return 0
        df = pd.DataFrame([_comment_to_row(c) for c in items])
        df.to_csv(self.csv_path(file_tag), index=False, encoding="utf-8")
        with self.jsonl_path(file_tag).open("a", encoding="utf-8") as fh:
            for c in items:
                fh.write(c.model_dump_json() + "\n")
        with self._conn() as conn:
            for row in df.to_dict("records"):
                conn.execute(
                    "INSERT OR IGNORE INTO comments ("
                    "platform, product_id, comment_id, author, rating, "
                    "content, created_at, crawled_at"
                    ") VALUES (?,?,?,?,?,?,?,?)",
                    (
                        row["platform"],
                        row["product_id"],
                        row["comment_id"],
                        row["author"],
                        row["rating"],
                        row["content"],
                        row["created_at"],
                        row["crawled_at"],
                    ),
                )
        logger.info(f"Saved {len(items)} comments -> {self.csv_path(file_tag).name}")
        return len(items)

    # ------------------------------------------------------------------ runs

    def record_run(self, run_row: dict[str, Any]) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO runs ("
                "run_id, mode, platforms, category, keywords, started_at, "
                "finished_at, product_count, comment_count, output_dir"
                ") VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    run_row["run_id"],
                    run_row["mode"],
                    ",".join(run_row.get("platforms", [])),
                    run_row.get("category"),
                    ",".join(run_row.get("keywords", [])),
                    run_row.get("started_at"),
                    run_row.get("finished_at"),
                    run_row.get("product_count", 0),
                    run_row.get("comment_count", 0),
                    run_row.get("output_dir"),
                ),
            )


# ----------------------------------------------------------------- helpers


def _product_to_row(p: Product) -> dict[str, Any]:
    d = p.model_dump()
    # Pydantic serializes datetime to str in model_dump_json but keeps datetime
    # in model_dump; convert here so CSV/DB get consistent ISO strings.
    if isinstance(d.get("crawled_at"), datetime):
        d["crawled_at"] = d["crawled_at"].isoformat()
    if isinstance(d.get("platform"), object) and not isinstance(d.get("platform"), str):
        d["platform"] = str(d["platform"])
    return d


def _category_to_row(c: Category) -> dict[str, Any]:
    d = c.model_dump()
    if not isinstance(d.get("platform"), str):
        d["platform"] = str(d["platform"])
    return d


def _comment_to_row(c: Comment) -> dict[str, Any]:
    d = c.model_dump()
    if isinstance(d.get("crawled_at"), datetime):
        d["crawled_at"] = d["crawled_at"].isoformat()
    if not isinstance(d.get("platform"), str):
        d["platform"] = str(d["platform"])
    return d


def write_jsonl(path: Path, items: Iterable[Any]) -> None:
    """Append items as JSON Lines to `path` (one JSON object per line)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for item in items:
            if hasattr(item, "model_dump_json"):
                fh.write(item.model_dump_json() + "\n")
            else:
                fh.write(json.dumps(item, default=str) + "\n")
