"""Tests for Streamlit console data builders."""

from __future__ import annotations

from datetime import date

from eventalpha.briefing import BriefingCollectedData
from eventalpha.scheduler.schemas import SchedulerRunRecord
from eventalpha.ui.components import build_dashboard_summary, build_page_data


def test_dashboard_summary_handles_empty_state() -> None:
    """Dashboard should be constructible with no local data."""
    bundle = {
        "collected_data": BriefingCollectedData(briefing_date=date(2026, 6, 21)),
        "latest_report": None,
        "notes": ["empty"],
        "warnings": [],
    }

    summary = build_dashboard_summary(bundle)

    assert summary.urgent_count == 0
    assert summary.latest_auto_review_status == "暂无"
    assert summary.notes == ["empty"]


def test_dashboard_summary_reads_auto_review_counts() -> None:
    """Latest auto-review notes should feed summary counters."""
    run = SchedulerRunRecord(
        job_id="auto_review_runner",
        job_type="auto_review_runner",
        status="success",
        notes=["ReviewResult count: 5.", "RuleUpdate count: 1."],
    )
    data = BriefingCollectedData(briefing_date=date(2026, 6, 21), recent_runs=[run])
    bundle = {"collected_data": data, "latest_report": None, "notes": [], "warnings": []}

    summary = build_dashboard_summary(bundle)

    assert summary.latest_auto_review_status == "success"
    assert summary.latest_review_result_count == 5
    assert summary.latest_rule_update_count == 1


def test_page_data_models_are_graceful_for_empty_state() -> None:
    """Every page should have a stable empty list/string value."""
    bundle = {
        "collected_data": BriefingCollectedData(briefing_date=date(2026, 6, 21)),
        "latest_report": None,
        "notes": [],
        "warnings": [],
    }

    page_data = build_page_data(bundle)

    assert page_data.daily_briefing_markdown == ""
    assert page_data.event_cards == []
    assert page_data.lifecycle_events == []
    assert page_data.background_events == []
    assert page_data.review_results == []
    assert page_data.rule_updates == []
    assert page_data.scheduler_runs == []
    assert page_data.scheduler_status_counts == {}
    assert page_data.scheduler_job_type_counts == {}
