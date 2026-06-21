"""Tests for daily briefing Markdown rendering and JSON writing."""

from __future__ import annotations

from datetime import date

from eventalpha.briefing import (
    BriefingItem,
    BriefingSection,
    DailyBriefing,
    JSONBriefingWriter,
    MarkdownBriefingRenderer,
)


def test_markdown_renderer_contains_sections_and_no_trading_terms() -> None:
    """Markdown should be readable and avoid trading instructions."""
    briefing = DailyBriefing(
        briefing_date=date(2026, 6, 21),
        title="EventAlpha Daily Briefing - 2026-06-21",
        sections=[
            BriefingSection(
                section_id="new_events",
                title="今日重点事件",
                items=[
                    BriefingItem(
                        item_id="1",
                        title="AI event",
                        item_type="event",
                        summary="summary",
                        risk_notes=["demo/mock signal"],
                        verification_indicators=["official filing"],
                    )
                ],
            ),
            BriefingSection(section_id="system_status", title="系统状态与风险提示", notes=["ok"]),
        ],
    )

    markdown = MarkdownBriefingRenderer().render(briefing)

    assert "# EventAlpha Daily Briefing - 2026-06-21" in markdown
    assert "今日重点事件" in markdown
    assert "风险：demo/mock signal" in markdown
    assert "验证：official filing" in markdown
    assert briefing.risk_disclaimer in markdown
    assert "买入" not in markdown
    assert "卖出" not in markdown
    assert "目标价" not in markdown


def test_json_writer_writes_markdown_and_json(tmp_path) -> None:
    """Writer should create both report formats."""
    briefing = DailyBriefing(
        briefing_date=date(2026, 6, 21),
        title="EventAlpha Daily Briefing - 2026-06-21",
        sections=[],
    )

    paths = JSONBriefingWriter(tmp_path).write(briefing)

    assert paths["markdown"].exists()
    assert paths["json"].exists()
    assert "20260621" in paths["markdown"].name
