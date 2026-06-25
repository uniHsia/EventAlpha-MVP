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
    assert page_data.prediction_ledger_rows == []
    assert page_data.lifecycle_summary["source_kind"] == "real"
    assert page_data.daily_briefing_preview["source_kind"] == "placeholder"
    assert all(row["source_kind"] in {"real", "demo", "placeholder"} for row in page_data.scheduler_status_rows)
    assert page_data.historical_cases == []
    assert page_data.historical_case_summary["历史案例数"] == 0
    assert page_data.page_updated_at == "未记录"
    assert page_data.source_coverage_summary["source_kind"] == "placeholder"
    assert page_data.search_quality_summary["source_kind"] == "placeholder"
    assert page_data.rule_feedback_summary["signal_count"] == 0
    assert page_data.push_outbox_summary["source_kind"] == "placeholder"


def test_homepage_sections_carry_source_kind_for_loaded_rows() -> None:
    """Homepage-specific rows should expose data provenance."""
    data = BriefingCollectedData(
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
        review_results=[
            {
                "id": 1,
                "review_id": "REV_1",
                "prediction_id": "PRED_1",
                "asset_name": "AI chips",
                "horizon": "T+1",
                "causal_validity": "valid",
                "direction_correct": 1,
                "excess_return": 0.02,
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
                "reason": "worked",
            }
        ],
    )
    bundle = {
        "collected_data": data,
        "latest_report": None,
        "notes": [],
        "warnings": [],
        "prediction_ledger_rows": [
            {
                "prediction_id": "PRED_1",
                "event_id": "EVT_1",
                "event_title": "AI export event",
                "asset_name": "AI chips",
                "direction": "up",
                "time_window": "T+1",
                "status": "tracking",
            }
        ],
    }

    page_data = build_page_data(bundle)

    assert page_data.event_cards[0]["source_kind"] == "real"
    assert page_data.prediction_ledger_rows[0]["source_kind"] == "real"
    assert page_data.review_results[0]["source_kind"] == "real"
    assert page_data.rule_updates[0]["source_kind"] == "real"
    assert page_data.asset_signal_rows[0]["source_kind"] == "real"
    assert page_data.causal_evidence_rows
    assert page_data.causal_evidence_summary["total"] >= 1


def test_capability_report_summaries_are_loaded_into_page_data() -> None:
    """Capability reports should become compact UI summaries."""
    bundle = {
        "collected_data": BriefingCollectedData(briefing_date=date(2026, 6, 21)),
        "latest_report": None,
        "notes": [],
        "warnings": [],
        "capability_reports": {
            "source_coverage": {"demo_mode": True, "enabled_count": 1, "ok_count": 1, "failed_count": 0, "placeholder_count": 3, "_path": "reports/demo/source.json"},
            "search_quality": {"demo_mode": True, "raw_news_count": 3, "after_dedup_count": 2, "cluster_count": 1, "event_card_count": 1, "ledger_prediction_count": 1},
            "rule_feedback": {"demo_mode": True, "signal_count": 1, "signals": [{"rule_key": "x", "adjustment": 0.03}]},
            "push_outbox": {"demo_mode": True, "message_count": 1, "channel_note": "wechat placeholder"},
        },
    }

    page_data = build_page_data(bundle)

    assert page_data.source_coverage_summary["ok_count"] == 1
    assert page_data.search_quality_summary["cluster_count"] == 1
    assert page_data.rule_feedback_summary["signal_count"] == 1
    assert page_data.push_outbox_summary["message_count"] == 1


def test_historical_seed_cases_are_marked_demo() -> None:
    """Manual seed/demo historical cases should not be presented as real evidence."""
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
                "event_date": "2024-01-01",
                "summary": "Manual seed record.",
                "affected_assets": ["AI chips"],
                "tags": ["manual_seed_demo"],
                "source_notes": ["manual_seed_demo fixture"],
                "outcome": {
                    "outcome_quality": "manual_seed_demo",
                    "market_reaction_summary": "Illustrative outcome.",
                },
                "causal_assessment": {
                    "expected_direction": "up",
                    "realized_direction": "up",
                    "causal_validity": "valid",
                },
            }
        ],
    }

    page_data = build_page_data(bundle)

    assert page_data.historical_cases[0]["source_kind"] == "demo"
    assert page_data.historical_cases[0]["source_label"] == "Demo Historical Case"
    assert page_data.historical_case_summary["历史案例数"] == 1
    assert page_data.historical_case_summary["已有 outcome"] == 1
