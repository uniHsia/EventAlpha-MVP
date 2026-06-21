"""Schemas for case-based causal validation."""

from __future__ import annotations

from pydantic import Field, field_validator

from eventalpha.schemas.base import EventAlphaModel, new_id


class CausalValidationSignal(EventAlphaModel):
    """One historical validation signal for a current causal chain."""

    signal_id: str = Field(default_factory=lambda: new_id("CVAL_SIG"))
    signal_type: str
    strength: str
    source_case_id: str | None = None
    source_case_title: str | None = None
    rationale: str
    affected_chain_steps: list[int] = Field(default_factory=list)
    related_assets: list[str] = Field(default_factory=list)
    reliability: str = "demo_only"
    risk_notes: list[str] = Field(default_factory=list)


class AssetLevelHistoricalSignal(EventAlphaModel):
    """Historical validation signal aggregated for one mapped asset."""

    asset_name: str
    historical_support: str
    support_score: float
    supporting_cases: list[str] = Field(default_factory=list)
    weakening_cases: list[str] = Field(default_factory=list)
    lessons: list[str] = Field(default_factory=list)
    required_verifications: list[str] = Field(default_factory=list)
    reliability: str = "demo_only"

    @field_validator("support_score")
    @classmethod
    def clamp_support_score(cls, value: float) -> float:
        """Clamp support score into 0..1."""
        return round(min(max(float(value), 0.0), 1.0), 4)


class CaseBasedCausalValidation(EventAlphaModel):
    """Case-based validation summary for one current event."""

    validation_id: str = Field(default_factory=lambda: new_id("CVAL"))
    current_event_title: str
    event_type: str | None = None
    overall_validation: str
    confidence_adjustment_hint: float = 0.0
    signals: list[CausalValidationSignal] = Field(default_factory=list)
    asset_signals: list[AssetLevelHistoricalSignal] = Field(default_factory=list)
    transferable_lessons: list[str] = Field(default_factory=list)
    non_transferable_lessons: list[str] = Field(default_factory=list)
    required_verifications: list[str] = Field(default_factory=list)
    validation_notes: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)

    @field_validator("confidence_adjustment_hint")
    @classmethod
    def clamp_confidence_adjustment_hint(cls, value: float) -> float:
        """Clamp confidence adjustment hints into a conservative range."""
        return round(min(max(float(value), -0.1), 0.1), 4)
