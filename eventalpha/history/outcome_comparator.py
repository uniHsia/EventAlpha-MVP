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
    ) -> HistoricalOutcomeComparison:
        """Build a deterministic historical-current outcome comparison."""
        current_review_results = current_review_results or []
        current_market_returns = current_market_returns or {}
        historical_outcome = historical_case.outcome
        outcome_quality = historical_outcome.outcome_quality if historical_outcome else None
        windows = historical_outcome.time_windows if historical_outcome else DEFAULT_OUTCOME_WINDOWS
        risk_notes = ["Historical outcome comparison is a research aid and not investment advice."]
        validation_notes: list[str] = []
        mismatch_reasons: list[str] = []

        if outcome_quality == "manual_seed_demo":
            risk_notes.append(MANUAL_SEED_RISK_NOTE)
            validation_notes.append("Historical outcome is an MVP seed example and must not be treated as real return validation.")
            mismatch_reasons.append("Historical case is seed demo data, so any match is illustrative only.")

        if not historical_outcome:
            return self._comparison(
                analogy=analogy,
                historical_case=historical_case,
                outcome_quality=outcome_quality,
                status="missing_historical_outcome",
                windows=windows,
                mismatch_reasons=["Historical case has no outcome data."],
                validation_notes=["Add historical outcome windows before comparing this analogy."],
                risk_notes=risk_notes,
            )

        historical_returns = _historical_window_returns(historical_outcome.asset_returns, windows)
        current_returns = _current_window_returns(current_review_results, current_market_returns, windows)
        has_current_outcome = any(metrics.get("current_return") is not None for metrics in current_returns.values())

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
        status: str,
        windows: list[str],
        historical_returns: dict[str, dict[str, float | None]] | None = None,
        current_returns: dict[str, dict[str, float | None]] | None = None,
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
) -> dict[str, dict[str, float | None]]:
    results: dict[str, dict[str, float | None]] = {}
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
) -> dict[str, dict[str, float | None]]:
    review_metrics = _review_window_returns(review_results, windows)
    if any(metrics.get("current_return") is not None for metrics in review_metrics.values()):
        return review_metrics
    return _market_window_returns(market_returns, windows)


def _review_window_returns(review_results: list[Any], windows: list[str]) -> dict[str, dict[str, float | None]]:
    grouped: dict[str, dict[str, list[float]]] = {
        window: {"actual_return": [], "benchmark_return": [], "excess_return": []}
        for window in windows
    }
    for review in review_results:
        horizon = _get_value(review, "horizon")
        if horizon not in grouped:
            continue
        for field in ["actual_return", "benchmark_return", "excess_return"]:
            value = _get_value(review, field)
            if value is not None:
                grouped[horizon][field].append(float(value))
    return {
        window: {
            "current_return": _average(values["actual_return"]),
            "current_benchmark_return": _average(values["benchmark_return"]),
            "current_excess_return": _average(values["excess_return"]),
        }
        for window, values in grouped.items()
    }


def _market_window_returns(market_returns: dict[str, Any], windows: list[str]) -> dict[str, dict[str, float | None]]:
    if not market_returns:
        return {window: {"current_return": None, "current_excess_return": None} for window in windows}
    if any(window in market_returns for window in windows):
        return {
            window: _direct_market_metrics(market_returns.get(window))
            for window in windows
        }
    results: dict[str, dict[str, float | None]] = {}
    for window in windows:
        values = []
        for asset_payload in market_returns.values():
            if isinstance(asset_payload, dict) and asset_payload.get(window) is not None:
                values.append(float(asset_payload[window]))
        results[window] = {"current_return": _average(values), "current_excess_return": None}
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
    historical_metrics: dict[str, float | None],
    current_metrics: dict[str, float | None],
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
        notes=notes,
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
    return float(value)


def _unique(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        results.append(value)
    return results
