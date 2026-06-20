"""Tests for historical analogy scoring."""

from __future__ import annotations

from eventalpha.history import HistoricalAnalogyRetriever, build_seed_historical_cases


def test_event_type_match_improves_score() -> None:
    """Exact event type should lift the matching case score."""
    cases = build_seed_historical_cases()
    retriever = HistoricalAnalogyRetriever(cases)

    exact = retriever.retrieve(event_type="ai_export_control", limit=1)[0]
    unrelated = retriever.retrieve(event_type="ai_export_control", assets=["crude oil"], limit=5)[-1]

    assert exact.historical_case_title.startswith("US advanced chip")
    assert exact.overall_score > unrelated.overall_score


def test_asset_overlap_improves_score() -> None:
    """Asset overlap should rank relevant oil cases highly."""
    cases = build_seed_historical_cases()

    results = HistoricalAnalogyRetriever(cases).retrieve(assets=["crude oil"], limit=3)

    assert results
    assert any("oil" in analogy.historical_case_title.casefold() for analogy in results)
    assert results[0].overall_score > 0


def test_unrelated_case_has_low_score() -> None:
    """Unrelated signals should not produce a high score."""
    cases = build_seed_historical_cases()

    results = HistoricalAnalogyRetriever(cases).retrieve(
        query="local restaurant menu sports entertainment",
        assets=["stadium food"],
        limit=3,
    )

    assert not results or results[0].overall_score < 0.25


def test_dimension_scores_include_core_dimensions_and_terms() -> None:
    """Dimension scores should be present with matched terms."""
    cases = build_seed_historical_cases()

    analogy = HistoricalAnalogyRetriever(cases).retrieve(
        query="AI chip export control",
        event_type="ai_export_control",
        assets=["AI chips", "GPU"],
        tags=["semiconductor"],
        limit=1,
    )[0]
    dimensions = {score.dimension: score for score in analogy.dimension_scores}

    assert set(dimensions) == {
        "event_type",
        "affected_assets",
        "entities",
        "industries",
        "tags",
        "causal_chain",
        "query_keywords",
        "region",
    }
    assert dimensions["event_type"].score == 1.0
    assert dimensions["affected_assets"].matched_terms
