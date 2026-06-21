"""Tracking policies derived from urgency scores."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel

from .urgency import EventUrgencyScore


TrackingMode = Literal["urgent", "enhanced", "normal", "background", "paused"]


class TrackingPolicy(EventAlphaModel):
    """Tracking policy for one lifecycle event."""

    tracked_event_id: str
    tracking_mode: TrackingMode
    scan_interval_minutes: int
    analyze: bool = False
    reason: str


class TrackingPolicyService:
    """Build tracking policies from urgency scores."""

    def build_policies(self, scores: list[EventUrgencyScore]) -> list[TrackingPolicy]:
        """Return policies in the same order as the supplied scores."""
        return [self.build_policy(score) for score in scores]

    def build_policy(self, score: EventUrgencyScore) -> TrackingPolicy:
        """Return one tracking policy for a score."""
        if score.urgency_level == "urgent":
            return _policy(score, "urgent", 15, True)
        if score.urgency_level == "high":
            return _policy(score, "enhanced", 30, True)
        if score.urgency_level == "normal":
            return _policy(score, "normal", 60, True)
        if score.urgency_level == "background":
            return _policy(score, "background", 240, False)
        return _policy(score, "paused", 0, False)


def _policy(
    score: EventUrgencyScore,
    mode: TrackingMode,
    interval: int,
    analyze: bool,
) -> TrackingPolicy:
    reason_parts = [f"urgency_level={score.urgency_level}", f"score={score.urgency_score:.1f}"]
    if score.reasons:
        reason_parts.append(f"top_reason={score.reasons[0]}")
    if score.penalties:
        reason_parts.append(f"top_penalty={score.penalties[0]}")
    return TrackingPolicy(
        tracked_event_id=score.tracked_event_id,
        tracking_mode=mode,
        scan_interval_minutes=interval,
        analyze=analyze,
        reason="; ".join(reason_parts),
    )
