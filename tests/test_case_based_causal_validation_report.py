"""Tests for case-based causal validation reports."""

from __future__ import annotations

from eventalpha.history import (
    AssetLevelHistoricalSignal,
    CaseBasedCausalValidation,
    CaseBasedCausalValidationReportBuilder,
    CausalValidationSignal,
)
from eventalpha.schemas import RISK_DISCLAIMER


def test_case_based_causal_validation_report_contains_required_sections() -> None:
    """Report should include validation status, assets, verifications, and disclaimer."""
    validation = CaseBasedCausalValidation(
        current_event_title="US expands AI chip export controls",
        event_type="ai_export_control",
        overall_validation="demo_only",
        confidence_adjustment_hint=0.02,
        signals=[
            CausalValidationSignal(
                signal_type="supports_chain",
                strength="strong",
                source_case_title="US advanced chip export controls",
                rationale="Historical case supports the chain.",
                reliability="demo_only",
            )
        ],
        asset_signals=[
            AssetLevelHistoricalSignal(
                asset_name="AI chips",
                historical_support="supported",
                support_score=0.8,
                required_verifications=["Verify GPU orders."],
            )
        ],
        required_verifications=["Verify GPU orders."],
        risk_notes=["Demo-only signal."],
    )

    report = CaseBasedCausalValidationReportBuilder().build_text_report(validation)

    assert "overall_validation=demo_only" in report
    assert "asset_signals=" in report
    assert "AI chips" in report
    assert "required_verifications=" in report
    assert RISK_DISCLAIMER in report
