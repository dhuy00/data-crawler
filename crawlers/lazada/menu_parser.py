"""Parse Lazada menu seed into `Category` instances."""

from __future__ import annotations

from models import Category, Platform

from .menu_seed import LAZADA_MENU_SEED


def parse_seed(seed: list[tuple] | None = None) -> list[Category]:
    seed = seed if seed is not None else LAZADA_MENU_SEED
    out: list[Category] = []
    for level, slug, name, parent, url in seed:
        out.append(
            Category(
                platform=Platform.LAZADA,
                category_id=str(slug),
                name=str(name),
                parent_id=str(parent) if parent else None,
                level=int(level),
                url=str(url),
            )
        )
    return out
