"""Tests for Streamlit UI formatting helpers."""

from __future__ import annotations

from eventalpha.ui.formatters import (
    aggregate_rule_updates,
    aggregate_warnings,
    contains_forbidden_trading_terms,
    dedupe_review_results,
    format_event_card,
    format_review_result,
    format_rule_update,
)


def test_event_card_formatter_outputs_chinese_fields() -> None:
    """EventCard formatter should expose UI-friendly Chinese labels."""
    row = {
        "card_id": "CARD_1",
        "event_id": "EVT_1",
        "event_title": "AI export event",
        "event_level": "A",
        "one_sentence": "summary",
        "risk_factors": ["risk"],
        "verification_indicators": ["verify"],
        "duplicate_count": 3,
    }

    formatted = format_event_card(row)

    assert formatted["标题"] == "AI export event"
    assert formatted["风险"] == ["risk"]
    assert formatted["验证"] == ["verify"]
    assert formatted["重复数"] == 3


def test_review_result_formatter_formats_returns_and_direction() -> None:
    """ReviewResult values should be compact and readable."""
    formatted = format_review_result(
        {
            "review_id": "REV_1",
            "prediction_id": "PRED_1",
            "asset_name": "AI chips",
            "horizon": "T+1",
            "causal_validity": "valid",
            "direction_correct": 1,
            "actual_return": 0.031,
            "benchmark_return": 0.01,
            "excess_return": 0.021,
            "error_type": "none",
        }
    )

    assert formatted["方向正确"] == "是"
    assert formatted["实际收益"] == "3.10%"
    assert formatted["超额收益"] == "2.10%"


def test_rule_update_aggregation_formatter() -> None:
    """Rule updates should group by rule/action before formatting."""
    rows = [
        {
            "id": 1,
            "update_id": "UPD_1",
            "rule_id": "RULE_AI_EXPORT_001",
            "update_action": "strengthen",
            "old_weight": 0.7,
            "new_weight": 0.72,
            "reason": "old",
            "created_at": "2026-06-20",
        },
        {
            "id": 2,
            "update_id": "UPD_2",
            "rule_id": "RULE_AI_EXPORT_001",
            "update_action": "strengthen",
            "old_weight": 0.72,
            "new_weight": 0.75,
            "reason": "latest",
            "created_at": "2026-06-21",
        },
    ]

    formatted = format_rule_update(aggregate_rule_updates(rows)[0])

    assert formatted["RuleID"] == "RULE_AI_EXPORT_001"
    assert formatted["动作"] == "strengthen"
    assert formatted["次数"] == 2
    assert formatted["新权重"] == 0.75
    assert formatted["理由"] == "latest"


def test_warning_aggregation_and_forbidden_terms() -> None:
    """Warnings should aggregate and formatter output should avoid trading terms."""
    warnings = aggregate_warnings(
        [
            "RSS query matched no items.",
            "RSS query matched no items.",
            "Provider timeout.",
            "CSV missing.",
            "hidden",
        ],
        limit=3,
    )

    assert len(warnings) == 3
    assert warnings[0].startswith("RSS query matched no items.")
    assert warnings[0].endswith("2")
    assert not contains_forbidden_trading_terms("关注方向与验证指标")


def test_review_result_dedup_uses_prediction_asset_horizon() -> None:
    """Duplicate asset/horizon rows should collapse to latest."""
    rows = [
        {
            "id": 1,
            "review_id": "REV_OLD",
            "prediction_id": "PRED_1",
            "asset_name": "AI chips",
            "horizon": "T+1",
            "created_at": "2026-06-20",
        },
        {
            "id": 2,
            "review_id": "REV_NEW",
            "prediction_id": "PRED_1",
            "asset_name": "AI chips",
            "horizon": "T+1",
            "created_at": "2026-06-21",
        },
    ]

    deduped = dedupe_review_results(rows)

    assert len(deduped) == 1
    assert deduped[0]["review_id"] == "REV_NEW"
    assert deduped[0]["duplicate_count"] == 2
