"""Tests for case-based causal validation schemas."""

from __future__ import annotations

from eventalpha.history import (
    AssetLevelHistoricalSignal,
    CaseBasedCausalValidation,
    CausalValidationSignal,
)


def test_causal_validation_signal_can_be_created() -> None:
    """Signal schema should create stable local IDs and default lists."""
    signal = CausalValidationSignal(
        signal_type="supports_chain",
        strength="strong",
        rationale="Historical case supports the chain.",
    )

    assert signal.signal_id.startswith("CVAL_SIG_")
    assert signal.reliability == "demo_only"
    assert signal.affected_chain_steps == []
    assert signal.related_assets == []


def test_asset_level_historical_signal_can_be_created_and_clamps_score() -> None:
    """Asset support scores should be clamped into 0..1."""
    signal = AssetLevelHistoricalSignal(
        asset_name="AI chips",
        historical_support="supported",
        support_score=1.5,
    )

    assert signal.support_score == 1.0
    assert signal.supporting_cases == []
    assert signal.reliability == "demo_only"


def test_case_based_causal_validation_can_be_created_and_clamps_hint() -> None:
    """Validation schema should clamp confidence adjustment hints conservatively."""
    validation = CaseBasedCausalValidation(
        current_event_title="Current event",
        event_type="ai_export_control",
        overall_validation="demo_only",
        confidence_adjustment_hint=0.5,
    )

    assert validation.validation_id.startswith("CVAL_")
    assert validation.confidence_adjustment_hint == 0.1
    assert validation.signals == []
    assert validation.asset_signals == []
