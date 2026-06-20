"""Schemas for the historical case store."""

from __future__ import annotations

import hashlib
import re
from datetime import date

from pydantic import Field, model_validator

from eventalpha.schemas.base import EventAlphaModel


def make_historical_case_id(
    title: str,
    event_type: str,
    event_date: date | None = None,
) -> str:
    """Generate a stable historical case ID."""
    key = f"{_normalize_text(event_type)}::{_normalize_text(title)}::{event_date.isoformat() if event_date else ''}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"HCASE_{digest}"


class HistoricalOutcome(EventAlphaModel):
    """Illustrative market outcome attached to a historical case."""

    benchmark: str | None = None
    asset_returns: dict[str, dict[str, float]] = Field(default_factory=dict)
    market_reaction_summary: str | None = None
    time_windows: list[str] = Field(default_factory=lambda: ["T+1", "T+3", "T+7"])
    outcome_quality: str = "manual_seed"


class HistoricalCausalAssessment(EventAlphaModel):
    """Manual assessment of whether the expected causal logic worked."""

    expected_direction: str | None = None
    realized_direction: str | None = None
    causal_validity: str = "unknown"
    what_worked: list[str] = Field(default_factory=list)
    what_failed: list[str] = Field(default_factory=list)
    lessons: list[str] = Field(default_factory=list)


class HistoricalCase(EventAlphaModel):
    """A historical event case used for analogy and validation research."""

    case_id: str = ""
    title: str
    event_type: str
    event_date: date | None = None
    region: str | None = None
    summary: str
    entities: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    affected_assets: list[str] = Field(default_factory=list)
    causal_chain_summary: list[str] = Field(default_factory=list)
    source_notes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    outcome: HistoricalOutcome | None = None
    causal_assessment: HistoricalCausalAssessment | None = None

    @model_validator(mode="after")
    def fill_case_id(self) -> "HistoricalCase":
        """Fill a stable case ID when callers omit one."""
        if not self.case_id:
            self.case_id = make_historical_case_id(
                title=self.title,
                event_type=self.event_type,
                event_date=self.event_date,
            )
        return self


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()
