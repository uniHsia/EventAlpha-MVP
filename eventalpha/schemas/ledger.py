"""Prediction ledger schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .base import Direction, EventLevel, EventType, Horizon, TimestampedModel, new_id, utc_now


LedgerStatus = Literal["active", "reviewed_partial", "reviewed_final", "archived"]


class PredictedAsset(TimestampedModel):
    """A market object tracked for later review."""

    asset_name: str
    asset_type: str = "theme"
    direction: Direction = "up"
    time_window: Horizon = "T+3"
    asset_confidence: float = 0.5
    chain_confidence: float = 0.5
    anti_spurious_adjusted_confidence: float = 0.5
    final_confidence: float = 0.25
    confidence: float = 0.25
    benchmark: str = "沪深300"

    @model_validator(mode="after")
    def sync_confidence_alias(self) -> "PredictedAsset":
        """Keep the legacy confidence field aligned with final_confidence."""
        computed = round(self.asset_confidence * self.anti_spurious_adjusted_confidence, 4)
        if self.final_confidence == 0.25 and self.confidence != 0.25:
            self.final_confidence = self.confidence
        elif self.final_confidence == 0.25 and computed != 0.25:
            self.final_confidence = computed
        self.confidence = self.final_confidence
        return self


class PredictionLedgerEntry(TimestampedModel):
    """Structured prediction snapshot written before publication."""

    prediction_id: str = Field(default_factory=lambda: new_id("PRED"))
    event_id: str
    event_title: str
    event_type: EventType = "unknown"
    publish_time: datetime = Field(default_factory=utc_now)
    event_level: EventLevel = "D"
    credibility_score: float = 0.5
    impact_score: int = 0
    causal_chain_ids: list[str] = Field(default_factory=list)
    predicted_assets: list[PredictedAsset] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    review_schedule: list[Horizon] = Field(default_factory=lambda: ["T+1", "T+3", "T+7"])
    status: LedgerStatus = "active"
