"""Tests for LLM causal strict/fallback behavior."""

from __future__ import annotations

import pytest

from eventalpha.agents import LLMCausalReasoningAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.llm.errors import LLMOutputValidationError
from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews, StructuredEvent


def _agent(failure_mode: str, tmp_path) -> LLMCausalReasoningAgent:
    return LLMCausalReasoningAgent(
        runner=StructuredRunner(
            MockLLMClient(responses={"CausalChain": "{not valid json"}),
            trace_writer=LLMTraceWriter(tmp_path, enabled=True),
        ),
        failure_mode=failure_mode,  # type: ignore[arg-type]
    )


def test_llm_causal_strict_raises_validation_error(tmp_path) -> None:
    """Strict mode should raise invalid structured output."""
    event = StructuredEvent(
        event_type="ai_export_control",
        affected_assets_hint=["国产 AI 芯片"],
    )

    with pytest.raises(LLMOutputValidationError):
        _agent("strict", tmp_path).build_chain(event)


def test_llm_causal_fallback_returns_rule_based_chain(tmp_path) -> None:
    """Fallback mode should use rule-based causal chain and expose warnings."""
    raw_news = RawNews(
        title="美国升级 AI 芯片出口管制",
        source="Reuters",
        source_type="mainstream_media",
        raw_text="Reuters 报道，美国宣布升级 AI 芯片和 GPU 出口管制。",
    )

    result = run_event_pipeline(raw_news, persist=False, causal_agent=_agent("fallback", tmp_path))

    assert result["causal_chain"].event_id == result["structured_event"].event_id
    assert result["causal_warnings"]
    assert "fell back to rule-based causal chain" in result["causal_warnings"][0]
