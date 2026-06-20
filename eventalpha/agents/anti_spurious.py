"""Mock anti-spurious reasoning agent."""

from __future__ import annotations

from eventalpha.schemas import AntiSpuriousCheck, CausalChain, StructuredEvent


def check_spurious_reasoning(event: StructuredEvent, chain: CausalChain) -> AntiSpuriousCheck:
    """Check for weak links, long chains, and second-order mappings."""
    issues: list[str] = []
    required: list[str] = []

    if len(chain.logic) > 4:
        issues.append("因果链条较长，部分影响可能属于二阶传导")
        required.append("验证每一层变量是否实际发生")

    if "半导体设备" in chain.affected_assets:
        issues.append("半导体设备属于二阶映射，短期反应需要资本开支信号支持")
        required.append("检查晶圆厂扩产、设备订单或政策资金信号")

    if event.event_type == "earthquake_supply_chain":
        issues.append("供应链替代能力需要事实验证，不能仅凭地震直接外推")
        required.append("确认受灾区域是否有关键产能停产")

    if not chain.affected_assets:
        issues.append("缺少明确可观察资产映射")
        required.append("补充行业、指数或主题方向映射")

    if not issues:
        risk = "low"
        adjusted = chain.confidence
    elif len(issues) == 1:
        risk = "medium"
        adjusted = max(0.0, round(chain.confidence - 0.12, 2))
    else:
        risk = "high"
        adjusted = max(0.0, round(chain.confidence - 0.25, 2))

    return AntiSpuriousCheck(
        event_id=event.event_id,
        chain_id=chain.chain_id,
        spurious_risk=risk,
        issues=issues,
        required_verifications=required,
        adjusted_confidence=adjusted,
    )


class RuleBasedAntiSpuriousAgent:
    """Thin wrapper around the deterministic anti-spurious checker."""

    warnings: list[str] = []

    def check(
        self,
        structured_event: StructuredEvent,
        causal_chain: CausalChain,
        verification=None,
        impact_score=None,
        market_mapping=None,
        extraction_warnings: list[str] | None = None,
        causal_warnings: list[str] | None = None,
        supported_assets: list[str] | None = None,
    ) -> AntiSpuriousCheck:
        """Run the existing rule-based anti-spurious check."""
        self.warnings = []
        return check_spurious_reasoning(structured_event, causal_chain)
