"""Readable explanations for historical analogies."""

from __future__ import annotations

from eventalpha.schemas import RISK_DISCLAIMER

from .analogy import HistoricalAnalogy


class HistoricalAnalogyExplainer:
    """Render historical analogies into human-readable text."""

    def explain(self, analogy: HistoricalAnalogy) -> str:
        """Explain one analogy."""
        sections = [
            f"- {analogy.historical_case_title}",
            f"  overall_score={analogy.overall_score:.2f}",
            f"  strength_label={analogy.strength_label}",
            "  input_context=" + _format_input_context(analogy),
            f"  low_score_explanation={analogy.low_score_explanation or 'none'}",
            "  dimension_scores="
            + ", ".join(f"{score.dimension}:{score.score:.2f}" for score in analogy.dimension_scores),
            "  similarities=" + _join(analogy.similarities),
            "  differences=" + _join(analogy.differences),
            "  transferable_lessons=" + _join(analogy.transferable_lessons),
            "  non_transferable_lessons=" + _join(analogy.non_transferable_lessons),
            "  verification_suggestions=" + _join(analogy.verification_suggestions),
            "  risk_notes=" + _join(analogy.risk_notes),
        ]
        return "\n".join(sections)

    def explain_many(self, analogies: list[HistoricalAnalogy]) -> str:
        """Explain a list of analogies."""
        if not analogies:
            return f"No historical analogies found.\n\n{RISK_DISCLAIMER}"
        sections = ["Historical Analogy Matches"]
        sections.extend(self.explain(analogy) for analogy in analogies)
        sections.append(RISK_DISCLAIMER)
        return "\n\n".join(sections)


def _join(values: list[str]) -> str:
    return " | ".join(values) if values else "none"


def _format_input_context(analogy: HistoricalAnalogy) -> str:
    context = analogy.input_context
    if not context:
        return "none"
    return (
        f"{context.context_label}; "
        f"provided={','.join(context.provided_dimensions) or 'none'}; "
        f"missing={','.join(context.missing_dimensions) or 'none'}; "
        f"completeness={context.context_completeness_score:.3f}"
    )
