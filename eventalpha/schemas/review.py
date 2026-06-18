"""Review and learning schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from .base import (
    CausalValidity,
    ConclusionLevel,
    Direction,
    ErrorType,
    Horizon,
    RISK_DISCLAIMER,
    TimestampedModel,
    new_id,
    utc_now,
)


ReviewStatus = Literal["pending", "completed", "skipped"]


class ReviewTask(TimestampedModel):
    """Scheduled review task for a ledger entry."""

    task_id: str = Field(default_factory=lambda: new_id("REV_TASK"))
    prediction_id: str
    event_id: str
    horizon: Horizon = "T+3"
    due_at: datetime = Field(default_factory=utc_now)
    status: ReviewStatus = "pending"


class DirectionEvaluation(TimestampedModel):
    """Direction-specific review result for one predicted asset."""

    predicted_direction: Direction = "watch"
    actual_return: float = 0.0
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    is_directional_call: bool = False
    direction_correct: bool | None = None
    outperformed_benchmark: bool = False
    relative_weaker_than_benchmark: bool = False
    evaluation_note: str = ""


class ReviewResult(TimestampedModel):
    """Review result comparing prediction and market outcome."""

    review_id: str = Field(default_factory=lambda: new_id("REV"))
    prediction_id: str
    event_id: str
    horizon: Horizon = "T+3"
    asset_name: str
    predicted_direction: Direction = "watch"
    benchmark: str = "沪深300"
    actual_return: float = 0.0
    benchmark_return: float = 0.0
    excess_return: float = 0.0
    is_directional_call: bool = False
    direction_correct: bool = False
    outperformed_benchmark: bool = False
    direction_evaluation: DirectionEvaluation | None = None
    asset_confidence: float = 0.5
    final_confidence: float = 0.25
    causal_validity: CausalValidity = "unknown"
    review_conclusion: str = ""
    error_type: ErrorType = "unknown"
    risk_disclaimer: str = RISK_DISCLAIMER


class PredictionReviewSummary(TimestampedModel):
    """Aggregate review summary for one prediction across all reviewed assets."""

    summary_id: str = Field(default_factory=lambda: new_id("REV_SUM"))
    prediction_id: str
    event_id: str
    horizon: Horizon = "T+3"
    total_assets: int = 0
    reviewed_assets: int = 0
    direction_correct_count: int = 0
    outperform_count: int = 0
    valid_causal_count: int = 0
    invalid_causal_count: int = 0
    watch_or_mixed_count: int = 0
    average_excess_return: float = 0.0
    conclusion_level: ConclusionLevel = "mixed"
    summary_text: str = ""
    error_types: list[ErrorType] = Field(default_factory=list)
    rule_update_suggestions: list[str] = Field(default_factory=list)
