"""Tests for rule-based historical case search."""

from __future__ import annotations

from eventalpha.history import (
    search_cases,
    search_cases_for_structured_event,
    search_cases_for_tracked_event,
    build_seed_historical_cases,
)
from eventalpha.news import TrackedEvent
from eventalpha.schemas import StructuredEvent
from eventalpha.schemas.base import utc_now


def test_event_type_search_prioritizes_exact_match() -> None:
    cases = build_seed_historical_cases()

    results = search_cases(cases, event_type="ai_export_control", limit=3)

    assert results
    assert results[0].event_type == "ai_export_control"


def test_asset_overlap_search_matches_relevant_case() -> None:
    cases = build_seed_historical_cases()

    results = search_cases(cases, assets=["crude oil"], limit=3)

    assert results
    assert any("crude oil" in [asset.casefold() for asset in case.affected_assets] for case in results)


def test_query_keyword_search_matches_ai_chip_case() -> None:
    cases = build_seed_historical_cases()

    results = search_cases(cases, query="AI chip export control", limit=3)

    assert results
    assert results[0].event_type == "ai_export_control"


def test_tags_entities_and_limit_are_applied() -> None:
    cases = build_seed_historical_cases()

    results = search_cases(cases, entities=["Federal Reserve"], tags=["rates"], limit=1)

    assert len(results) == 1
    assert "Federal Reserve" in results[0].entities or "rates" in results[0].tags


def test_search_cases_for_tracked_event() -> None:
    cases = build_seed_historical_cases()
    now = utc_now()
    tracked_event = TrackedEvent(
        canonical_title="US expands AI chip export controls on advanced GPUs",
        first_seen_at=now,
        last_seen_at=now,
        latest_claims=["US expands AI chip export controls"],
        dominant_keywords=["AI_chip", "semiconductor"],
    )

    results = search_cases_for_tracked_event(cases, tracked_event, limit=2)

    assert results
    assert results[0].event_type == "ai_export_control"


def test_search_cases_for_structured_event() -> None:
    cases = build_seed_historical_cases()
    event = StructuredEvent(
        event_type="trade_tariff",
        event_title="New tariff policy announced",
        summary="Tariff pressure on import supply chains.",
        entities=["United States", "China"],
        affected_assets_hint=["importers", "domestic substitutes"],
    )

    results = search_cases_for_structured_event(cases, event, limit=2)

    assert results
    assert results[0].event_type == "trade_tariff"
