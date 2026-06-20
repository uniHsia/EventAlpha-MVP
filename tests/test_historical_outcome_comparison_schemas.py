"""Tests for historical outcome comparison schemas."""

from __future__ import annotations

from eventalpha.history import (
    HistoricalCurrentOutcomePair,
    HistoricalOutcomeComparison,
    HistoricalOutcomeComparator,
    OutcomeWindowComparison,
    build_seed_historical_cases,
    make_outcome_comparison_id,
    retrieve_analogies_for_query,
)


def test_outcome_window_comparison_allows_none_fields() -> None:
    """Window schema should allow missing current/historical return fields."""
    window = OutcomeWindowComparison(window="T+1")

    assert window.window == "T+1"
    assert window.current_return is None
    assert window.direction_match is None


def test_historical_outcome_comparison_can_be_created() -> None:
    """Comparison schema should support optional score and empty windows."""
    comparison = HistoricalOutcomeComparison(
        historical_case_id="CASE_X",
        historical_case_title="Example",
        analogy_score=None,
        comparison_status="insufficient_current_outcome",
    )

    assert comparison.analogy_score is None
    assert comparison.window_comparisons == []
    assert comparison.comparison_id
    assert comparison.historical_data_quality == "unknown"
    assert comparison.current_data_quality == "missing"
    assert comparison.comparison_reliability == "insufficient"
    assert comparison.scenario_name is None


def test_comparison_id_is_stable() -> None:
    """Comparison IDs should be stable for the same analogy/case/title tuple."""
    first = make_outcome_comparison_id("ANALOGY_1", "CASE_1", "Current")
    second = make_outcome_comparison_id("ANALOGY_1", "CASE_1", "Current")

    assert first == second


def test_historical_current_outcome_pair_can_be_created() -> None:
    """Pair schema should wrap analogy, case, and current outcome payloads."""
    cases = build_seed_historical_cases()
    analogy = retrieve_analogies_for_query("AI chip export control", cases, limit=1)[0]
    pair = HistoricalCurrentOutcomePair(
        analogy=analogy,
        historical_case=cases[0],
        current_market_returns={"T+1": {"actual_return": 0.0}},
    )

    assert pair.analogy.historical_case_id == cases[0].case_id
    assert pair.current_market_returns
