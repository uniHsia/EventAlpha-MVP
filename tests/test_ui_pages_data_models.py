"""Tests for page-specific Streamlit console data models."""

from __future__ import annotations

from datetime import date

from eventalpha.briefing import BriefingCollectedData
from eventalpha.ui.components import build_page_data


def test_all_page_data_models_are_created_from_empty_state() -> None:
    """Empty local state should still produce all page data sections."""
    bundle = {
        "collected_data": BriefingCollectedData(briefing_date=date(2026, 6, 21)),
        "latest_report": None,
        "notes": [],
        "warnings": [],
    }

    page_data = build_page_data(bundle)

    assert page_data.dashboard.metric_cards
    assert page_data.event_cards == []
    assert page_data.lifecycle_events == []
    assert page_data.background_events == []
    assert page_data.review_results == []
    assert page_data.rule_updates == []
    assert page_data.scheduler_runs == []
    assert page_data.scheduler_jobs == []
    assert page_data.tracking_policies == []
    assert "scheduler_status_counts" in page_data.raw_debug


def test_scheduler_page_debug_data_is_expander_ready() -> None:
    """Scheduler debug fields should exist separately from primary page cards."""
    bundle = {
        "collected_data": BriefingCollectedData(
            briefing_date=date(2026, 6, 21),
            warnings=["RSS query matched no items."],
        ),
        "latest_report": None,
        "notes": ["No scheduler run records found."],
        "warnings": ["RSS query matched no items."],
    }

    page_data = build_page_data(bundle)

    assert page_data.friendly_scheduler_warnings == [
        "数据源提示：RSS 最近多次未匹配到新闻，不影响本地 demo/mock 流程。"
    ]
    assert page_data.raw_debug["raw_warnings"]
