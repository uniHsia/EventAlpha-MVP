"""Tests for daily briefing schemas."""

from __future__ import annotations

from datetime import date

from eventalpha.briefing import BriefingItem, BriefingSection, DailyBriefing


def test_daily_briefing_schemas_create_with_disclaimer() -> None:
    """Briefing schemas should be lightweight and include the disclaimer."""
    item = BriefingItem(item_id="item1", title="Event", item_type="event")
    section = BriefingSection(section_id="new_events", title="今日重点事件", items=[item])
    briefing = DailyBriefing(
        briefing_date=date(2026, 6, 21),
        title="EventAlpha Daily Briefing - 2026-06-21",
        sections=[section],
    )

    assert briefing.sections[0].items[0].title == "Event"
    assert briefing.risk_disclaimer
    assert "Daily Briefing" in briefing.title
