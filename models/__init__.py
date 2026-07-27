"""Models package — Pydantic data classes shared across crawlers and storage."""

from .base_models import Category, Comment, Product, Run
from .platform import Platform

__all__ = ["Platform", "Category", "Product", "Comment", "Run"]
