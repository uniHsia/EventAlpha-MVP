"""Credibility source classification tests."""

from __future__ import annotations

from eventalpha.agents import extract_event, verify_event
from eventalpha.schemas import RawNews


def test_reuters_with_announcement_text_is_not_official_source() -> None:
    """Reuters text containing '公告' should remain a media source."""
    raw_news = RawNews(
        title="美国宣布升级 AI 芯片出口管制",
        source="Reuters",
        source_type="mainstream_media",
        raw_text="Reuters 报道，美国发布公告宣布升级 AI 芯片出口管制。",
    )
    event = extract_event(raw_news)
    verification = verify_event(raw_news, event)
    evidence_types = {item["type"] for item in verification.evidence}

    assert verification.source_classification in {"mainstream_media", "recognized_media"}
    assert verification.content_contains_official_claim is True
    assert "official_source" not in evidence_types
    assert "official_keyword" not in evidence_types


def test_official_institution_source_can_be_official_source() -> None:
    """Official institution source should be classified as official_source."""
    raw_news = RawNews(
        title="中国人民银行发布公告宣布降息",
        source="中国人民银行",
        source_type="official",
        raw_text="中国人民银行公告宣布下调政策利率。",
    )
    event = extract_event(raw_news)
    verification = verify_event(raw_news, event)

    assert verification.source_classification == "official_source"
    assert verification.content_contains_official_claim is True
    assert any(item["type"] == "official_source" for item in verification.evidence)
