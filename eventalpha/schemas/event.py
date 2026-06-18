"""Event input and extraction schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from .base import EventAlphaModel, EventType, TimestampedModel, new_id, utc_now


SourceType = Literal[
    "official",
    "mainstream_media",
    "social_media",
    "research_report",
    "unknown",
]
EventStatus = Literal["announced", "confirmed", "rumor", "draft", "happened", "unknown"]


class RawNews(TimestampedModel):
    """Original event text and source metadata."""

    raw_id: str = Field(default_factory=lambda: new_id("RAW"))
    title: str = ""
    source: str = "unknown"
    source_type: SourceType = "unknown"
    publish_time: datetime = Field(default_factory=utc_now)
    url: str | None = None
    language: str = "zh"
    raw_text: str
    metadata: dict[str, str] = Field(default_factory=dict)


class StructuredEvent(TimestampedModel):
    """Normalized event extracted from raw text."""

    event_id: str = Field(default_factory=lambda: new_id("EVT"))
    raw_id: str | None = None
    event_type: EventType = "unknown"
    event_title: str = ""
    summary: str = ""
    entities: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    event_time: datetime | None = None
    status: EventStatus = "unknown"
    affected_industries: list[str] = Field(default_factory=list)
    affected_assets_hint: list[str] = Field(default_factory=list)
    novelty_score: float = 0.5
