"""Tests for Chinese EventCard display text."""

from __future__ import annotations

from eventalpha.agents.card_generation import generate_event_card
from eventalpha.schemas import (
    AntiSpuriousCheck,
    CausalChain,
    CausalStep,
    EventVerification,
    ImpactScore,
    MappedAsset,
    MarketMapping,
    RISK_DISCLAIMER,
    RawNews,
    StructuredEvent,
)


def test_event_card_uses_chinese_display_templates() -> None:
    """EventCard user-facing summary and impact templates should stay Chinese."""
    raw_news = RawNews(raw_text="政策公告正文", source="官方公告", source_type="official")
    event = StructuredEvent(
        event_id="EVT_CN",
        event_title="政策事件",
        summary="政策事件摘要",
        affected_industries=["能源", "航运"],
    )
    verification = EventVerification(
        event_id="EVT_CN",
        credibility_score=0.82,
        verification_status="confirmed",
    )
    score = ImpactScore(event_id="EVT_CN", event_level="A", impact_score=80)
    chain = CausalChain(
        event_id="EVT_CN",
        logic=[
            CausalStep(order=1, description="政策发布"),
            CausalStep(order=2, description="供需变化"),
        ],
    )
    anti_spurious = AntiSpuriousCheck(
        event_id="EVT_CN",
        chain_id=chain.chain_id,
        adjusted_confidence=0.6,
    )
    mapping = MarketMapping(
        event_id="EVT_CN",
        mapped_assets=[
            MappedAsset(asset_name="能源", relation="direct_beneficiary", direction="up"),
            MappedAsset(asset_name="航运", relation="cost_pressure", direction="down"),
            MappedAsset(asset_name="黄金", relation="watch", direction="watch"),
        ],
    )

    card = generate_event_card(
        raw_news=raw_news,
        event=event,
        verification=verification,
        score=score,
        chain=chain,
        anti_spurious=anti_spurious,
        mapping=mapping,
    )
    impacts_text = " ".join(card.possible_impacts)

    assert "may affect" not in card.one_sentence
    assert "follow-up" not in card.one_sentence
    assert "possible upside" not in impacts_text
    assert "needs observation" not in impacts_text
    assert "可能影响" in card.one_sentence
    assert "仍需结合后续市场数据验证" in card.one_sentence
    assert "可能受益或受到市场关注" in impacts_text
    assert "需要继续观察" in impacts_text
    assert RISK_DISCLAIMER in card.risk_disclaimer
