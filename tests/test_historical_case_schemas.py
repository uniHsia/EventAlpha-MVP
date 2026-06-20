"""Tests for historical case schemas."""

from __future__ import annotations

from datetime import date

from eventalpha.history import (
    HistoricalCase,
    HistoricalCausalAssessment,
    HistoricalOutcome,
)


def test_historical_case_schemas_roundtrip() -> None:
    """Historical case schemas should be creatable and JSON round-trippable."""
    outcome = HistoricalOutcome(
        benchmark="illustrative benchmark",
        asset_returns={"AI chips": {"T+1": 0.0, "T+3": 0.0}},
        market_reaction_summary="Manual seed example.",
        outcome_quality="manual_seed_demo",
    )
    assessment = HistoricalCausalAssessment(
        expected_direction="mixed",
        realized_direction="mixed",
        causal_validity="partially_valid",
        lessons=["Validate direct and second-order mappings separately."],
    )
    case = HistoricalCase(
        title="US AI chip export control example",
        event_type="ai_export_control",
        event_date=date(2022, 10, 7),
        summary="Illustrative historical case.",
        affected_assets=["AI chips"],
        outcome=outcome,
        causal_assessment=assessment,
    )

    restored = HistoricalCase.model_validate(case.model_dump(mode="json"))

    assert case.case_id == restored.case_id
    assert restored.outcome.outcome_quality == "manual_seed_demo"
    assert restored.causal_assessment.lessons


def test_historical_case_id_is_stable() -> None:
    """Omitted case IDs should be stable for the same title/type/date."""
    first = HistoricalCase(
        title="Rate cut example",
        event_type="rate_policy",
        event_date=date(2020, 3, 3),
        summary="Example.",
    )
    second = HistoricalCase(
        title="Rate cut example",
        event_type="rate_policy",
        event_date=date(2020, 3, 3),
        summary="Example with different body.",
    )

    assert first.case_id == second.case_id
