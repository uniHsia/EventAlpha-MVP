"""Credibility verification schemas."""

from __future__ import annotations

from pydantic import Field

from .base import SourceClassification, TimestampedModel, VerificationStatus, new_id


class EventVerification(TimestampedModel):
    """Credibility assessment for a structured event."""

    verification_id: str = Field(default_factory=lambda: new_id("VER"))
    event_id: str
    credibility_score: float = 0.5
    verification_status: VerificationStatus = "needs_confirmation"
    source_classification: SourceClassification = "unknown_source"
    content_contains_official_claim: bool = False
    evidence: list[dict[str, str]] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
