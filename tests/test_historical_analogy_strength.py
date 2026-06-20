"""Tests for analogy strength labels and low-context explanations."""

from __future__ import annotations

from eventalpha.history import (
    HistoricalAnalogy,
    analogy_strength_label,
    build_seed_historical_cases,
    retrieve_analogies_for_query,
)


def test_analogy_strength_label_mapping() -> None:
    """Scores should map to stable human-readable strength labels."""
    assert analogy_strength_label(0.70) == "strong"
    assert analogy_strength_label(0.40) == "moderate"
    assert analogy_strength_label(0.20) == "weak"
    assert analogy_strength_label(0.10) == "surface_only"


def test_historical_analogy_fills_strength_label() -> None:
    """HistoricalAnalogy should fill strength_label when omitted."""
    analogy = HistoricalAnalogy(
        historical_case_id="CASE_X",
        historical_case_title="Example",
        overall_score=0.2,
    )

    assert analogy.strength_label == "weak"


def test_query_only_low_context_warning() -> None:
    """Query-only retrieval should explain that a low score can reflect sparse input."""
    analogies = retrieve_analogies_for_query(
        "AI chip export control",
        build_seed_historical_cases(),
        limit=1,
    )

    assert analogies
    assert analogies[0].input_context is not None
    assert analogies[0].input_context.context_label == "query-only"
    assert analogies[0].input_context.low_context_warning
    assert analogies[0].low_score_explanation
    assert "limited input context" in analogies[0].low_score_explanation
