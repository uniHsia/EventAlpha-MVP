"""Schemas for offline daily briefing reports."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import Field

from eventalpha.news import TrackedEvent
from eventalpha.schemas.base import EventAlphaModel, RISK_DISCLAIMER, new_id, utc_now


class BriefingItem(EventAlphaModel):
    """One compact item inside a briefing section."""

    item_id: str
    title: str
    item_type: str
    priority: str = "normal"
    summary: str | None = None
    details: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    verification_indicators: list[str] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BriefingSection(EventAlphaModel):
    """A named section in the daily briefing."""

    section_id: str
    title: str
    items: list[BriefingItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class DailyBriefing(EventAlphaModel):
    """A deterministic offline briefing for one local analysis date."""

    briefing_id: str = Field(default_factory=lambda: new_id("BRIEF"))
    briefing_date: date
    generated_at: datetime = Field(default_factory=utc_now)
    title: str
    sections: list[BriefingSection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    risk_disclaimer: str = RISK_DISCLAIMER


class BriefingCollectedData(EventAlphaModel):
    """Read-only local data used to build a briefing."""

    briefing_date: date
    active_events: list[TrackedEvent] = Field(default_factory=list)
    urgency_scores: list[Any] = Field(default_factory=list)
    scheduler_jobs: list[Any] = Field(default_factory=list)
    recent_runs: list[Any] = Field(default_factory=list)
    tracking_policies: list[Any] = Field(default_factory=list)
    event_cards: list[dict[str, Any]] = Field(default_factory=list)
    review_results: list[dict[str, Any]] = Field(default_factory=list)
    review_summaries: list[dict[str, Any]] = Field(default_factory=list)
    rule_updates: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
