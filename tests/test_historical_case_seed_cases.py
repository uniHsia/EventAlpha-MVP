"""Tests for historical seed cases."""

from __future__ import annotations

from eventalpha.history import build_seed_historical_cases


def test_seed_cases_cover_core_event_types() -> None:
    """Seed cases should cover the Phase 5A required topics."""
    cases = build_seed_historical_cases()
    event_types = {case.event_type for case in cases}
    tags = {tag for case in cases for tag in case.tags}

    assert len(cases) >= 8
    assert "ai_export_control" in event_types
    assert "geopolitical_conflict" in event_types
    assert "rate_policy" in event_types
    assert "trade_tariff" in event_types
    assert "earthquake_supply_chain" in event_types
    assert "technology_breakthrough" in event_types
    assert "election_policy" in event_types
    assert "cloud_ai_capex" in event_types
    assert "red_sea" in tags


def test_each_seed_case_has_lessons_or_outcome() -> None:
    """Every seed case should have useful demo content."""
    for historical_case in build_seed_historical_cases():
        has_lessons = bool(
            historical_case.causal_assessment
            and historical_case.causal_assessment.lessons
        )
        assert historical_case.outcome or has_lessons
        if historical_case.outcome:
            assert historical_case.outcome.outcome_quality == "manual_seed_demo"
