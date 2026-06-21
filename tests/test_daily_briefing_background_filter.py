"""Tests for background filtering in daily briefings."""

from __future__ import annotations

from datetime import date, timedelta

from eventalpha.briefing import BriefingCollectedData, DailyBriefingBuilder
from eventalpha.news import TrackedEvent
from eventalpha.scheduler import EventPriorityRanker
from eventalpha.schemas.base import utc_now


def test_background_analysis_sources_do_not_enter_new_events() -> None:
    """Think tank and analysis-only events should not be top events."""
    now = utc_now()
    urgent = TrackedEvent(
        canonical_title="Official AI chip export control confirmed",
        current_summary="Official confirmed update.",
        lifecycle_stage="developing",
        first_seen_at=now - timedelta(hours=1),
        last_seen_at=now,
        source_count=3,
        sources=["Official Source", "Wire"],
        credibility_status="high_confidence",
        official_evidence_status="official_source_present",
        dominant_keywords=["AI chip", "export control"],
    )
    think_tank = TrackedEvent(
        canonical_title="Brookings analysis of AI export controls",
        current_summary="Commentary background.",
        lifecycle_stage="developing",
        first_seen_at=now - timedelta(hours=1),
        last_seen_at=now,
        source_count=1,
        sources=["Brookings"],
        credibility_status="single_source_low_confidence",
        dominant_keywords=["analysis", "AI chip"],
    )
    analysis_only = TrackedEvent(
        canonical_title="Foundation commentary on policy design",
        lifecycle_stage="analysis_only",
        first_seen_at=now,
        last_seen_at=now,
        source_count=1,
        sources=["Foundation"],
        credibility_status="analysis_only",
    )
    scores = EventPriorityRanker().rank([urgent, think_tank, analysis_only])
    data = BriefingCollectedData(
        briefing_date=date(2026, 6, 21),
        active_events=[urgent, think_tank, analysis_only],
        urgency_scores=scores,
    )

    section = _section(DailyBriefingBuilder(max_items=10).build(data), "new_events")
    titles = [item.title for item in section.items]

    assert urgent.canonical_title in titles
    assert think_tank.canonical_title not in titles
    assert analysis_only.canonical_title not in titles


def _section(briefing, section_id):
    return next(section for section in briefing.sections if section.section_id == section_id)
