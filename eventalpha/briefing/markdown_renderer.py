"""Markdown rendering for daily briefings."""

from __future__ import annotations

from .schemas import BriefingItem, DailyBriefing


class MarkdownBriefingRenderer:
    """Render a DailyBriefing as compact Markdown."""

    def render(self, briefing: DailyBriefing) -> str:
        """Return Markdown text."""
        lines = [
            f"# {briefing.title}",
            "",
            f"> {briefing.risk_disclaimer}",
            "",
        ]
        if briefing.warnings:
            lines.extend(["## Warnings", ""])
            for warning in _dedupe(briefing.warnings):
                lines.append(f"- {warning}")
            lines.append("")

        for index, section in enumerate(briefing.sections, start=1):
            lines.extend([f"## {index}. {section.title}", ""])
            if section.notes:
                for note in _dedupe(section.notes):
                    lines.append(f"- {note}")
                lines.append("")
            if section.items:
                for item in section.items:
                    lines.extend(_render_item(item))
                lines.append("")
            elif not section.notes:
                lines.extend(["- 暂无数据。", ""])
        return "\n".join(lines).strip() + "\n"


def _render_item(item: BriefingItem) -> list[str]:
    lines = [f"- **{item.title}** `{item.priority}`"]
    if item.summary:
        lines.append(f"  - {item.summary}")
    for detail in item.details[:4]:
        lines.append(f"  - {detail}")
    for risk in item.risk_notes[:3]:
        lines.append(f"  - Risk: {risk}")
    for verification in item.verification_indicators[:3]:
        lines.append(f"  - Verify: {verification}")
    for source in item.source_refs[:3]:
        lines.append(f"  - Source: {source}")
    return lines


def _dedupe(values: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results
