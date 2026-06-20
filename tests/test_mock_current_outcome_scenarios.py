"""Tests for deterministic mock current outcome scenarios."""

from __future__ import annotations

from scripts.run_historical_outcome_comparison_demo import run_historical_outcome_comparison_demo


def test_mock_current_outcome_aligned_is_comparable(tmp_path) -> None:
    """Aligned mock returns should produce a comparable first AI-export comparison."""
    result = run_historical_outcome_comparison_demo(
        demo_current_ai_export=True,
        with_mock_current_outcome=True,
        mock_outcome_scenario="aligned",
        limit=1,
        store_path=tmp_path / "missing_cases.json",
    )

    comparison = result["comparisons"][0]
    assert comparison.comparison_status == "comparable"
    assert comparison.current_data_quality == "mock_demo"
    assert comparison.comparison_reliability == "demo_only"
    assert comparison.scenario_name == "aligned"


def test_mock_current_outcome_mixed_is_inconclusive(tmp_path) -> None:
    """Mixed mock returns should produce mixed or inconclusive status."""
    result = run_historical_outcome_comparison_demo(
        demo_current_ai_export=True,
        with_mock_current_outcome=True,
        mock_outcome_scenario="mixed",
        limit=1,
        store_path=tmp_path / "missing_cases.json",
    )

    comparison = result["comparisons"][0]
    assert comparison.comparison_status == "mixed_or_inconclusive"
    assert comparison.scenario_name == "mixed"
    assert any(window.direction_match is False for window in comparison.window_comparisons)


def test_mock_current_outcome_opposite_is_inconclusive(tmp_path) -> None:
    """Opposite mock returns should not be classified as comparable."""
    result = run_historical_outcome_comparison_demo(
        demo_current_ai_export=True,
        with_mock_current_outcome=True,
        mock_outcome_scenario="opposite",
        limit=1,
        store_path=tmp_path / "missing_cases.json",
    )

    comparison = result["comparisons"][0]
    assert comparison.comparison_status == "mixed_or_inconclusive"
    assert comparison.scenario_name == "opposite"
    assert all(window.direction_match is False for window in comparison.window_comparisons)


def test_mock_current_outcome_is_deterministic_and_local(tmp_path) -> None:
    """Repeated calls with a missing temp store should produce the same local mock returns."""
    kwargs = {
        "demo_current_ai_export": True,
        "with_mock_current_outcome": True,
        "mock_outcome_scenario": "aligned",
        "limit": 1,
        "store_path": tmp_path / "missing_cases.json",
    }

    first = run_historical_outcome_comparison_demo(**kwargs)
    second = run_historical_outcome_comparison_demo(**kwargs)

    assert first["used_seed_memory"] is True
    assert second["used_seed_memory"] is True
    assert first["current_market_returns"] == second["current_market_returns"]
