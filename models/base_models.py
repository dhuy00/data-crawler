"""Core Pydantic models shared across crawlers, services, and storage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .platform import Platform


def _utcnow() -> datetime:
    """Current UTC time, used as default for `crawled_at`."""
    return datetime.now(timezone.utc)


class Category(BaseModel):
    """One node in a platform's category tree (up to 3 levels deep)."""

    model_config = ConfigDict(frozen=False, use_enum_values=False)

    platform: Platform
    category_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    parent_id: Optional[str] = None
    level: int = Field(ge=1, le=3)
    url: str = Field(min_length=1)

    @field_validator("url")
    @classmethod
    def _strip_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"Invalid URL: {v!r}")
        return v


class Product(BaseModel):
    """A normalized product record across platforms."""

    model_config = ConfigDict(use_enum_values=False)

    platform: Platform
    product_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    price: Optional[float] = Field(default=None, ge=0)
    original_price: Optional[float] = Field(default=None, ge=0)
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    review_count: Optional[int] = Field(default=None, ge=0)
    sold_count: Optional[int] = Field(default=None, ge=0)
    category_path: str = ""
    url: str = ""
    crawled_at: datetime = Field(default_factory=_utcnow)

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        if not v:
            return v
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError(f"Invalid URL: {v!r}")
        return v

    @field_validator("name")
    @classmethod
    def _normalize_name(cls, v: str) -> str:
        return " ".join(v.split())


class Comment(BaseModel):
    """A single review/comment for a product."""

    model_config = ConfigDict(use_enum_values=False)

    platform: Platform
    product_id: str = Field(min_length=1)
    comment_id: str = Field(min_length=1)
    author: str = ""
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    content: str = ""
    created_at: str = ""
    crawled_at: datetime = Field(default_factory=_utcnow)


class Run(BaseModel):
    """Metadata for a single pipeline execution."""

    run_id: str
    mode: str
    platforms: list[Platform]
    category: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=_utcnow)
    finished_at: Optional[datetime] = None
    product_count: int = 0
    comment_count: int = 0
    output_dir: str = ""
