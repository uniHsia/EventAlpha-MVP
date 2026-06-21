"""Tests for compact history validation summaries."""

from __future__ import annotations

from eventalpha.history import (
    AssetLevelHistoricalSignal,
    CaseBasedCausalValidation,
    CausalValidationSignal,
    DEMO_HISTORY_RISK_NOTE,
    HistoryValidationSummary,
)


def test_history_validation_summary_from_validation_is_compact() -> None:
    """Summary should keep only card/anti-spurious relevant fields."""
    validation = CaseBasedCausalValidation(
        current_event_title="US expands AI chip export controls",
        overall_validation="demo_only",
        confidence_adjustment_hint=0.02,
        signals=[
            CausalValidationSignal(
                signal_type="supports_chain",
                strength="strong",
                source_case_title="AI export controls",
                rationale="History supports the chain.",
                reliability="demo_only",
            ),
            CausalValidationSignal(
                signal_type="second_order_warning",
                strength="moderate",
                source_case_title="AI export controls",
                rationale="Second-order mapping needs verification.",
                reliability="demo_only",
            ),
        ],
        asset_signals=[
            AssetLevelHistoricalSignal(
                asset_name="semiconductor equipment",
                historical_support="second_order_watch",
                support_score=0.4,
                required_verifications=["Verify equipment orders."],
                reliability="demo_only",
            )
        ],
        transferable_lessons=["Separate direct and second-order mappings."],
        required_verifications=["Verify GPU orders."],
        risk_notes=["Manual seed demo signal."],
    )

    summary = HistoryValidationSummary.from_validation(validation)

    assert summary.overall_validation == "demo_only"
    assert summary.reliability == "demo_only"
    assert summary.confidence_adjustment_hint == 0.02
    assert any("supports_chain" in signal for signal in summary.top_signals)
    assert any("semiconductor equipment" in note for note in summary.asset_notes)
    assert "Verify GPU orders." in summary.required_verifications
    assert "Verify equipment orders." in summary.required_verifications
    assert DEMO_HISTORY_RISK_NOTE in summary.risk_notes


def test_history_validation_summary_clamps_confidence_hint() -> None:
    """Summary confidence hint should stay in the conservative range."""
    summary = HistoryValidationSummary(
        overall_validation="historically_supported",
        confidence_adjustment_hint=0.5,
    )

    assert summary.confidence_adjustment_hint == 0.1


def test_history_validation_summary_uses_strongest_reliability() -> None:
    """Summary reliability should use strongest useful contributing signal."""
    validation = CaseBasedCausalValidation(
        current_event_title="Current event",
        overall_validation="partially_supported",
        signals=[
            CausalValidationSignal(
                signal_type="supports_chain",
                strength="moderate",
                rationale="Review backed support.",
                reliability="review_backed",
            ),
            CausalValidationSignal(
                signal_type="priced_in_risk",
                strength="weak",
                rationale="Pricing risk.",
                reliability="preliminary",
            ),
        ],
    )

    summary = HistoryValidationSummary.from_validation(validation)

    assert summary.reliability == "review_backed"
    assert DEMO_HISTORY_RISK_NOTE not in summary.risk_notes
