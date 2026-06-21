"""Compact summaries of case-based validation for cards and critiques."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import Field, field_validator

from eventalpha.schemas.base import EventAlphaModel

from .causal_validation import CaseBasedCausalValidation


DEMO_HISTORY_RISK_NOTE = (
    "Historical validation signals are illustrative demo signals, not real market evidence."
)

RELIABILITY_RANK = {
    "insufficient": 0,
    "demo_only": 1,
    "preliminary": 2,
    "review_backed": 3,
    "market_backed": 4,
}


class HistoryValidationSummary(EventAlphaModel):
    """Small validation summary used by EventCard and AntiSpuriousCheck."""

    overall_validation: str
    confidence_adjustment_hint: float = 0.0
    top_signals: list[str] = Field(default_factory=list)
    asset_notes: list[str] = Field(default_factory=list)
    transferable_lessons: list[str] = Field(default_factory=list)
    required_verifications: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    reliability: str = "demo_only"

    @field_validator("confidence_adjustment_hint")
    @classmethod
    def clamp_confidence_adjustment_hint(cls, value: float) -> float:
        """Clamp confidence adjustment hints to the Phase 5D conservative range."""
        return round(min(max(float(value), -0.1), 0.1), 4)

    @classmethod
    def from_validation(
        cls,
        validation: CaseBasedCausalValidation,
        *,
        max_signals: int = 5,
        max_asset_notes: int = 6,
        max_lessons: int = 6,
        max_verifications: int = 8,
        max_risk_notes: int = 6,
    ) -> "HistoryValidationSummary":
        """Create a compact summary from a full case-based validation object."""
        reliability = _best_reliability(
            signal.reliability
            for signal in validation.signals
            if signal.signal_type != "insufficient_evidence"
        )
        if reliability == "insufficient" and validation.overall_validation == "demo_only":
            reliability = "demo_only"

        top_signals = [
            _signal_text(signal)
            for signal in validation.signals
            if signal.signal_type != "insufficient_evidence"
        ]
        if validation.overall_validation in {"historically_weakened", "demo_only", "mixed_or_inconclusive"}:
            top_signals.insert(
                0,
                f"overall_validation: {validation.overall_validation}",
            )

        asset_notes = [
            (
                f"{asset.asset_name}: {asset.historical_support}"
                f" (score={asset.support_score:.2f}, reliability={asset.reliability})"
            )
            for asset in validation.asset_signals
            if asset.historical_support != "insufficient"
        ]

        asset_required = [
            item
            for asset in validation.asset_signals
            for item in asset.required_verifications
        ]
        risk_notes = list(validation.risk_notes)
        for signal in validation.signals:
            risk_notes.extend(signal.risk_notes)
        if reliability == "demo_only":
            risk_notes = [DEMO_HISTORY_RISK_NOTE] + risk_notes

        return cls(
            overall_validation=validation.overall_validation,
            confidence_adjustment_hint=validation.confidence_adjustment_hint,
            top_signals=_unique(top_signals)[:max_signals],
            asset_notes=_unique(asset_notes)[:max_asset_notes],
            transferable_lessons=_unique(validation.transferable_lessons)[:max_lessons],
            required_verifications=_unique(
                list(validation.required_verifications) + asset_required
            )[:max_verifications],
            risk_notes=_unique(risk_notes)[:max_risk_notes],
            reliability=reliability,
        )


def _signal_text(signal) -> str:
    source = signal.source_case_title or signal.source_case_id or "historical case"
    return (
        f"{signal.signal_type}: {signal.strength} signal from {source}"
        f" (reliability={signal.reliability})"
    )


def _best_reliability(values: Iterable[str]) -> str:
    reliabilities = [value for value in values if value]
    if not reliabilities:
        return "insufficient"
    return max(reliabilities, key=lambda value: RELIABILITY_RANK.get(value, 0))


def _unique(values: Iterable[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        results.append(text)
    return results
