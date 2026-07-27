"""Pipelines package for Tiki crawling framework."""
from pipelines.full_pipeline import full_pipeline
from pipelines.keyword_pipeline import keyword_pipeline
from pipelines.menu_pipeline import menu_pipeline
from pipelines.menu_products_pipeline import menu_products_pipeline
from pipelines.products_from_menu_pipeline import products_from_menu_pipeline
from pipelines.comments_from_products_pipeline import comments_from_products_pipeline

__all__ = [
    "full_pipeline",
    "keyword_pipeline",
    "menu_pipeline",
    "menu_products_pipeline",
    "products_from_menu_pipeline",
    "comments_from_products_pipeline",
]
