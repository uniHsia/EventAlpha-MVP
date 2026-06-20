"""Schemas for historical analogy retrieval."""

from __future__ import annotations

import hashlib
import re

from pydantic import Field, field_validator, model_validator

from eventalpha.schemas.base import EventAlphaModel


def make_analogy_id(current_event_title: str | None, historical_case_id: str) -> str:
    """Generate a stable analogy ID."""
    key = f"{_normalize_text(current_event_title or '')}::{_normalize_text(historical_case_id)}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"ANALOGY_{digest}"


def analogy_strength_label(score: float) -> str:
    """Map an analogy score to a human-readable strength label."""
    if score >= 0.60:
        return "strong"
    if score >= 0.35:
        return "moderate"
    if score >= 0.15:
        return "weak"
    return "surface_only"


class AnalogyInputContext(EventAlphaModel):
    """Diagnostic summary of how much current-event context was provided."""

    provided_dimensions: list[str] = Field(default_factory=list)
    missing_dimensions: list[str] = Field(default_factory=list)
    context_completeness_score: float = 0.0
    context_label: str = "partial"
    low_context_warning: str | None = None

    @field_validator("context_completeness_score")
    @classmethod
    def clamp_context_score(cls, value: float) -> float:
        """Clamp context completeness into 0..1."""
        return round(min(max(float(value), 0.0), 1.0), 4)


class AnalogyDimensionScore(EventAlphaModel):
    """Score for one analogy dimension."""

    dimension: str
    score: float
    matched_terms: list[str] = Field(default_factory=list)
    explanation: str | None = None

    @field_validator("score")
    @classmethod
    def clamp_score(cls, value: float) -> float:
        """Clamp dimension score into 0..1."""
        return round(min(max(float(value), 0.0), 1.0), 4)


class HistoricalAnalogy(EventAlphaModel):
    """Rule-based analogy between a current event and a historical case."""

    analogy_id: str = ""
    current_event_title: str | None = None
    historical_case_id: str
    historical_case_title: str
    overall_score: float
    strength_label: str = ""
    input_context: AnalogyInputContext | None = None
    low_score_explanation: str | None = None
    dimension_scores: list[AnalogyDimensionScore] = Field(default_factory=list)
    similarities: list[str] = Field(default_factory=list)
    differences: list[str] = Field(default_factory=list)
    transferable_lessons: list[str] = Field(default_factory=list)
    non_transferable_lessons: list[str] = Field(default_factory=list)
    verification_suggestions: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)

    @field_validator("overall_score")
    @classmethod
    def clamp_overall_score(cls, value: float) -> float:
        """Clamp overall score into 0..1."""
        return round(min(max(float(value), 0.0), 1.0), 4)

    @model_validator(mode="after")
    def fill_analogy_id(self) -> "HistoricalAnalogy":
        """Fill stable ID when omitted."""
        if not self.analogy_id:
            self.analogy_id = make_analogy_id(self.current_event_title, self.historical_case_id)
        if not self.strength_label:
            self.strength_label = analogy_strength_label(self.overall_score)
        if not self.low_score_explanation and self.input_context and self.input_context.low_context_warning:
            self.low_score_explanation = self.input_context.low_context_warning
        return self


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip()).casefold()
