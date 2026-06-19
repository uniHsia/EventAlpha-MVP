"""Tests for optional LLM causal reasoning agent."""

from __future__ import annotations

from eventalpha.agents import LLMCausalReasoningAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.schemas import CausalChain, StructuredEvent


def _agent(responses: dict | None = None, tmp_path=None) -> LLMCausalReasoningAgent:
    return LLMCausalReasoningAgent(
        runner=StructuredRunner(
            MockLLMClient(responses=responses),
            trace_writer=LLMTraceWriter(tmp_path, enabled=True) if tmp_path else None,
        )
    )


def test_llm_causal_agent_forces_event_id_and_audit_fields(tmp_path) -> None:
    """LLM-generated audit fields should not be trusted."""
    event = StructuredEvent(
        event_id="EVT_REAL",
        event_type="ai_export_control",
        event_title="美国升级 AI 芯片出口管制",
        status="announced",
        affected_assets_hint=["国产 AI 芯片"],
    )
    raw_chain = CausalChain(
        event_id="EVT_FAKE",
        chain_id="CHAIN_FAKE",
        affected_assets=["国产 AI 芯片"],
        direction="up",
        confidence=0.8,
    ).model_dump(mode="json")
    chain = _agent({"CausalChain": raw_chain}, tmp_path).build_chain(event)

    assert chain.event_id == "EVT_REAL"
    assert chain.chain_id != "CHAIN_FAKE"
    assert chain.affected_assets == ["国产 AI 芯片"]


def test_llm_causal_agent_filters_unsupported_assets(tmp_path) -> None:
    """Unsupported assets should be filtered and warned."""
    event = StructuredEvent(
        event_id="EVT_REAL",
        event_type="ai_export_control",
        event_title="美国升级 AI 芯片出口管制",
        status="announced",
        affected_assets_hint=["国产 AI 芯片"],
    )
    raw_chain = CausalChain(
        event_id="EVT_FAKE",
        affected_assets=["国产 AI 芯片", "不存在资产"],
        direction="up",
        confidence=0.8,
    ).model_dump(mode="json")
    agent = _agent({"CausalChain": raw_chain}, tmp_path)

    chain = agent.build_chain(event)

    assert chain.affected_assets == ["国产 AI 芯片"]
    assert any("Filtered unsupported causal affected_assets" in item for item in agent.warnings)


def test_llm_causal_agent_caps_rumor_confidence(tmp_path) -> None:
    """Rumor events should not keep high causal confidence."""
    event = StructuredEvent(
        event_id="EVT_RUMOR",
        event_type="ai_export_control",
        event_title="市场传闻 AI 芯片限制升级",
        status="rumor",
        affected_assets_hint=["国产 AI 芯片"],
    )
    raw_chain = CausalChain(
        event_id="EVT_FAKE",
        affected_assets=["国产 AI 芯片"],
        direction="up",
        confidence=0.9,
    ).model_dump(mode="json")
    agent = _agent({"CausalChain": raw_chain}, tmp_path)

    chain = agent.build_chain(event)

    assert chain.confidence <= 0.55
    assert any("Reduced causal confidence" in item for item in agent.warnings)
