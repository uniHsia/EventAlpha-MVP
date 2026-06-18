"""Rule weight update service."""

from __future__ import annotations

from eventalpha.schemas import PredictionLedgerEntry, PredictionReviewSummary, RuleUpdate


RULE_DEFAULTS = {
    "ai_export_control": ("RULE_AI_EXPORT_001", 0.70),
    "geopolitical_conflict": ("RULE_GEO_OIL_001", 0.70),
    "rate_policy": ("RULE_RATE_LIQ_001", 0.60),
    "trade_tariff": ("RULE_TARIFF_001", 0.55),
    "earthquake_supply_chain": ("RULE_SUPPLY_CHAIN_001", 0.50),
    "unknown": ("RULE_UNKNOWN_001", 0.40),
}


def update_rule_from_review(
    prediction: PredictionLedgerEntry,
    summary: PredictionReviewSummary,
    old_weight: float | None = None,
) -> RuleUpdate:
    """Create a rule update from an aggregate prediction review summary."""
    rule_id, default_weight = RULE_DEFAULTS.get(
        prediction.event_type, RULE_DEFAULTS["unknown"]
    )
    old = default_weight if old_weight is None else old_weight
    primary_error = _primary_error(summary.error_types)

    if primary_error == "spurious_mapping":
        delta = -0.08
        action = "weaken"
        reason = "复盘显示伪相关映射风险，降低规则权重并要求更强事实验证。"
    elif primary_error == "macro_factor_override":
        delta = 0.0
        action = "keep"
        reason = "复盘显示宏观变量覆盖风险，保持权重但增加宏观覆盖条件。"
    elif primary_error == "priced_in":
        delta = 0.0
        action = "keep"
        reason = "复盘显示可能已提前定价，保持权重但增加提前定价检测条件。"
    elif summary.conclusion_level == "fully_supported":
        delta = 0.05
        action = "strengthen"
        reason = "整条预测方向和因果均获得支持，小幅强化规则。"
    elif summary.conclusion_level == "partially_supported":
        delta = 0.02
        action = "slightly_strengthen"
        reason = "整条预测部分获得支持，仅小幅强化规则。"
    elif summary.conclusion_level == "direction_right_causality_unclear":
        delta = 0.0
        action = "do_not_strengthen"
        reason = "方向有支持但因果不清晰，不强化规则。"
    elif summary.conclusion_level == "not_supported":
        delta = -0.05
        action = "weaken"
        reason = "整条预测未获得复盘支持，降低规则权重。"
    else:
        delta = 0.0
        action = "keep"
        reason = "复盘结果混合，保持权重并继续收集样本。"

    new_weight = max(0.0, min(1.0, round(old + delta, 2)))
    return RuleUpdate(
        rule_id=rule_id,
        prediction_id=prediction.prediction_id,
        review_id=summary.summary_id,
        summary_id=summary.summary_id,
        old_weight=old,
        new_weight=new_weight,
        reason=reason,
        update_action=action,
    )


def _primary_error(error_types: list[str]) -> str:
    priority = ["spurious_mapping", "macro_factor_override", "priced_in"]
    for error_type in priority:
        if error_type in error_types:
            return error_type
    return error_types[0] if error_types else "unknown"
