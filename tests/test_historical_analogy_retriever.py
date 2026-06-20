"""Tests for historical analogy retriever helpers."""

from __future__ import annotations

from eventalpha.history import (
    HistoricalAnalogyRetriever,
    build_seed_historical_cases,
    retrieve_analogies_for_query,
    retrieve_analogies_for_structured_event,
    retrieve_analogies_for_tracked_event,
)
from eventalpha.news import TrackedEvent
from eventalpha.schemas import StructuredEvent
from eventalpha.schemas.base import utc_now


def test_query_retrieval_returns_ai_chip_analogies() -> None:
    """Query retrieval should surface AI chip analogies."""
    cases = build_seed_historical_cases()

    results = retrieve_analogies_for_query("AI chip export control", cases, limit=3)

    assert results
    assert results[0].historical_case_title.startswith("US advanced chip")


def test_structured_event_retrieval() -> None:
    """StructuredEvent retrieval should use event type and assets."""
    cases = build_seed_historical_cases()
    event = StructuredEvent(
        event_type="ai_export_control",
        event_title="US expands AI chip export controls",
        summary="Advanced GPU export controls affect semiconductor supply chains.",
        entities=["US Commerce Department", "China"],
        affected_industries=["semiconductors", "AI infrastructure"],
        affected_assets_hint=["AI chips", "GPUs"],
    )

    results = retrieve_analogies_for_structured_event(event, cases, limit=2)

    assert results[0].historical_case_title.startswith("US advanced chip")


def test_tracked_event_retrieval() -> None:
    """TrackedEvent retrieval should use title, claims, and keywords."""
    cases = build_seed_historical_cases()
    now = utc_now()
    tracked = TrackedEvent(
        canonical_title="AI chip export controls on advanced GPUs",
        first_seen_at=now,
        last_seen_at=now,
        latest_claims=["AI chip export controls affect semiconductor supply chains"],
        dominant_keywords=["AI_chip", "semiconductor", "GPU"],
    )

    results = retrieve_analogies_for_tracked_event(tracked, cases, limit=2)

    assert results
    assert results[0].overall_score >= results[-1].overall_score


def test_limit_and_sort_order() -> None:
    """Retriever should honor limit and sort descending by score."""
    cases = build_seed_historical_cases()

    results = HistoricalAnalogyRetriever(cases).retrieve(query="AI chip export control", limit=2)

    assert len(results) == 2
    assert results[0].overall_score >= results[1].overall_score
