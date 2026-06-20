"""Schemas for comparing historical outcomes with current event outcomes."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from pydantic import Field, model_validator

from eventalpha.schemas.base import EventAlphaModel

from .analogy import HistoricalAnalogy
from .schemas import HistoricalCase


DEFAULT_OUTCOME_WINDOWS = ["T+1", "T+3", "T+7"]


def make_outcome_comparison_id(
    analogy_id: str,
    historical_case_id: str,
    current_event_title: str | None = None,
) -> str:
    """Generate a stable comparison ID."""
    key = "::".join(
        [
            _normalize_text(analogy_id),
            _normalize_text(historical_case_id),
            _normalize_text(current_event_title or ""),
        ]
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"OUTCOME_CMP_{digest}"


class OutcomeWindowComparison(EventAlphaModel):
    """Comparison for one T+n window."""

    window: str
    historical_direction: str | None = None
    current_direction: str | None = None
    historical_return: float | None = None
    current_return: float | None = None
    historical_excess_return: float | None = None
    current_excess_return: float | None = None
    direction_match: bool | None = None
    excess_return_sign_match: bool | None = None
    magnitude_gap: float | None = None
    notes: list[str] = Field(default_factory=list)


class HistoricalOutcomeComparison(EventAlphaModel):
    """Outcome comparison between a historical case and current event outcome."""

    comparison_id: str = ""
    current_event_title: str | None = None
    historical_case_id: str
    historical_case_title: str
    analogy_score: float | None = None
    analogy_strength_label: str | None = None
    outcome_quality: str | None = None
    historical_data_quality: str = "unknown"
    current_data_quality: str = "missing"
    comparison_reliability: str = "insufficient"
    scenario_name: str | None = None
    comparison_status: str
    window_comparisons: list[OutcomeWindowComparison] = Field(default_factory=list)
    matched_lessons: list[str] = Field(default_factory=list)
    mismatch_reasons: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def fill_comparison_id(self) -> "HistoricalOutcomeComparison":
        """Fill stable comparison ID when omitted."""
        if not self.comparison_id:
            self.comparison_id = make_outcome_comparison_id(
                analogy_id=f"{self.historical_case_id}:{self.analogy_score}",
                historical_case_id=self.historical_case_id,
                current_event_title=self.current_event_title,
            )
        return self


class HistoricalCurrentOutcomePair(EventAlphaModel):
    """Input pair for historical-current outcome comparison."""

    analogy: HistoricalAnalogy
    historical_case: HistoricalCase
    current_review_results: list[Any] = Field(default_factory=list)
    current_market_returns: dict[str, Any] = Field(default_factory=dict)


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()
