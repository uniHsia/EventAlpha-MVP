"""Readable summaries for historical case search results."""

from __future__ import annotations

from eventalpha.schemas import RISK_DISCLAIMER

from .schemas import HistoricalCase


def summarize_case(historical_case: HistoricalCase) -> str:
    """Return a concise human-readable case summary."""
    lines = [
        f"- {historical_case.title}",
        f"  event_type={historical_case.event_type}",
    ]
    if historical_case.event_date:
        lines.append(f"  event_date={historical_case.event_date.isoformat()}")
    if historical_case.affected_assets:
        lines.append(f"  affected_assets={', '.join(historical_case.affected_assets)}")
    if historical_case.outcome and historical_case.outcome.market_reaction_summary:
        lines.append(f"  outcome={historical_case.outcome.market_reaction_summary}")
        lines.append(f"  outcome_quality={historical_case.outcome.outcome_quality}")
    if historical_case.causal_assessment:
        lines.append(f"  causal_validity={historical_case.causal_assessment.causal_validity}")
        if historical_case.causal_assessment.lessons:
            lines.append(f"  lessons={' | '.join(historical_case.causal_assessment.lessons)}")
    return "\n".join(lines)


def summarize_search_results(cases: list[HistoricalCase]) -> str:
    """Return a report for a list of matched historical cases."""
    if not cases:
        return f"No matching historical cases found.\n\n{RISK_DISCLAIMER}"
    sections = ["Historical Case Matches"]
    sections.extend(summarize_case(historical_case) for historical_case in cases)
    sections.append(RISK_DISCLAIMER)
    return "\n\n".join(sections)
