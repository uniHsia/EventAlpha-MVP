"""Event impact scoring schemas."""

from __future__ import annotations

from pydantic import Field

from .base import EventLevel, TimestampedModel, new_id


class ImpactScore(TimestampedModel):
    """Market impact score and handling level."""

    score_id: str = Field(default_factory=lambda: new_id("SCORE"))
    event_id: str
    impact_score: int = 0
    event_level: EventLevel = "D"
    trigger_alert: bool = False
    tracking_mode: str = "none"
    score_breakdown: dict[str, int] = Field(default_factory=dict)
