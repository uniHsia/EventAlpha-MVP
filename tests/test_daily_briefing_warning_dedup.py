"""Tests for warning aggregation in daily briefings."""

from __future__ import annotations

from datetime import date

from eventalpha.briefing import BriefingCollectedData, DailyBriefingBuilder
from eventalpha.scheduler.schemas import SchedulerRunRecord


def test_warning_messages_are_aggregated_and_limited() -> None:
    """Repeated and already-aggregated warnings should merge into one counted message."""
    data = BriefingCollectedData(
        briefing_date=date(2026, 6, 21),
        warnings=[
            "RSS query matched no items.",
            "RSS query matched no items.",
            "Provider timeout.",
            "Provider timeout.",
            "CSV missing row.",
            "Fourth warning should be hidden.",
            "RSS query matched no items. x3",
        ],
    )

    briefing = DailyBriefingBuilder(max_items=10).build(data)
    system = _section(briefing, "system_status")

    rss_warning = next(item for item in briefing.warnings if item.startswith("RSS query matched no items."))
    provider_warning = next(item for item in briefing.warnings if item.startswith("Provider timeout."))
    assert rss_warning.endswith("5")
    assert provider_warning.endswith("2")
    assert len(briefing.warnings) == 3
    assert any(note.startswith("Recent warning: RSS query matched no items.") and note.endswith("5") for note in system.notes)
    assert not any("Fourth warning" in note for note in system.notes)


def test_run_level_warnings_are_not_repeated_in_scheduler_items() -> None:
    """System status should keep run warnings aggregated at section note level."""
    run = SchedulerRunRecord(
        job_id="scheduler_status",
        job_type="scheduler_status",
        status="success",
        warnings=["RSS query matched no items.", "RSS query matched no items."],
    )
    data = BriefingCollectedData(
        briefing_date=date(2026, 6, 21),
        recent_runs=[run],
        warnings=run.warnings,
    )

    briefing = DailyBriefingBuilder(max_items=10).build(data)
    system = _section(briefing, "system_status")

    assert any(note.startswith("Recent warning: RSS query matched no items.") for note in system.notes)
    assert system.items[0].risk_notes == []


def _section(briefing, section_id):
    return next(section for section in briefing.sections if section.section_id == section_id)
