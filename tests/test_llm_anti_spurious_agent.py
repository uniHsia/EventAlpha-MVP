"""Tests for optional LLM anti-spurious agent."""

from __future__ import annotations

from eventalpha.agents import LLMAntiSpuriousAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.schemas import AntiSpuriousCheck, CausalChain, StructuredEvent


def _agent(responses: dict | None = None, tmp_path=None) -> LLMAntiSpuriousAgent:
    return LLMAntiSpuriousAgent(
        runner=StructuredRunner(
            MockLLMClient(responses=responses),
            trace_writer=LLMTraceWriter(tmp_path, enabled=True) if tmp_path else None,
        )
    )


def test_llm_anti_spurious_forces_event_and_chain_ids(tmp_path) -> None:
    """LLM-generated audit IDs should not be trusted."""
    event = StructuredEvent(event_id="EVT_REAL", event_type="ai_export_control")
    chain = CausalChain(
        chain_id="CHAIN_REAL",
        event_id="EVT_REAL",
        affected_assets=["国产 AI 芯片"],
        confidence=0.8,
    )
    raw_check = AntiSpuriousCheck(
        event_id="EVT_FAKE",
        chain_id="CHAIN_FAKE",
        issues=["二阶映射需要验证"],
        required_verifications=["检查订单和招标"],
        adjusted_confidence=0.7,
    ).model_dump(mode="json")

    check = _agent({"AntiSpuriousCheck": raw_check}, tmp_path).check(event, chain)

    assert check.event_id == "EVT_REAL"
    assert check.chain_id == "CHAIN_REAL"
    assert check.check_id != raw_check["check_id"]


def test_llm_anti_spurious_rumor_caps_adjusted_confidence(tmp_path) -> None:
    """Rumor events should not retain high adjusted confidence."""
    event = StructuredEvent(
        event_id="EVT_RUMOR",
        event_type="ai_export_control",
        status="rumor",
    )
    chain = CausalChain(
        chain_id="CHAIN_REAL",
        event_id="EVT_RUMOR",
        affected_assets=["国产 AI 芯片"],
        confidence=0.9,
    )
    raw_check = AntiSpuriousCheck(
        event_id="EVT_FAKE",
        chain_id="CHAIN_FAKE",
        spurious_risk="low",
        issues=["传闻事件需要确认"],
        required_verifications=["确认官方文件"],
        adjusted_confidence=0.9,
    ).model_dump(mode="json")
    agent = _agent({"AntiSpuriousCheck": raw_check}, tmp_path)

    check = agent.check(event, chain)

    assert check.adjusted_confidence <= 0.55
    assert check.spurious_risk == "medium"
    assert any("Reduced adjusted_confidence" in item for item in agent.warnings)


def test_llm_anti_spurious_adds_required_verification_for_issues(tmp_path) -> None:
    """Issues without required verification should be repaired for auditability."""
    event = StructuredEvent(event_id="EVT_REAL", event_type="ai_export_control")
    chain = CausalChain(chain_id="CHAIN_REAL", event_id="EVT_REAL", confidence=0.8)
    raw_check = AntiSpuriousCheck(
        event_id="EVT_FAKE",
        chain_id="CHAIN_FAKE",
        issues=["链条从事件直接跳到资产"],
        required_verifications=[],
        adjusted_confidence=0.7,
    ).model_dump(mode="json")
    agent = _agent({"AntiSpuriousCheck": raw_check}, tmp_path)

    check = agent.check(event, chain)

    assert check.required_verifications
    assert any("issues but no required verifications" in item for item in agent.warnings)
