"""Tests for presentation-ready dashboard summary data."""

from __future__ import annotations

from datetime import date

from eventalpha.briefing import BriefingCollectedData
from eventalpha.news import TrackedEvent
from eventalpha.scheduler.schemas import SchedulerRunRecord
from eventalpha.scheduler.urgency import EventUrgencyScore
from eventalpha.schemas.base import utc_now
from eventalpha.ui.components import build_dashboard_summary, build_page_data


def test_dashboard_summary_contains_chinese_metrics_and_sections() -> None:
    """Dashboard summary should be suitable for a non-technical demo."""
    now = utc_now()
    event = TrackedEvent(
        tracked_event_id="TRACK_1",
        canonical_title="AI chip export controls",
        current_summary="Export controls may affect semiconductor supply chain.",
        lifecycle_stage="developing",
        first_seen_at=now,
        last_seen_at=now,
        sources=["Mock Wire"],
        source_count=1,
        credibility_status="multi_source_supported",
    )
    score = EventUrgencyScore(
        tracked_event_id="TRACK_1",
        title=event.canonical_title,
        urgency_score=70,
        urgency_level="high",
        reasons=["high-impact event type", "updated within 24h"],
    )
    run = SchedulerRunRecord(
        job_id="auto_review_runner",
        job_type="auto_review_runner",
        status="success",
        notes=["ReviewResult count: 1.", "RuleUpdate count: 1."],
    )
    data = BriefingCollectedData(
        briefing_date=date(2026, 6, 21),
        active_events=[event],
        urgency_scores=[score],
        recent_runs=[run],
        review_results=[
            {
                "id": 1,
                "review_id": "REV_1",
                "prediction_id": "PRED_1",
                "asset_name": "AI chips",
                "horizon": "T+1",
                "direction_correct": 1,
                "causal_validity": "valid",
                "excess_return": 0.028,
                "error_type": "none",
                "created_at": "2026-06-21",
            }
        ],
        rule_updates=[
            {
                "id": 1,
                "update_id": "UPD_1",
                "rule_id": "RULE_AI_EXPORT_001",
                "update_action": "strengthen",
                "old_weight": 0.7,
                "new_weight": 0.75,
                "reason": "review supported",
                "created_at": "2026-06-21",
            }
        ],
        warnings=["RSS query matched no items.", "RSS query matched no items."],
    )
    bundle = {"collected_data": data, "latest_report": None, "notes": [], "warnings": data.warnings}

    summary = build_dashboard_summary(bundle)
    page_data = build_page_data(bundle)
    text = str(summary.model_dump(mode="json")) + str(page_data.model_dump(mode="json"))

    assert [metric.label for metric in summary.metric_cards[:4]] == ["紧急事件", "高优先级", "普通跟踪", "背景观察"]
    assert summary.friendly_warnings == ["数据源提示：RSS 最近多次未匹配到新闻，不影响本地 demo/mock 流程。"]
    assert summary.top_events[0]["标题"] == "AI chip export controls"
    assert summary.recent_reviews[0]["资产"] == "AI chips"
    assert summary.recent_rule_updates[0]["RuleID"] == "RULE_AI_EXPORT_001"
    assert "买入" not in text
    assert "卖出" not in text
    assert "目标价" not in text
