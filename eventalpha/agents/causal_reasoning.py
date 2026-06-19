"""Template-based mock causal reasoning agent."""

from __future__ import annotations

from eventalpha.schemas import CausalChain, CausalStep, ImpactScore, StructuredEvent


def _steps(items: list[tuple[str, str]]) -> list[CausalStep]:
    return [
        CausalStep(order=index + 1, description=description, variable_type=variable_type)
        for index, (description, variable_type) in enumerate(items)
    ]


class RuleBasedCausalReasoningAgent:
    """Thin wrapper around the deterministic causal reasoning function."""

    warnings: list[str] = []

    def build_chain(
        self,
        structured_event: StructuredEvent,
        verification=None,
        impact_score: ImpactScore | None = None,
        supported_assets: list[str] | None = None,
        extraction_warnings: list[str] | None = None,
    ) -> CausalChain:
        """Build a causal chain using the existing rule-based implementation."""
        if impact_score is None:
            raise ValueError("impact_score is required for rule-based causal reasoning")
        self.warnings = []
        return generate_causal_chain(structured_event, impact_score)


def generate_causal_chain(event: StructuredEvent, score: ImpactScore) -> CausalChain:
    """Generate a fixed causal chain by event type."""
    if event.event_type == "ai_export_control":
        return CausalChain(
            event_id=event.event_id,
            logic=_steps([
                ("出口管制升级", "policy"),
                ("海外 GPU 供应受限", "supply"),
                ("国产 AI 芯片替代预期上升", "industry"),
                ("国产服务器、先进封装、国产 EDA 受到关注", "market"),
            ]),
            affected_assets=["国产 AI 芯片", "服务器", "先进封装", "国产 EDA", "半导体设备"],
            direction="up",
            time_horizon="T+3",
            confidence=0.78,
            rationale="出口限制可能强化国产替代叙事，但二阶设备端需要资本开支验证。",
        )

    if event.event_type == "geopolitical_conflict":
        return CausalChain(
            event_id=event.event_id,
            logic=_steps([
                ("冲突升级", "geopolitical"),
                ("原油供应不确定性上升", "commodity"),
                ("油价风险溢价抬升", "commodity"),
                ("油气和黄金短期受到关注", "market"),
            ]),
            affected_assets=["原油", "黄金", "油气"],
            direction="mixed",
            time_horizon="T+3",
            confidence=0.72,
            rationale="能源供给和避险情绪是主要传导路径。",
        )

    if event.event_type == "rate_policy":
        return CausalChain(
            event_id=event.event_id,
            logic=_steps([
                ("利率政策变化", "macro"),
                ("流动性和贴现率预期变化", "macro"),
                ("权益估值和汇率反应变化", "market"),
            ]),
            affected_assets=["成长风格指数", "债券", "汇率"],
            direction="mixed",
            time_horizon="T+3",
            confidence=0.60,
            rationale="利率政策影响方向取决于政策措辞和市场预期差。",
        )

    return CausalChain(
        event_id=event.event_id,
        logic=_steps([
            ("事件发生", "event"),
            ("相关市场变量变化", "market"),
            ("需要后续数据验证", "verification"),
        ]),
        affected_assets=event.affected_assets_hint,
        direction="mixed",
        time_horizon="T+3",
        confidence=0.45,
        rationale="未分类事件仅保留观察链条。",
    )
