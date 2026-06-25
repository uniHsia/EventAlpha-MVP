"""Tests for page-specific Streamlit console data models."""

from __future__ import annotations

from datetime import date

from eventalpha.briefing import BriefingCollectedData
from eventalpha.ui.components import build_page_data
from eventalpha.ui.pages import _dashboard_shell, _historical_cases_html, _system_status_html


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
        "数据源提示：RSS 最近多次未匹配到新闻，不影响本地只读流程。"
    ]
    assert page_data.raw_debug["raw_warnings"]


def test_dashboard_shell_does_not_render_static_fake_homepage_values() -> None:
    """Homepage HTML should not contain old mocked-as-real values."""
    bundle = {
        "collected_data": BriefingCollectedData(briefing_date=date(2026, 6, 21)),
        "latest_report": None,
        "notes": [],
        "warnings": [],
    }

    html = _dashboard_shell(build_page_data(bundle))

    assert "较昨日" not in html
    assert "全球媒体源" not in html
    assert "所有服务健康" not in html
    assert "查看全部预测账本" not in html
    assert "ea-topbar" not in html
    assert "已发现</div>" not in html
    assert "AI芯片出口管制升级" not in html
    assert "暂无预测记录，请先运行事件分析流程。" in html
    assert "暂无自动复盘结果" in html
    assert "暂无规则更新" in html
    assert "暂无生命周期记录" in html
    assert "Demo Signal" in html
    assert "Demo Chain" in html


def test_dashboard_single_top_event_uses_wide_card_layout() -> None:
    """A single real EventCard should render as one wide card, not a sparse 3-column area."""
    bundle = {
        "collected_data": BriefingCollectedData(
            briefing_date=date(2026, 6, 21),
            event_cards=[
                {
                    "id": 1,
                    "card_id": "CARD_1",
                    "event_id": "EVT_1",
                    "event_title": "AI export event",
                    "event_level": "A",
                    "credibility_score": 0.8,
                    "one_sentence": "summary",
                    "possible_impacts": ["AI chips"],
                    "risk_factors": [],
                    "verification_indicators": ["verify"],
                    "created_at": "2026-06-21",
                }
            ],
        ),
        "latest_report": None,
        "notes": [],
        "warnings": [],
    }

    html = _dashboard_shell(build_page_data(bundle))

    assert "ea-event-cards cols-1" in html
    assert "ea-event-card wide" in html
    assert "AI chips" in html


def test_demo_system_health_metric_uses_split_badge_text() -> None:
    """Demo health should render as main text plus badge, not one wrapped headline."""
    bundle = {
        "collected_data": BriefingCollectedData(briefing_date=date(2026, 6, 21)),
        "latest_report": None,
        "notes": [],
        "warnings": [],
        "source_kind": "demo",
        "source_label": "本地 Demo 数据",
    }

    html = _dashboard_shell(build_page_data(bundle))

    assert "本地 Demo 正常" not in html
    assert '<div class="ea-health-main">本地 Demo</div>' in html
    assert '<span class="ea-health-badge">正常</span>' in html


def test_subpage_product_html_keeps_source_labels_and_no_fake_health() -> None:
    """Historical/system product pages should be honest about demo and health data."""
    bundle = {
        "collected_data": BriefingCollectedData(briefing_date=date(2026, 6, 21)),
        "latest_report": None,
        "notes": [],
        "warnings": [],
        "historical_cases": [
            {
                "case_id": "CASE_SEED_1",
                "title": "Seed historical case",
                "event_type": "ai_export_control",
                "tags": ["manual_seed_demo"],
                "source_notes": ["manual_seed_demo fixture"],
            }
        ],
    }

    page_data = build_page_data(bundle)
    html = _historical_cases_html(page_data.historical_cases) + _system_status_html(page_data)

    assert "Demo Historical Case" in html
    assert "所有服务健康" not in html
    assert "全球媒体源" not in html
    assert "较昨日" not in html
