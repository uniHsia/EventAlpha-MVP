"""Rule-based historical outcome comparator."""

from __future__ import annotations

from typing import Any

from .analogy import HistoricalAnalogy
from .outcome_comparison import (
    DEFAULT_OUTCOME_WINDOWS,
    HistoricalOutcomeComparison,
    OutcomeWindowComparison,
    make_outcome_comparison_id,
)
from .schemas import HistoricalCase


MANUAL_SEED_RISK_NOTE = "Historical outcome is manual_seed_demo illustrative data, not a verified backtest."


class HistoricalOutcomeComparator:
    """Compare illustrative historical outcomes with current review or market outcomes."""

    def compare(
        self,
        analogy: HistoricalAnalogy,
        historical_case: HistoricalCase,
        current_review_results: list[Any] | None = None,
        current_market_returns: dict[str, Any] | None = None,
        current_data_quality: str | None = None,
        scenario_name: str | None = None,
    ) -> HistoricalOutcomeComparison:
        """Build a deterministic historical-current outcome comparison."""
        current_review_results = current_review_results or []
        current_market_returns = current_market_returns or {}
        historical_outcome = historical_case.outcome
        outcome_quality = historical_outcome.outcome_quality if historical_outcome else None
        historical_data_quality = outcome_quality or "unknown"
        windows = historical_outcome.time_windows if historical_outcome else DEFAULT_OUTCOME_WINDOWS
        risk_notes = ["Historical outcome comparison is a research aid and not investment advice."]
        validation_notes: list[str] = []
        mismatch_reasons: list[str] = []

        if outcome_quality == "manual_seed_demo":
            risk_notes.append(MANUAL_SEED_RISK_NOTE)
            validation_notes.append("Historical outcome is an MVP seed example and must not be treated as real return validation.")
            mismatch_reasons.append("Historical case is seed demo data, so any match is illustrative only.")

        if not historical_outcome:
            labels = _quality_labels(
                historical_data_quality=historical_data_quality,
                current_data_quality=current_data_quality,
                current_source=_current_source_hint(current_review_results, current_market_returns),
                has_current_outcome=bool(current_review_results or current_market_returns),
                has_historical_outcome=False,
            )
            return self._comparison(
                analogy=analogy,
                historical_case=historical_case,
                outcome_quality=outcome_quality,
                historical_data_quality=historical_data_quality,
                current_data_quality=labels["current_data_quality"],
                comparison_reliability=labels["comparison_reliability"],
                scenario_name=scenario_name,
                status="missing_historical_outcome",
                windows=windows,
                mismatch_reasons=["Historical case has no outcome data."],
                validation_notes=["Add historical outcome windows before comparing this analogy."],
                risk_notes=risk_notes,
            )

        historical_returns = _historical_window_returns(historical_outcome.asset_returns, windows)
        current_returns, current_source = _current_window_returns(
            current_review_results,
            current_market_returns,
            windows,
        )
        has_current_outcome = any(metrics.get("current_return") is not None for metrics in current_returns.values())
        labels = _quality_labels(
            historical_data_quality=historical_data_quality,
            current_data_quality=current_data_quality,
            current_source=current_source,
            has_current_outcome=has_current_outcome,
            has_historical_outcome=True,
        )

        if not has_current_outcome:
            mismatch_reasons.extend(
                [
                    "Current review or market outcome is not available yet.",
                    "Current review windows may not have matured.",
                ]
            )
            return self._comparison(
                analogy=analogy,
                historical_case=historical_case,
                outcome_quality=outcome_quality,
                historical_data_quality=historical_data_quality,
                current_data_quality=labels["current_data_quality"],
                comparison_reliability=labels["comparison_reliability"],
                scenario_name=scenario_name,
                status="insufficient_current_outcome",
                windows=windows,
                historical_returns=historical_returns,
                current_returns=current_returns,
                mismatch_reasons=mismatch_reasons,
                validation_notes=validation_notes + ["Run review/market-return collection after T+ windows mature."],
                risk_notes=risk_notes,
            )

        window_comparisons = [
            _compare_window(window, historical_returns.get(window, {}), current_returns.get(window, {}))
            for window in windows
        ]
        comparable_windows = [window for window in window_comparisons if window.direction_match is not None]
        match_count = sum(1 for window in comparable_windows if window.direction_match)
        mismatch_count = sum(1 for window in comparable_windows if window.direction_match is False)
        status = "comparable" if comparable_windows and match_count > mismatch_count else "mixed_or_inconclusive"

        if status == "mixed_or_inconclusive":
            mismatch_reasons.extend(
                [
                    "Window-level direction results are mixed or incomplete.",
                    "Current event status, asset mapping, or market pricing may differ from the historical case.",
                ]
            )
        else:
            validation_notes.append("Most comparable windows point in the same direction as the historical outcome.")
        mismatch_reasons.extend(_standard_mismatch_reasons())

        return HistoricalOutcomeComparison(
            comparison_id=make_outcome_comparison_id(
                analogy.analogy_id,
                historical_case.case_id,
                analogy.current_event_title,
            ),
            current_event_title=analogy.current_event_title,
            historical_case_id=historical_case.case_id,
            historical_case_title=historical_case.title,
            analogy_score=analogy.overall_score,
            analogy_strength_label=analogy.strength_label,
            outcome_quality=outcome_quality,
            historical_data_quality=historical_data_quality,
            current_data_quality=labels["current_data_quality"],
            comparison_reliability=labels["comparison_reliability"],
            scenario_name=scenario_name,
            comparison_status=status,
            window_comparisons=window_comparisons,
            matched_lessons=_matched_lessons(historical_case),
            mismatch_reasons=_unique(mismatch_reasons),
            validation_notes=_unique(validation_notes),
            risk_notes=_unique(risk_notes),
        )

    def _comparison(
        self,
        *,
        analogy: HistoricalAnalogy,
        historical_case: HistoricalCase,
        outcome_quality: str | None,
        historical_data_quality: str,
        current_data_quality: str,
        comparison_reliability: str,
        scenario_name: str | None,
        status: str,
        windows: list[str],
        historical_returns: dict[str, dict[str, Any]] | None = None,
        current_returns: dict[str, dict[str, Any]] | None = None,
        mismatch_reasons: list[str] | None = None,
        validation_notes: list[str] | None = None,
        risk_notes: list[str] | None = None,
    ) -> HistoricalOutcomeComparison:
        historical_returns = historical_returns or {}
        current_returns = current_returns or {}
        return HistoricalOutcomeComparison(
            comparison_id=make_outcome_comparison_id(
                analogy.analogy_id,
                historical_case.case_id,
                analogy.current_event_title,
            ),
            current_event_title=analogy.current_event_title,
            historical_case_id=historical_case.case_id,
            historical_case_title=historical_case.title,
            analogy_score=analogy.overall_score,
            analogy_strength_label=analogy.strength_label,
            outcome_quality=outcome_quality,
            historical_data_quality=historical_data_quality,
            current_data_quality=current_data_quality,
            comparison_reliability=comparison_reliability,
            scenario_name=scenario_name,
            comparison_status=status,
            window_comparisons=[
                _compare_window(window, historical_returns.get(window, {}), current_returns.get(window, {}))
                for window in windows
            ],
            matched_lessons=_matched_lessons(historical_case),
            mismatch_reasons=_unique(mismatch_reasons or []),
            validation_notes=_unique(validation_notes or []),
            risk_notes=_unique(risk_notes or []),
        )


