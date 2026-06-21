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
            for warning in briefing.warnings[:3]:
                lines.append(f"- {warning}")
            lines.append("")

        for index, section in enumerate(briefing.sections, start=1):
            lines.extend([f"## {index}. {section.title}", ""])
            for note in section.notes:
                lines.append(f"- {note}")
            if section.notes:
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
    for detail in _metadata_details(item) + item.details[:4]:
        lines.append(f"  - {detail}")
    for risk in item.risk_notes[:3]:
        lines.append(f"  - 风险：{risk}")
    for verification in item.verification_indicators[:3]:
        lines.append(f"  - 验证：{verification}")
    for source in item.source_refs[:3]:
        lines.append(f"  - 来源：{source}")
    return lines


def _metadata_details(item: BriefingItem) -> list[str]:
    details: list[str] = []
    duplicate_count = int(item.metadata.get("duplicate_count") or 0)
    if duplicate_count > 1 and not any("duplicate_count" in detail for detail in item.details):
        details.append(f"duplicate_count={duplicate_count}, showing latest only")
    count = int(item.metadata.get("count") or 0)
    if count > 1 and not any("count=" in detail for detail in item.details):
        details.append(f"count={count}")
    return details
