"""User-facing card schemas."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from .base import EventLevel, RISK_DISCLAIMER, TimestampedModel, new_id


class EventCard(TimestampedModel):
    """Research card for one event."""

    card_id: str = Field(default_factory=lambda: new_id("CARD"))
    event_id: str
    event_title: str
    event_level: EventLevel = "D"
    credibility_score: float = 0.5
    one_sentence: str = ""
    what_happened: str = ""
    sources: list[str] = Field(default_factory=list)
    causal_chain_summary: list[str] = Field(default_factory=list)
    possible_impacts: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    verification_indicators: list[str] = Field(default_factory=list)
    history_validation_summary: dict[str, Any] | None = None
    risk_disclaimer: str = RISK_DISCLAIMER
