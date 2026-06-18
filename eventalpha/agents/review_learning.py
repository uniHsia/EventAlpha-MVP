"""Mock review and learning agent."""

from __future__ import annotations

from eventalpha.data_sources import MarketDataProvider
from eventalpha.schemas import (
    DirectionEvaluation,
    PredictedAsset,
    PredictionLedgerEntry,
    PredictionReviewSummary,
    ReviewResult,
)


NEUTRAL_THRESHOLD = 0.005


def evaluate_direction(
    predicted_direction: str,
    actual_return: float,
    benchmark_return: float,
    excess_return: float,
) -> DirectionEvaluation:
    """Evaluate one predicted direction against mock asset and benchmark returns."""
    if predicted_direction == "up":
        direction_correct = actual_return > 0
        outperformed = excess_return > 0
        note = "up 方向要求资产绝对收益为正，超额收益为正表示跑赢基准。"
        return DirectionEvaluation(
            predicted_direction="up",
            actual_return=actual_return,
            benchmark_return=benchmark_return,
            excess_return=excess_return,
            is_directional_call=True,
            direction_correct=direction_correct,
            outperformed_benchmark=outperformed,
            evaluation_note=note,
        )

    if predicted_direction == "down":
        direction_correct = actual_return < 0
        relative_weaker = excess_return < 0
        note = "down 方向要求资产绝对收益为负，超额收益为负表示相对基准更弱。"
        return DirectionEvaluation(
            predicted_direction="down",
            actual_return=actual_return,
            benchmark_return=benchmark_return,
            excess_return=excess_return,
            is_directional_call=True,
            direction_correct=direction_correct,
            outperformed_benchmark=relative_weaker,
            relative_weaker_than_benchmark=relative_weaker,
            evaluation_note=note,
        )

    if predicted_direction == "neutral":
        direction_correct = (
            abs(actual_return) <= NEUTRAL_THRESHOLD
            and abs(excess_return) <= NEUTRAL_THRESHOLD
        )
        note = "neutral 方向要求绝对收益和超额收益都接近 0。"
        return DirectionEvaluation(
            predicted_direction="neutral",
            actual_return=actual_return,
            benchmark_return=benchmark_return,
            excess_return=excess_return,
            is_directional_call=True,
            direction_correct=direction_correct,
            outperformed_benchmark=False,
            evaluation_note=note,
        )

    note = "mixed/watch 仅记录市场表现，不计入方向正确率。"
    return DirectionEvaluation(
        predicted_direction=predicted_direction,  # type: ignore[arg-type]
        actual_return=actual_return,
        benchmark_return=benchmark_return,
        excess_return=excess_return,
        is_directional_call=False,
        direction_correct=None,
        outperformed_benchmark=False,
        evaluation_note=note,
    )


def review_asset(
    prediction: PredictionLedgerEntry,
    asset: PredictedAsset,
    market_data: MarketDataProvider,
    horizon: str = "T+3",
) -> ReviewResult:
    """Review one predicted asset with deterministic mock market returns."""
    actual = market_data.get_asset_return(asset.asset_name, horizon)
    benchmark = market_data.get_benchmark_return(asset.benchmark, horizon)
    excess = round(actual - benchmark, 6)
    evaluation = evaluate_direction(asset.direction, actual, benchmark, excess)

    causal_validity, error_type, conclusion = _infer_causal_result(
        prediction, asset, evaluation
    )

    return ReviewResult(
        prediction_id=prediction.prediction_id,
        event_id=prediction.event_id,
        horizon=horizon,  # type: ignore[arg-type]
        asset_name=asset.asset_name,
        predicted_direction=asset.direction,
        benchmark=asset.benchmark,
        actual_return=actual,
        benchmark_return=benchmark,
        excess_return=excess,
        is_directional_call=evaluation.is_directional_call,
        direction_correct=bool(evaluation.direction_correct),
        outperformed_benchmark=evaluation.outperformed_benchmark,
        direction_evaluation=evaluation,
        asset_confidence=asset.asset_confidence,
        final_confidence=asset.final_confidence,
        causal_validity=causal_validity,  # type: ignore[arg-type]
        review_conclusion=conclusion,
        error_type=error_type,  # type: ignore[arg-type]
    )


def review_prediction(
    prediction: PredictionLedgerEntry,
    market_data: MarketDataProvider,
    horizon: str = "T+3",
) -> list[ReviewResult]:
    """Review all predicted assets that match the requested horizon."""
    candidates = [
        asset for asset in prediction.predicted_assets if asset.time_window == horizon
    ]
    return [
        review_asset(prediction, asset, market_data, horizon=horizon)
        for asset in candidates
    ]


