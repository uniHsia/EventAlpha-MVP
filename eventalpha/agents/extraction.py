"""Rule-based mock event extraction agent."""

from __future__ import annotations

from eventalpha.schemas import RawNews, StructuredEvent


class RuleBasedExtractionAgent:
    """Thin class wrapper around the existing rule-based extractor."""

    def extract(self, raw_news: RawNews) -> StructuredEvent:
        """Extract a structured event using the existing keyword rules."""
        return extract_event(raw_news)


def extract_event(raw_news: RawNews) -> StructuredEvent:
    """Extract a structured event from raw text using keyword rules."""
    text = f"{raw_news.title} {raw_news.raw_text}"
    event_time = raw_news.publish_time

    if any(k in text for k in ["AI 芯片", "人工智能芯片", "出口管制", "GPU", "先进芯片"]):
        return StructuredEvent(
            raw_id=raw_news.raw_id,
            event_type="ai_export_control",
            event_title=raw_news.title or "AI 芯片出口管制升级",
            summary="AI 芯片相关出口管制升级，可能影响国产替代和算力产业链关注度。",
            entities=["美国", "中国", "AI 芯片", "GPU"],
            locations=["美国", "中国"],
            event_time=event_time,
            status="announced",
            affected_industries=["半导体", "AI 算力", "服务器", "先进封装"],
            affected_assets_hint=["国产 AI 芯片", "服务器", "先进封装", "国产 EDA"],
            novelty_score=0.82,
        )

    if any(k in text for k in ["中东冲突", "战争", "武装冲突", "原油", "地缘"]):
        return StructuredEvent(
            raw_id=raw_news.raw_id,
            event_type="geopolitical_conflict",
            event_title=raw_news.title or "地缘冲突升级",
            summary="地缘冲突可能影响能源供给、避险情绪和全球风险偏好。",
            entities=["中东", "原油", "黄金"],
            locations=["中东"],
            event_time=event_time,
            status="announced",
            affected_industries=["能源", "贵金属", "航空", "化工"],
            affected_assets_hint=["原油", "黄金", "油气", "航空"],
            novelty_score=0.75,
        )

    if any(k in text for k in ["降息", "加息", "美联储", "央行", "利率"]):
        return StructuredEvent(
            raw_id=raw_news.raw_id,
            event_type="rate_policy",
            event_title=raw_news.title or "央行利率政策变化",
            summary="利率政策变化可能影响流动性、汇率、估值和风险偏好。",
            entities=["央行", "利率"],
            locations=[],
            event_time=event_time,
            status="announced",
            affected_industries=["权益市场", "债券", "汇率"],
            affected_assets_hint=["成长风格指数", "债券", "汇率"],
            novelty_score=0.70,
        )

    if any(k in text for k in ["关税", "贸易", "进口限制", "出口限制"]):
        return StructuredEvent(
            raw_id=raw_news.raw_id,
            event_type="trade_tariff",
            event_title=raw_news.title or "贸易关税政策变化",
            summary="贸易政策变化可能影响出口链、进口替代和成本传导。",
            entities=["关税", "贸易"],
            locations=[],
            event_time=event_time,
            status="announced",
            affected_industries=["出口链", "进口替代", "制造业"],
            affected_assets_hint=["出口链", "进口替代主题"],
            novelty_score=0.72,
        )

    if any(k in text for k in ["地震", "供应链", "停产", "工厂"]):
        return StructuredEvent(
            raw_id=raw_news.raw_id,
            event_type="earthquake_supply_chain",
            event_title=raw_news.title or "地震引发供应链扰动",
            summary="自然灾害可能影响局部产能和供应链替代预期。",
            entities=["地震", "供应链"],
            locations=[],
            event_time=event_time,
            status="happened",
            affected_industries=["供应链", "制造业"],
            affected_assets_hint=["供应链替代主题"],
            novelty_score=0.60,
        )

    return StructuredEvent(
        raw_id=raw_news.raw_id,
        event_type="unknown",
        event_title=raw_news.title or "未分类事件",
        summary=raw_news.raw_text[:160],
        event_time=event_time,
        status="unknown",
        novelty_score=0.40,
    )
