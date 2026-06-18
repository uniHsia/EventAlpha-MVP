"""Rule update schemas."""

from __future__ import annotations

from pydantic import Field

from .base import TimestampedModel, new_id


class RuleUpdate(TimestampedModel):
    """A lightweight rule weight update produced after review."""

    update_id: str = Field(default_factory=lambda: new_id("RULE_UPD"))
    rule_id: str
    prediction_id: str
    review_id: str
    summary_id: str | None = None
    old_weight: float = 0.5
    new_weight: float = 0.5
    reason: str = ""
    update_action: str = "unchanged"
