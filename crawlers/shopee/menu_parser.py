"""Parse the Shopee menu seed into `Category` instances.

Shopee exposes no public category-tree endpoint at this time, so we
ship a curated seed. The same `parse_seed(...)` shape as Tiki keeps
the rest of the pipeline platform-agnostic.
"""

from __future__ import annotations

from models import Category, Platform

from .menu_seed import SHOPEE_MENU_SEED


def parse_seed(seed: list[tuple] | None = None) -> list[Category]:
    """Convert raw seed tuples to `Category` objects."""
    seed = seed if seed is not None else SHOPEE_MENU_SEED
    out: list[Category] = []
    for level, slug, name, parent, url in seed:
        out.append(
            Category(
                platform=Platform.SHOPEE,
                category_id=str(slug),
                name=str(name),
                parent_id=str(parent) if parent else None,
                level=int(level),
                url=str(url),
            )
        )
    return out
