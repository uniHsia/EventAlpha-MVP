"""Tests for the Phase 5C outcome comparison demo."""

from __future__ import annotations

from eventalpha.history import HistoricalCaseStore, build_seed_historical_cases
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
    assert result["comparisons"][0].current_data_quality == "missing"
    assert result["comparisons"][0].comparison_reliability == "insufficient"
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
    assert comparison.current_data_quality == "mock_demo"
    assert comparison.comparison_reliability == "demo_only"
    assert comparison.scenario_name == "aligned"
    assert result["current_market_returns"]
    assert all(window.current_return is not None for window in comparison.window_comparisons)


def test_outcome_comparison_demo_refreshes_old_zero_seed_store(tmp_path) -> None:
    """Old persisted manual seed stores with zero returns should use current seed returns in memory."""
    path = tmp_path / "historical_cases.json"
    store = HistoricalCaseStore(path)
    old_seed_cases = build_seed_historical_cases()
    for historical_case in old_seed_cases:
        if historical_case.outcome:
            historical_case.outcome.asset_returns = {
                asset: {"T+1": 0.0, "T+3": 0.0, "T+7": 0.0}
                for asset in historical_case.affected_assets[:3]
            }
        store.upsert(historical_case)
    store.save()

    result = run_historical_outcome_comparison_demo(
        demo_current_ai_export=True,
        with_mock_current_outcome=True,
        limit=1,
        store_path=path,
    )

    comparison = result["comparisons"][0]
    assert result["refreshed_seed_outcomes"] is True
    assert comparison.comparison_status == "comparable"
    assert all(window.historical_return != 0.0 for window in comparison.window_comparisons)
