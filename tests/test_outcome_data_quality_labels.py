"""Tests for outcome data quality and reliability labels."""

from __future__ import annotations

from eventalpha.history import HistoricalOutcomeComparator, build_seed_historical_cases, retrieve_analogies_for_query
from eventalpha.schemas import ReviewResult


def test_no_current_outcome_has_insufficient_reliability() -> None:
    """Missing current outcome should keep comparison reliability insufficient."""
    case = build_seed_historical_cases()[0]
    analogy = retrieve_analogies_for_query(case.title, [case], limit=1)[0]

    comparison = HistoricalOutcomeComparator().compare(analogy, case)

    assert comparison.historical_data_quality == "manual_seed_demo"
    assert comparison.current_data_quality == "missing"
    assert comparison.comparison_reliability == "insufficient"


def test_seed_plus_mock_is_demo_only() -> None:
    """Manual seed historical outcome plus mock current outcome is demo-only."""
    case = build_seed_historical_cases()[0]
    analogy = retrieve_analogies_for_query(case.title, [case], limit=1)[0]

    comparison = HistoricalOutcomeComparator().compare(
        analogy,
        case,
        current_market_returns={"T+1": {"actual_return": 0.01}},
        current_data_quality="mock_demo",
        scenario_name="aligned",
    )

    assert comparison.current_data_quality == "mock_demo"
    assert comparison.comparison_reliability == "demo_only"
    assert comparison.scenario_name == "aligned"


def test_seed_plus_review_result_is_preliminary() -> None:
    """Manual seed historical outcome plus ReviewResult should be preliminary."""
    case = build_seed_historical_cases()[0]
    analogy = retrieve_analogies_for_query(case.title, [case], limit=1)[0]
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
        current_review_results=[review],
    )

    assert comparison.current_data_quality == "ledger_review"
    assert comparison.comparison_reliability == "preliminary"