def _historical_window_returns(
    asset_returns: dict[str, dict[str, float]],
    windows: list[str],
) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for window in windows:
        values = [
            float(returns[window])
            for returns in asset_returns.values()
            if isinstance(returns, dict) and window in returns and returns[window] is not None
        ]
        average = _average(values)
        results[window] = {
            "historical_return": average,
            "historical_excess_return": None,
        }
    return results


def _current_window_returns(
    review_results: list[Any],
    market_returns: dict[str, Any],
    windows: list[str],
) -> tuple[dict[str, dict[str, Any]], str]:
    review_metrics = _review_window_returns(review_results, windows)
    if any(metrics.get("current_return") is not None for metrics in review_metrics.values()):
        return review_metrics, "review"
    market_metrics = _market_window_returns(market_returns, windows)
    if any(metrics.get("current_return") is not None for metrics in market_metrics.values()):
        return market_metrics, "market"
    if review_results:
        return review_metrics, "review"
    if market_returns:
        return market_metrics, "market"
    return market_metrics, "none"


def _review_window_returns(review_results: list[Any], windows: list[str]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {
        window: {"actual_return": [], "benchmark_return": [], "excess_return": [], "notes": []}
        for window in windows
    }
    for review in review_results:
        horizon = _get_value(review, "horizon")
        if horizon not in grouped:
            continue
        actual = _review_metric_float(review, "actual_return", horizon, grouped[horizon]["notes"])
        benchmark = _review_metric_float(review, "benchmark_return", horizon, grouped[horizon]["notes"])
        excess = _review_metric_float(review, "excess_return", horizon, grouped[horizon]["notes"], required=False)
        if actual is not None:
            grouped[horizon]["actual_return"].append(actual)
        if benchmark is not None:
            grouped[horizon]["benchmark_return"].append(benchmark)
        if excess is None and actual is not None and benchmark is not None:
            excess = round(actual - benchmark, 6)
            grouped[horizon]["notes"].append(
                f"Current review row missing excess_return for {horizon}; computed from actual_return minus benchmark_return."
            )
        elif excess is None:
            grouped[horizon]["notes"].append(f"Current review row missing excess_return for {horizon}.")
        if excess is not None:
            grouped[horizon]["excess_return"].append(excess)
    return {
        window: {
            "current_return": _average(values["actual_return"]),
            "current_benchmark_return": _average(values["benchmark_return"]),
            "current_excess_return": _average(values["excess_return"]),
            "notes": _unique(values["notes"]),
        }
        for window, values in grouped.items()
    }


def _market_window_returns(market_returns: dict[str, Any], windows: list[str]) -> dict[str, dict[str, Any]]:
    if not market_returns:
        return {window: {"current_return": None, "current_excess_return": None} for window in windows}
    if any(window in market_returns for window in windows):
        return {
            window: _direct_market_metrics(market_returns.get(window))
            for window in windows
        }
    results: dict[str, dict[str, Any]] = {}
    for window in windows:
        actual_values = []
        benchmark_values = []
        excess_values = []
        for asset_payload in market_returns.values():
            if isinstance(asset_payload, dict) and asset_payload.get(window) is not None:
                metrics = _direct_market_metrics(asset_payload[window])
                if metrics.get("current_return") is not None:
                    actual_values.append(metrics["current_return"])
                if metrics.get("current_benchmark_return") is not None:
                    benchmark_values.append(metrics["current_benchmark_return"])
                if metrics.get("current_excess_return") is not None:
                    excess_values.append(metrics["current_excess_return"])
        results[window] = {
            "current_return": _average(actual_values),
            "current_benchmark_return": _average(benchmark_values),
            "current_excess_return": _average(excess_values),
        }
    return results


def _direct_market_metrics(payload: Any) -> dict[str, float | None]:
    if isinstance(payload, dict):
        actual = _float_or_none(payload.get("actual_return", payload.get("current_return")))
        benchmark = _float_or_none(payload.get("benchmark_return"))
        excess = _float_or_none(payload.get("excess_return", payload.get("current_excess_return")))
        if excess is None and actual is not None and benchmark is not None:
            excess = round(actual - benchmark, 6)
        return {
            "current_return": actual,
            "current_benchmark_return": benchmark,
            "current_excess_return": excess,
        }
    return {"current_return": _float_or_none(payload), "current_excess_return": None}


def _compare_window(
    window: str,
    historical_metrics: dict[str, Any],
    current_metrics: dict[str, Any],
) -> OutcomeWindowComparison:
    historical_return = historical_metrics.get("historical_return")
    current_return = current_metrics.get("current_return")
    historical_excess = historical_metrics.get("historical_excess_return")
    current_excess = current_metrics.get("current_excess_return")
    historical_direction = _direction(historical_return)
    current_direction = _direction(current_return)
    direction_match = (
        historical_direction == current_direction
        if historical_direction is not None and current_direction is not None
        else None
    )
    excess_match = (
        _sign(historical_excess) == _sign(current_excess)
        if historical_excess is not None and current_excess is not None
        else None
    )
    magnitude_gap = (
        round(abs(float(current_return) - float(historical_return)), 6)
        if historical_return is not None and current_return is not None
        else None
    )
    notes = []
    notes.extend(historical_metrics.get("notes", []))
    notes.extend(current_metrics.get("notes", []))
    if current_return is None:
        notes.append("Current outcome unavailable for this window.")
    if historical_return is None:
        notes.append("Historical outcome unavailable for this window.")
    if direction_match is False:
        notes.append("Historical and current directions differ.")
    return OutcomeWindowComparison(
        window=window,
        historical_direction=historical_direction,
        current_direction=current_direction,
        historical_return=historical_return,
        current_return=current_return,
        historical_excess_return=historical_excess,
        current_excess_return=current_excess,
        direction_match=direction_match,
        excess_return_sign_match=excess_match,
        magnitude_gap=magnitude_gap,
        notes=_unique(notes),
    )


def _matched_lessons(historical_case: HistoricalCase) -> list[str]:
    if historical_case.causal_assessment:
        return historical_case.causal_assessment.lessons[:5]
    return []


def _standard_mismatch_reasons() -> list[str]:
    return [
        "Current event status may differ from the historical case.",
        "Market may have priced in the current event before the review window.",
        "Current asset mapping may differ from the historical affected assets.",
    ]


def _current_source_hint(review_results: list[Any], market_returns: dict[str, Any]) -> str:
    if review_results:
        return "review"
    if market_returns:
        return "market"
    return "none"


def _quality_labels(
    *,
    historical_data_quality: str,
    current_data_quality: str | None,
    current_source: str,
    has_current_outcome: bool,
    has_historical_outcome: bool,
) -> dict[str, str]:
    current_quality = current_data_quality or _current_quality_from_source(current_source)
    if not has_current_outcome:
        current_quality = "missing"

    if not has_historical_outcome or not has_current_outcome:
        reliability = "insufficient"
    elif historical_data_quality == "manual_seed_demo" and current_quality == "mock_demo":
        reliability = "demo_only"
    elif historical_data_quality == "manual_seed_demo" and current_quality == "ledger_review":
        reliability = "preliminary"
    elif historical_data_quality == "verified_backtest" and current_quality == "ledger_review":
        reliability = "review_backed"
    elif historical_data_quality == "verified_backtest" and current_quality == "market_provider":
        reliability = "market_backed"
    elif current_quality == "mock_demo":
        reliability = "demo_only"
    elif current_quality in {"ledger_review", "market_provider"}:
        reliability = "preliminary"
    else:
        reliability = "preliminary"

    return {
        "current_data_quality": current_quality,
        "comparison_reliability": reliability,
    }


def _current_quality_from_source(source: str) -> str:
    if source == "review":
        return "ledger_review"
    if source == "market":
        return "market_provider"
    return "missing"


def _review_metric_float(
    review: Any,
    field: str,
    horizon: str,
    notes: list[str],
    required: bool = True,
) -> float | None:
    raw_value = _get_review_metric(review, field)
    value = _float_or_none(raw_value)
    if raw_value is None:
        if required:
            notes.append(f"Current review row missing {field} for {horizon}.")
        return None
    if value is None:
        notes.append(f"Current review row has non-numeric {field} for {horizon}.")
    return value


def _get_review_metric(payload: Any, field: str) -> Any:
    value = _get_value(payload, field)
    if value is not None:
        return value
    market_return = _get_value(payload, "market_return")
    if isinstance(market_return, dict):
        return market_return.get(field)
    return getattr(market_return, field, None)


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _direction(value: float | None) -> str | None:
    if value is None:
        return None
    if value > 0:
        return "up"
    if value < 0:
        return "down"
    return "flat"


def _sign(value: float | None) -> str | None:
    return _direction(value)


def _get_value(payload: Any, field: str) -> Any:
    if isinstance(payload, dict):
        return payload.get(field)
    return getattr(payload, field, None)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unique(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results
