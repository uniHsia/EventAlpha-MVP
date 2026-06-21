"""Tests for Streamlit UI formatting helpers."""

from __future__ import annotations

from eventalpha.ui.formatters import (
    aggregate_rule_updates,
    aggregate_warnings,
    contains_forbidden_trading_terms,
    dedupe_review_results,
    format_credibility_label,
    format_event_card,
    format_lifecycle_stage,
    format_priority_label,
    format_return_pct,
    format_review_explanation,
    format_review_result,
    format_rule_update,
    format_rule_update_action,
    format_warning_friendly,
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
    assert formatted["风险因素"] == ["risk"]
    assert formatted["后续验证指标"] == ["verify"]
    assert formatted["重复折叠数"] == 3
    assert "已折叠 3 条" in formatted["重复说明"]


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
    assert formatted["方向结果"] == "方向正确"
    assert formatted["实际收益"] == "+3.10%"
    assert formatted["超额收益"] == "+2.10%"
    assert "因果链获得支持" in formatted["复盘解释"]


def test_review_explanation_translates_error_types() -> None:
    """Review explanation should translate common review outcomes."""
    assert "mixed/watch 观察方向" in format_review_explanation(
        {
            "asset_name": "半导体设备",
            "horizon": "T+1",
            "direction_correct": 0,
            "excess_return": -0.002,
            "causal_validity": "unknown",
            "error_type": "mixed_or_watch_only",
        }
    )
    assert "可能需要检查资产映射" in format_review_explanation(
        {
            "asset_name": "国产 EDA",
            "horizon": "T+1",
            "direction_correct": 0,
            "excess_return": -0.002,
            "causal_validity": "invalid",
            "error_type": "wrong_asset_mapping",
        }
    )


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
    assert formatted["动作说明"] == "强化规则"
    assert formatted["次数"] == 2
    assert formatted["新权重"] == 0.75
    assert formatted["理由"] == "latest"
    assert "RULE_AI_EXPORT_001 strengthen ×2" == formatted["标题"]


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
    friendly = format_warning_friendly(warnings)

    assert len(warnings) == 3
    assert warnings[0].startswith("RSS query matched no items.")
    assert warnings[0].endswith("2")
    assert friendly[0] == "数据源提示：RSS 最近多次未匹配到新闻，不影响本地 demo/mock 流程。"
    assert not contains_forbidden_trading_terms("关注方向与验证指标")


def test_return_stage_priority_and_rule_labels() -> None:
    """Core labels should be Chinese and graceful with missing values."""
    assert format_return_pct(0.028) == "+2.80%"
    assert format_return_pct(-0.002) == "-0.20%"
    assert format_return_pct(None) == "暂无"
    assert format_lifecycle_stage("developing") == "持续发展"
    assert format_credibility_label("multi_source_supported") == "多源支持"
    assert format_priority_label("background") == "背景观察"
    assert format_rule_update_action("slightly_strengthen") == "小幅强化规则"
    assert format_rule_update_action("keep") == "保持规则"
    assert format_rule_update_action("mystery") == "未知动作"


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
