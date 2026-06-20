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


def make_cluster_id(items: list["NewsItem"]) -> str:
    """Generate a stable cluster identifier from sorted news IDs."""
    key = "::".join(sorted(item.news_id for item in items))
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"CLUSTER_{digest}"


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


class EventCluster(EventAlphaModel):
    """Lightweight event cluster built from related news items."""

    cluster_id: str = ""
    canonical_title: str
    canonical_summary: str | None = None
    items: list[NewsItem]
    sources: list[str] = Field(default_factory=list)
    source_count: int = 0
    mainstream_source_count: int = 0
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    dominant_keywords: list[str] = Field(default_factory=list)
    candidate_event_type: str | None = None
    verification_status: str = "single_source"
    confidence: float = 0.0
    debug_reasons: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_cluster_fields(self) -> "EventCluster":
        """Fill derived cluster fields from items."""
        if not self.cluster_id:
            self.cluster_id = make_cluster_id(self.items)
        if not self.sources:
            self.sources = _unique(item.source for item in self.items)
        self.source_count = len(set(self.sources))
        if self.first_seen_at is None or self.last_seen_at is None:
            seen_at = [
                item.published_at or item.fetched_at
                for item in self.items
                if item.published_at or item.fetched_at
            ]
            if seen_at:
                self.first_seen_at = self.first_seen_at or min(seen_at)
                self.last_seen_at = self.last_seen_at or max(seen_at)
        return self


def _normalize_url(url: str | None) -> str:
    if not url:
        return ""
    return str(url).strip().rstrip("/").casefold()


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()


def _unique(values) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results
