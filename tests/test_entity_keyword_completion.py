"""Tests for event-type-specific entity keyword completion."""

from __future__ import annotations

from eventalpha.services import EntityKeywordCompletionService


def test_entity_keyword_completion_adds_explicit_trade_terms() -> None:
    """Trade tariff keywords should be completed only when present in raw text."""
    service = EntityKeywordCompletionService()

    completed = service.complete_entities(
        event_type="trade_tariff",
        existing_entities=[],
        raw_title="美国宣布对部分进口商品加征关税",
        raw_text="本次贸易政策调整将影响部分出口链企业。",
    )

    assert "美国" in completed
    assert "关税" in completed
    assert "加征关税" in completed
    assert "贸易" in completed
    assert "进口商品" in completed
    assert "出口链" in completed
    assert "进口替代" not in completed
    assert service.warnings


def test_entity_keyword_completion_does_not_invent_absent_terms() -> None:
    """Absent keywords should not be added."""
    service = EntityKeywordCompletionService()

    completed = service.complete_entities(
        event_type="geopolitical_conflict",
        existing_entities=["中东"],
        raw_title="中东局势紧张",
        raw_text="市场关注区域冲突的后续变化。",
    )

    assert completed == ["中东", "冲突"]
    assert "原油" not in completed
    assert "黄金" not in completed


def test_entity_keyword_completion_handles_compact_text() -> None:
    """Whitespace differences should not block matching."""
    service = EntityKeywordCompletionService()

    completed = service.complete_entities(
        event_type="ai_export_control",
        existing_entities=[],
        raw_title="美国商务部扩大AI芯片出口管制",
        raw_text="GPU和服务器供应链受到关注。",
    )

    assert "AI 芯片" in completed
    assert "GPU" in completed
    assert "服务器" in completed
    assert "出口管制" in completed
