"""Tests for the Phase 5C outcome comparison demo."""

from __future__ import annotations

from scripts.run_historical_outcome_comparison_demo import run_historical_outcome_comparison_demo


def test_outcome_comparison_demo_runs_offline_without_current_outcome(tmp_path) -> None:
    """Default demo should run offline and report insufficient current outcome."""
    result = run_historical_outcome_comparison_demo(
        limit=1,
        store_path=tmp_path / "missing_cases.json",
    )

    assert result["used_seed_memory"] is True
    assert result["comparisons"]
    assert result["comparisons"][0].comparison_status == "insufficient_current_outcome"
    assert "Historical Outcome Comparison Report" in result["report"]


def test_outcome_comparison_demo_current_ai_export_context(tmp_path) -> None:
    """Rich AI export-control context should still produce comparisons."""
    result = run_historical_outcome_comparison_demo(
        demo_current_ai_export=True,
        limit=1,
        store_path=tmp_path / "missing_cases.json",
    )

    assert result["analogies"][0].historical_case_title.startswith("US advanced chip")
    assert result["comparisons"][0].historical_case_title.startswith("US advanced chip")


def test_outcome_comparison_demo_with_mock_current_outcome(tmp_path) -> None:
    """Mock current outcome should produce window-level comparisons."""
    result = run_historical_outcome_comparison_demo(
        demo_current_ai_export=True,
        with_mock_current_outcome=True,
        limit=1,
        store_path=tmp_path / "missing_cases.json",
    )

    comparison = result["comparisons"][0]
    assert comparison.comparison_status == "comparable"
    assert result["current_market_returns"]
    assert all(window.current_return is not None for window in comparison.window_comparisons)
