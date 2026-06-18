"""Rule update branch tests."""

from __future__ import annotations

from eventalpha.schemas import PredictionLedgerEntry, PredictionReviewSummary
from eventalpha.services import update_rule_from_review


def _prediction() -> PredictionLedgerEntry:
    return PredictionLedgerEntry(
        event_id="EVT_TEST",
        event_title="测试事件",
        event_type="ai_export_control",
    )


def _summary(conclusion_level: str, error_types: list[str]) -> PredictionReviewSummary:
    return PredictionReviewSummary(
        prediction_id="PRED_TEST",
        event_id="EVT_TEST",
        conclusion_level=conclusion_level,  # type: ignore[arg-type]
        error_types=error_types,  # type: ignore[arg-type]
    )


def test_fully_supported_strengthens_rule() -> None:
    update = update_rule_from_review(_prediction(), _summary("fully_supported", ["none"]), 0.50)

    assert update.update_action == "strengthen"
    assert update.new_weight == 0.55


def test_not_supported_weakens_rule() -> None:
    update = update_rule_from_review(
        _prediction(), _summary("not_supported", ["wrong_asset_mapping"]), 0.50
    )

    assert update.update_action == "weaken"
    assert update.new_weight == 0.45


def test_spurious_mapping_weakens_more() -> None:
    update = update_rule_from_review(
        _prediction(), _summary("not_supported", ["spurious_mapping"]), 0.50
    )

    assert update.update_action == "weaken"
    assert update.new_weight == 0.42


def test_macro_factor_override_keeps_weight() -> None:
    update = update_rule_from_review(
        _prediction(),
        _summary("direction_right_causality_unclear", ["macro_factor_override"]),
        0.50,
    )

    assert update.update_action == "keep"
    assert update.new_weight == 0.50
    assert "宏观" in update.reason


def test_priced_in_keeps_weight() -> None:
    update = update_rule_from_review(
        _prediction(), _summary("direction_right_causality_unclear", ["priced_in"]), 0.50
    )

    assert update.update_action == "keep"
    assert update.new_weight == 0.50
    assert "提前定价" in update.reason
