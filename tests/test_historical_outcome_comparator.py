"""Tests for the historical outcome comparator."""

from __future__ import annotations

import pytest

from eventalpha.history import (
    HistoricalCase,
    HistoricalCausalAssessment,
    HistoricalOutcome,
    HistoricalOutcomeComparator,
    build_seed_historical_cases,
    retrieve_analogies_for_query,
)
from eventalpha.schemas import ReviewResult


def test_missing_historical_outcome() -> None:
    """A case without historical outcome should be reported explicitly."""
    case = _case_without_outcome()
    analogy = _analogy_for(case)

    comparison = HistoricalOutcomeComparator().compare(analogy, case)

    assert comparison.comparison_status == "missing_historical_outcome"
    assert comparison.window_comparisons


def test_no_current_outcome_is_insufficient() -> None:
    """Missing current review/market data should not pretend comparability."""
    case = build_seed_historical_cases()[0]
    analogy = _analogy_for(case)

    comparison = HistoricalOutcomeComparator().compare(analogy, case)

    assert comparison.comparison_status == "insufficient_current_outcome"
    assert any("Current review" in reason for reason in comparison.mismatch_reasons)


def test_mock_current_outcome_direction_consistent_is_comparable() -> None:
    """When most windows match direction, comparison should be comparable."""
    case = _case_with_returns({"T+1": 0.01, "T+3": 0.02, "T+7": 0.03})
    analogy = _analogy_for(case)

    comparison = HistoricalOutcomeComparator().compare(
        analogy,
        case,
        current_market_returns={
            "T+1": {"actual_return": 0.02, "benchmark_return": 0.01},
            "T+3": {"actual_return": 0.03, "benchmark_return": 0.01},
            "T+7": {"actual_return": 0.04, "benchmark_return": 0.01},
        },
    )

    assert comparison.comparison_status == "comparable"
    assert all(window.direction_match for window in comparison.window_comparisons)


def test_mock_current_outcome_mixed_is_inconclusive() -> None:
    """Mixed window directions should be classified as inconclusive."""
    case = _case_with_returns({"T+1": 0.01, "T+3": 0.02, "T+7": 0.03})
    analogy = _analogy_for(case)

    comparison = HistoricalOutcomeComparator().compare(
        analogy,
        case,
        current_market_returns={
            "T+1": {"actual_return": 0.02},
            "T+3": {"actual_return": -0.03},
            "T+7": {"actual_return": -0.01},
        },
    )

    assert comparison.comparison_status == "mixed_or_inconclusive"
    assert sum(window.direction_match is False for window in comparison.window_comparisons) == 2


def test_manual_seed_demo_generates_risk_note() -> None:
    """manual_seed_demo outcomes must be clearly marked as illustrative."""
    case = build_seed_historical_cases()[0]
    analogy = _analogy_for(case)

    comparison = HistoricalOutcomeComparator().compare(
        analogy,
        case,
        current_market_returns={"T+1": {"actual_return": 0.0}},
    )

    assert any("manual_seed_demo" in note for note in comparison.risk_notes)
    assert any("not a verified backtest" in note for note in comparison.risk_notes)


def test_magnitude_gap_is_calculated() -> None:
    """Magnitude gap should be absolute current minus historical return."""
    case = _case_with_returns({"T+1": 0.01, "T+3": 0.02, "T+7": 0.03})
    analogy = _analogy_for(case)

    comparison = HistoricalOutcomeComparator().compare(
        analogy,
        case,
        current_market_returns={"T+1": {"actual_return": 0.025}},
    )

    assert comparison.window_comparisons[0].magnitude_gap == pytest.approx(0.015)


def test_review_result_object_and_dict_inputs_are_supported() -> None:
    """Comparator should parse both ReviewResult objects and dict review rows."""
    case = _case_with_returns({"T+1": 0.01, "T+3": 0.02, "T+7": 0.03})
    analogy = _analogy_for(case)
    review = ReviewResult(
        prediction_id="PRED_1",
        event_id="EVT_1",
        horizon="T+1",
        asset_name="AI chips",
        actual_return=0.02,
        benchmark_return=0.01,
        excess_return=0.01,
    )

    comparison = HistoricalOutcomeComparator().compare(
        analogy,
        case,
        current_review_results=[
            review,
            {"horizon": "T+3", "actual_return": 0.03, "benchmark_return": 0.01, "excess_return": 0.02},
        ],
    )

    assert comparison.window_comparisons[0].current_return == pytest.approx(0.02)
    assert comparison.window_comparisons[1].current_excess_return == pytest.approx(0.02)


def _analogy_for(case: HistoricalCase):
    return retrieve_analogies_for_query(case.title, [case], limit=1)[0]


def _case_without_outcome() -> HistoricalCase:
    return HistoricalCase(
        title="Historical case without outcome",
        event_type="test_event",
        summary="No outcome available.",
    )


def _case_with_returns(returns: dict[str, float]) -> HistoricalCase:
    return HistoricalCase(
        title="Historical positive outcome case",
        event_type="test_event",
        summary="A test event with non-zero returns.",
        affected_assets=["test asset"],
        outcome=HistoricalOutcome(
            asset_returns={"test asset": returns},
            time_windows=["T+1", "T+3", "T+7"],
            outcome_quality="verified_demo",
        ),
        causal_assessment=HistoricalCausalAssessment(
            lessons=["Compare current window maturity before drawing conclusions."],
        ),
    )