def summarize_reviews(
    prediction: PredictionLedgerEntry,
    reviews: list[ReviewResult],
    horizon: str = "T+3",
) -> PredictionReviewSummary:
    """Aggregate single-asset review results into one prediction-level summary."""
    reviewed_assets = len(reviews)
    direction_correct_count = sum(
        1 for review in reviews if review.is_directional_call and review.direction_correct
    )
    outperform_count = sum(1 for review in reviews if review.outperformed_benchmark)
    valid_causal_count = sum(1 for review in reviews if review.causal_validity == "valid")
    invalid_causal_count = sum(
        1 for review in reviews if review.causal_validity == "invalid"
    )
    watch_or_mixed_count = sum(1 for review in reviews if not review.is_directional_call)
    average_excess = (
        round(sum(review.excess_return for review in reviews) / reviewed_assets, 6)
        if reviewed_assets
        else 0.0
    )
    error_types = sorted({review.error_type for review in reviews}) or [
        "insufficient_evidence"
    ]
    directional_count = reviewed_assets - watch_or_mixed_count
    conclusion_level = _classify_summary(
        reviewed_assets,
        directional_count,
        direction_correct_count,
        valid_causal_count,
        invalid_causal_count,
        error_types,
    )
    suggestions = _rule_suggestions(conclusion_level, error_types)

    return PredictionReviewSummary(
        prediction_id=prediction.prediction_id,
        event_id=prediction.event_id,
        horizon=horizon,  # type: ignore[arg-type]
        total_assets=len(
            [asset for asset in prediction.predicted_assets if asset.time_window == horizon]
        ),
        reviewed_assets=reviewed_assets,
        direction_correct_count=direction_correct_count,
        outperform_count=outperform_count,
        valid_causal_count=valid_causal_count,
        invalid_causal_count=invalid_causal_count,
        watch_or_mixed_count=watch_or_mixed_count,
        average_excess_return=average_excess,
        conclusion_level=conclusion_level,  # type: ignore[arg-type]
        summary_text=_summary_text(conclusion_level, reviewed_assets, error_types),
        error_types=error_types,  # type: ignore[arg-type]
        rule_update_suggestions=suggestions,
    )


def _infer_causal_result(
    prediction: PredictionLedgerEntry,
    asset: PredictedAsset,
    evaluation: DirectionEvaluation,
) -> tuple[str, str, str]:
    """Infer mock causal validity from event type and direction evaluation."""
    if prediction.event_type == "earthquake_supply_chain":
        return (
            "invalid",
            "spurious_mapping",
            "供应链替代映射未被 mock 市场表现支持，伪相关风险较高。",
        )

    if not evaluation.is_directional_call:
        return (
            "unknown",
            "mixed_or_watch_only",
            "该资产为 mixed/watch 观察方向，仅记录市场表现，不判断方向正确。",
        )

    if prediction.event_type == "rate_policy":
        if abs(evaluation.actual_return) <= NEUTRAL_THRESHOLD or abs(
            evaluation.excess_return
        ) <= NEUTRAL_THRESHOLD:
            return (
                "unknown",
                "priced_in",
                "市场表现不明显，可能已提前定价，需增加提前定价检测。",
            )
        if evaluation.direction_correct:
            return (
                "partially_valid",
                "macro_factor_override",
                "方向有一定支持，但利率事件容易被更强宏观变量覆盖。",
            )

    if prediction.event_type == "geopolitical_conflict" and evaluation.direction_correct:
        return (
            "partially_valid",
            "macro_factor_override",
            "方向正确，但能源与避险资产受库存、美元和风险偏好共同影响。",
        )

    if evaluation.direction_correct and evaluation.outperformed_benchmark:
        return ("valid", "none", "方向正确且基准验证通过，mock 因果链获得支持。")
    if evaluation.direction_correct:
        return (
            "partially_valid",
            "macro_factor_override",
            "方向正确但基准验证不充分，需要检查宏观变量覆盖。",
        )
    return (
        "invalid",
        "wrong_asset_mapping",
        "方向未被市场表现验证，需要检查资产映射或事件重要性判断。",
    )


def _classify_summary(
    reviewed_assets: int,
    directional_count: int,
    direction_correct_count: int,
    valid_causal_count: int,
    invalid_causal_count: int,
    error_types: list[str],
) -> str:
    if reviewed_assets == 0:
        return "not_supported"
    if "spurious_mapping" in error_types and valid_causal_count == 0:
        return "not_supported"
    if directional_count == 0:
        return "mixed"
    if (
        direction_correct_count == directional_count
        and valid_causal_count == directional_count
        and invalid_causal_count == 0
    ):
        return "fully_supported"
    if direction_correct_count > 0 and valid_causal_count > 0:
        return "partially_supported"
    if direction_correct_count > 0 and valid_causal_count == 0:
        return "direction_right_causality_unclear"
    return "not_supported"


def _summary_text(conclusion_level: str, reviewed_assets: int, error_types: list[str]) -> str:
    if reviewed_assets == 0:
        return "没有可复盘资产，无法验证本条预测。"
    if conclusion_level == "fully_supported":
        return "多资产复盘支持原始方向和因果链。"
    if conclusion_level == "partially_supported":
        return "部分资产支持原始判断，但仍需验证弱链条。"
    if conclusion_level == "direction_right_causality_unclear":
        return "方向有支持，但因果解释不充分，不应强化规则。"
    if conclusion_level == "not_supported":
        return f"复盘不支持原始判断，主要错误类型：{', '.join(error_types)}。"
    return "复盘结果混合或以观察项为主，继续收集证据。"


def _rule_suggestions(conclusion_level: str, error_types: list[str]) -> list[str]:
    if "spurious_mapping" in error_types:
        return ["降低伪相关映射规则权重", "要求更强事实验证后再映射资产"]
    if "priced_in" in error_types:
        return ["增加提前定价检测条件"]
    if "macro_factor_override" in error_types:
        return ["增加宏观变量覆盖条件"]
    if conclusion_level == "fully_supported":
        return ["小幅强化当前因果规则"]
    if conclusion_level == "not_supported":
        return ["降低当前因果规则权重"]
    return ["保持规则，等待更多复盘样本"]
