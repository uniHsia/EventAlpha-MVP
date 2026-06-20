"""Tests for historical analogy schemas."""

from __future__ import annotations

from eventalpha.history import AnalogyDimensionScore, HistoricalAnalogy


def test_historical_analogy_schemas_clamp_scores() -> None:
    """Analogy schemas should clamp scores to 0..1."""
    dimension = AnalogyDimensionScore(
        dimension="event_type",
        score=1.5,
        matched_terms=["ai_export_control"],
    )
    analogy = HistoricalAnalogy(
        current_event_title="AI chip export controls",
        historical_case_id="HCASE_1",
        historical_case_title="Historical export control",
        overall_score=-0.2,
        dimension_scores=[dimension],
    )

    assert dimension.score == 1.0
    assert analogy.overall_score == 0.0
    assert analogy.analogy_id


def test_historical_analogy_id_is_stable() -> None:
    """Analogy ID should be stable for the same current title and historical case."""
    first = HistoricalAnalogy(
        current_event_title="AI chip export controls",
        historical_case_id="HCASE_1",
        historical_case_title="Historical export control",
        overall_score=0.8,
    )
    second = HistoricalAnalogy(
        current_event_title="AI chip export controls",
        historical_case_id="HCASE_1",
        historical_case_title="Historical export control",
        overall_score=0.6,
    )

    assert first.analogy_id == second.analogy_id
