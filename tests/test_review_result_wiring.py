"""Tests for ReviewResult and dict review outcome wiring."""

from __future__ import annotations

import pytest

from eventalpha.history import (
    HistoricalCase,
    HistoricalCausalAssessment,
    HistoricalOutcome,
    HistoricalOutcomeComparator,
    retrieve_analogies_for_query,
)
from eventalpha.schemas import ReviewResult


def test_review_result_object_is_parsed() -> None:
    """ReviewResult objects should feed current return metrics."""
    case = _case_with_returns()
    analogy = _analogy_for(case)
    review = ReviewResult(
        prediction_id="PRED_1",
        event_id="EVT_1",
        horizon="T+1",
        asset_name="test asset",
        actual_return=0.02,
        benchmark_return=0.01,
        excess_return=0.01,
    )

    comparison = HistoricalOutcomeComparator().compare(analogy, case, current_review_results=[review])

    assert comparison.window_comparisons[0].current_return == pytest.approx(0.02)
    assert comparison.window_comparisons[0].current_excess_return == pytest.approx(0.01)


def test_flat_dict_review_is_parsed() -> None:
    """Flat dict review rows should feed current return metrics."""
    case = _case_with_returns()
    analogy = _analogy_for(case)

    comparison = HistoricalOutcomeComparator().compare(
        analogy,
        case,
        current_review_results=[
            {
                "horizon": "T+3",
                "asset_name": "test asset",
                "actual_return": 0.03,
                "benchmark_return": 0.01,
                "excess_return": 0.02,
                "direction_correct": True,
            }
        ],
    )

    assert comparison.window_comparisons[1].current_return == pytest.approx(0.03)
    assert comparison.window_comparisons[1].current_excess_return == pytest.approx(0.02)


def test_nested_market_return_dict_review_is_parsed() -> None:
    """Nested market_return payloads should feed current return metrics."""
    case = _case_with_returns()
    analogy = _analogy_for(case)

    comparison = HistoricalOutcomeComparator().compare(
        analogy,
        case,
        current_review_results=[
            {
                "horizon": "T+3",
                "market_return": {
                    "actual_return": 0.03,
                    "benchmark_return": 0.01,
                    "excess_return": 0.02,
                },
            }
        ],
    )

    assert comparison.window_comparisons[1].current_return == pytest.approx(0.03)
    assert comparison.window_comparisons[1].current_excess_return == pytest.approx(0.02)


def test_multi_asset_same_horizon_is_averaged() -> None:
    """Multiple assets in one horizon should aggregate by average."""
    case = _case_with_returns()
    analogy = _analogy_for(case)

    comparison = HistoricalOutcomeComparator().compare(
        analogy,
        case,
        current_review_results=[
            {"horizon": "T+1", "asset_name": "asset A", "actual_return": 0.02, "benchmark_return": 0.01},
            {"horizon": "T+1", "asset_name": "asset B", "actual_return": 0.04, "benchmark_return": 0.02},
        ],
    )

    window = comparison.window_comparisons[0]
    assert window.current_return == pytest.approx(0.03)
    assert window.current_excess_return == pytest.approx(0.015)
    assert any("computed from actual_return" in note for note in window.notes)


def test_missing_review_fields_degrade_gracefully() -> None:
    """Missing fields should not raise and should leave explanatory notes."""
    case = _case_with_returns()
    analogy = _analogy_for(case)

    comparison = HistoricalOutcomeComparator().compare(
        analogy,
        case,
        current_review_results=[{"horizon": "T+3", "asset_name": "test asset", "benchmark_return": 0.01}],
    )

    window = comparison.window_comparisons[1]
    assert window.current_return is None
    assert any("missing actual_return" in note for note in window.notes)


def _analogy_for(case: HistoricalCase):
    return retrieve_analogies_for_query(case.title, [case], limit=1)[0]


def _case_with_returns() -> HistoricalCase:
    return HistoricalCase(
        title="Historical positive outcome case",
        event_type="test_event",
        summary="A test event with non-zero returns.",
        affected_assets=["test asset"],
        outcome=HistoricalOutcome(
            asset_returns={"test asset": {"T+1": 0.01, "T+3": 0.02, "T+7": 0.03}},
            time_windows=["T+1", "T+3", "T+7"],
            outcome_quality="verified_backtest",
        ),
        causal_assessment=HistoricalCausalAssessment(
            lessons=["Compare current window maturity before drawing conclusions."],
        ),
    )
