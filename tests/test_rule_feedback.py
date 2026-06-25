"""Tests for review feedback signals."""

from __future__ import annotations

from eventalpha.learning import apply_rule_feedback_to_prediction, load_rule_feedback_signals


def test_rule_feedback_positive_and_negative_adjustments_are_clamped() -> None:
    signals = load_rule_feedback_signals(
        review_results=[
            {"PredictionID": "P1", "资产": "AI chips", "因果有效性": "valid", "方向正确": "是"},
            {"PredictionID": "P1", "资产": "AI chips", "因果有效性": "valid", "方向正确": "是"},
            {"PredictionID": "P2", "资产": "Oil", "因果有效性": "invalid", "方向正确": "否"},
            {"PredictionID": "P2", "资产": "Oil", "因果有效性": "invalid", "方向正确": "否"},
            {"PredictionID": "P2", "资产": "Oil", "因果有效性": "invalid", "方向正确": "否"},
        ],
        ledger_rows=[
            {"PredictionID": "P1", "事件类型": "ai_export_control", "资产": "AI chips"},
            {"PredictionID": "P2", "事件类型": "geopolitical_conflict", "资产": "Oil"},
        ],
    )

    by_key = {signal.rule_key: signal for signal in signals}

    assert by_key["ai_export_control:AI chips"].adjustment > 0
    assert by_key["geopolitical_conflict:Oil"].adjustment == -0.1
    assert by_key["geopolitical_conflict:Oil"].needs_verification is True


def test_apply_rule_feedback_returns_metadata_without_mutating_input() -> None:
    row = {"事件类型": "ai_export_control", "资产": "AI chips", "最终置信度": 0.6}
    signals = load_rule_feedback_signals(
        review_results=[{"PredictionID": "P1", "资产": "AI chips", "因果有效性": "valid", "方向正确": "是"}],
        ledger_rows=[{"PredictionID": "P1", "事件类型": "ai_export_control", "资产": "AI chips"}],
    )

    adjusted = apply_rule_feedback_to_prediction(row, signals)

    assert "feedback_adjustment" not in row
    assert adjusted["feedback_adjusted_confidence"] > 0.6
    assert adjusted["feedback_reasons"]
