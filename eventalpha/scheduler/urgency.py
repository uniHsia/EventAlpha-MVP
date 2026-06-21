"""Urgency score schemas for scheduler tracking."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from eventalpha.schemas.base import EventAlphaModel


UrgencyLevel = Literal["urgent", "high", "normal", "background", "ignore"]


class EventUrgencyScore(EventAlphaModel):
    """Priority score for one tracked lifecycle event."""

    tracked_event_id: str
    title: str
    urgency_score: float
    urgency_level: UrgencyLevel = "normal"
    reasons: list[str] = Field(default_factory=list)
    penalties: list[str] = Field(default_factory=list)

    @field_validator("urgency_score")
    @classmethod
    def clamp_score(cls, value: float) -> float:
        """Clamp urgency score to 0..100."""
        return round(min(max(float(value), 0.0), 100.0), 4)

    @model_validator(mode="after")
    def fill_level(self) -> "EventUrgencyScore":
        """Fill urgency level from score when the caller leaves the default."""
        if self.urgency_level == "normal":
            self.urgency_level = urgency_level_for_score(self.urgency_score)
        return self


def urgency_level_for_score(score: float) -> UrgencyLevel:
    """Map a numeric urgency score to a level."""
    if score >= 75:
        return "urgent"
    if score >= 55:
        return "high"
    if score >= 30:
        return "normal"
    if score >= 10:
        return "background"
    return "ignore"
