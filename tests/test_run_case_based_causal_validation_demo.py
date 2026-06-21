"""Tests for the Phase 5D case-based causal validation demo."""

from __future__ import annotations

from pathlib import Path

from scripts.run_case_based_causal_validation_demo import run_case_based_causal_validation_demo


def test_case_based_causal_validation_demo_runs_offline(tmp_path) -> None:
    """Default demo should run offline and avoid ledger writes."""
    ledger_path = Path("eventalpha_mvp.sqlite3")
    before_mtime = ledger_path.stat().st_mtime_ns if ledger_path.exists() else None

    result = run_case_based_causal_validation_demo(
        store_path=tmp_path / "missing_cases.json",
        limit=1,
    )

    after_mtime = ledger_path.stat().st_mtime_ns if ledger_path.exists() else None
    assert result["used_seed_memory"] is True
    assert result["analogies"]
    assert result["comparisons"]
    assert result["validation"].signals
    assert "Case-Based Causal Validation Report" in result["report"]
    assert before_mtime == after_mtime


def test_case_based_causal_validation_demo_aligned_mixed_opposite(tmp_path) -> None:
    """All deterministic mock scenarios should run with distinct validation signals."""
    aligned = run_case_based_causal_validation_demo(
        demo_current_ai_export=True,
        mock_outcome_scenario="aligned",
        store_path=tmp_path / "aligned_cases.json",
        limit=1,
    )
    mixed = run_case_based_causal_validation_demo(
        demo_current_ai_export=True,
        mock_outcome_scenario="mixed",
        store_path=tmp_path / "mixed_cases.json",
        limit=1,
    )
    opposite = run_case_based_causal_validation_demo(
        demo_current_ai_export=True,
        mock_outcome_scenario="opposite",
        store_path=tmp_path / "opposite_cases.json",
        limit=1,
    )

    assert aligned["comparisons"][0].comparison_status == "comparable"
    assert aligned["validation"].overall_validation in {"demo_only", "partially_supported"}
    assert mixed["comparisons"][0].comparison_status == "mixed_or_inconclusive"
    assert any(signal.signal_type == "requires_verification" for signal in mixed["validation"].signals)
    assert opposite["comparisons"][0].comparison_status == "mixed_or_inconclusive"
    assert any(signal.signal_type in {"requires_verification", "weakens_chain"} for signal in opposite["validation"].signals)


def test_case_based_causal_validation_demo_uses_mock_demo_reliability(tmp_path) -> None:
    """Demo comparisons should remain marked as demo-only."""
    result = run_case_based_causal_validation_demo(
        demo_current_ai_export=True,
        mock_outcome_scenario="aligned",
        store_path=tmp_path / "missing_cases.json",
        limit=1,
    )

    assert result["comparisons"][0].comparison_reliability == "demo_only"
    assert any("illustrative only" in note for note in result["validation"].risk_notes)
