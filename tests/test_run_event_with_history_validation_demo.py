"""Tests for the Phase 5D.1 EventCard/AntiSpurious demo."""

from __future__ import annotations

from pathlib import Path

from scripts.run_event_with_history_validation_demo import run_event_with_history_validation_demo


def test_event_with_history_validation_demo_runs_offline_without_ledger_write(tmp_path) -> None:
    """The demo should run offline and avoid default ledger writes."""
    ledger_path = Path("eventalpha_mvp.sqlite3")
    before_mtime = ledger_path.stat().st_mtime_ns if ledger_path.exists() else None

    result = run_event_with_history_validation_demo(
        demo_current_ai_export=True,
        mock_outcome_scenario="aligned",
        store_path=tmp_path / "missing_cases.json",
    )

    after_mtime = ledger_path.stat().st_mtime_ns if ledger_path.exists() else None
    assert before_mtime == after_mtime
    assert result["enhanced"]["event_card"].history_validation_summary is not None
    assert result["history_validation_summary"].reliability == "demo_only"


def test_event_with_history_validation_demo_scenarios_differ(tmp_path) -> None:
    """Aligned, mixed, and opposite scenarios should produce different enhancements."""
    aligned = run_event_with_history_validation_demo(
        demo_current_ai_export=True,
        mock_outcome_scenario="aligned",
        store_path=tmp_path / "aligned_cases.json",
    )
    mixed = run_event_with_history_validation_demo(
        demo_current_ai_export=True,
        mock_outcome_scenario="mixed",
        store_path=tmp_path / "mixed_cases.json",
    )
    opposite = run_event_with_history_validation_demo(
        demo_current_ai_export=True,
        mock_outcome_scenario="opposite",
        store_path=tmp_path / "opposite_cases.json",
    )

    assert aligned["history_validation_summary"].overall_validation == "demo_only"
    assert any(
        "supports_chain" in signal
        for signal in aligned["history_validation_summary"].top_signals
    )
    assert any(
        "requires_verification" in signal
        for signal in mixed["history_validation_summary"].top_signals
    )
    assert any(
        "weakens_chain" in signal
        for signal in opposite["history_validation_summary"].top_signals
    )
    assert opposite["enhanced"]["anti_spurious_check"].spurious_risk in {"medium", "high"}


def test_event_with_history_validation_demo_outputs_enhanced_card(tmp_path) -> None:
    """Enhanced card should include history risk and verification text."""
    result = run_event_with_history_validation_demo(
        demo_current_ai_export=True,
        mock_outcome_scenario="mixed",
        store_path=tmp_path / "mixed_cases.json",
    )
    enhanced_card = result["enhanced"]["event_card"]

    assert enhanced_card.history_validation_summary["overall_validation"] == "demo_only"
    assert any("demo signals" in item for item in enhanced_card.risk_factors)
    assert enhanced_card.verification_indicators
