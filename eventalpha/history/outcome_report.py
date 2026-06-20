"""Text reports for historical outcome comparisons."""

from __future__ import annotations

from eventalpha.schemas import RISK_DISCLAIMER

from .outcome_comparison import HistoricalOutcomeComparison


class HistoricalOutcomeReportBuilder:
    """Render historical outcome comparisons into readable text."""

    def build_text_report(self, comparisons: list[HistoricalOutcomeComparison]) -> str:
        """Build a plain-text report for outcome comparisons."""
        if not comparisons:
            return f"No historical outcome comparisons found.\n\n{RISK_DISCLAIMER}"
        sections = ["Historical Outcome Comparison Report"]
        sections.extend(_format_comparison(comparison) for comparison in comparisons)
        sections.append(RISK_DISCLAIMER)
        return "\n\n".join(sections)


def _format_comparison(comparison: HistoricalOutcomeComparison) -> str:
    lines = [
        f"- {comparison.historical_case_title}",
        f"  comparison_status={comparison.comparison_status}",
        f"  analogy_score={_fmt(comparison.analogy_score)}",
        f"  analogy_strength={comparison.analogy_strength_label or 'none'}",
        f"  outcome_quality={comparison.outcome_quality or 'none'}",
        f"  historical_data_quality={comparison.historical_data_quality}",
        f"  current_data_quality={comparison.current_data_quality}",
        f"  comparison_reliability={comparison.comparison_reliability}",
        f"  scenario_name={comparison.scenario_name or 'none'}",
    ]
    if (
        comparison.historical_data_quality == "manual_seed_demo"
        or comparison.current_data_quality == "mock_demo"
        or comparison.comparison_reliability == "demo_only"
    ):
        lines.append(
            "  demo_warning=Manual seed and mock outcome values are deterministic demo data, "
            "not verified market returns or investment evidence."
        )
    lines.append("  windows=")
    for window in comparison.window_comparisons:
        lines.append(
            "    "
            + (
                f"{window.window}: historical_return={_fmt(window.historical_return)}, "
                f"current_return={_fmt(window.current_return)}, "
                f"historical_excess_return={_fmt(window.historical_excess_return)}, "
                f"current_excess_return={_fmt(window.current_excess_return)}, "
                f"historical_direction={window.historical_direction or 'none'}, "
                f"current_direction={window.current_direction or 'none'}, "
                f"direction_match={window.direction_match}, "
                f"excess_return_sign_match={window.excess_return_sign_match}, "
                f"magnitude_gap={_fmt(window.magnitude_gap)}"
            )
        )
        if window.notes:
            lines.append(f"      notes={_join(window.notes)}")
    lines.extend(
        [
            "  matched_lessons=" + _join(comparison.matched_lessons),
            "  mismatch_reasons=" + _join(comparison.mismatch_reasons),
            "  validation_notes=" + _join(comparison.validation_notes),
            "  risk_notes=" + _join(comparison.risk_notes),
        ]
    )
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "none" if value is None else f"{value:.4f}"


def _join(values: list[str]) -> str:
    return " | ".join(values) if values else "none"
