"""Schemas for news source collection."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime

from pydantic import Field, model_validator

from eventalpha.schemas.base import EventAlphaModel, utc_now


def make_news_id(
    title: str,
    source: str,
    url: str | None = None,
) -> str:
    """Generate a stable news identifier from URL or source/title."""
    key = _normalize_url(url) if url else ""
    if not key:
        key = f"{_normalize_text(source)}::{_normalize_text(title)}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"NEWS_{digest}"


class NewsItem(EventAlphaModel):
    """Standardized candidate news item from an external source."""

    news_id: str = ""
    title: str
    summary: str | None = None
    url: str | None = None
    source: str
    source_type: str = "unknown"
    published_at: datetime | None = None
    language: str | None = None
    country: str | None = None
    raw_text: str | None = None
    tags: list[str] = Field(default_factory=list)
    fetched_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def fill_news_id(self) -> "NewsItem":
        """Create a stable ID when providers do not supply one."""
        if not self.news_id:
            self.news_id = make_news_id(
                title=self.title,
                source=self.source,
                url=self.url,
            )
        return self


class NewsFetchResult(EventAlphaModel):
    """Result from one news provider fetch."""

    source_name: str
    fetched_at: datetime = Field(default_factory=utc_now)
    items: list[NewsItem] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def _normalize_url(url: str | None) -> str:
    if not url:
        return ""
    return str(url).strip().rstrip("/").casefold()


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()
