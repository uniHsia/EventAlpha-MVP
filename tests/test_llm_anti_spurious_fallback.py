"""Tests for LLM anti-spurious strict/fallback behavior."""

from __future__ import annotations

import pytest

from eventalpha.agents import LLMAntiSpuriousAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.llm.errors import LLMOutputValidationError
from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import CausalChain, RawNews, StructuredEvent


def _agent(failure_mode: str, tmp_path) -> LLMAntiSpuriousAgent:
    return LLMAntiSpuriousAgent(
        runner=StructuredRunner(
            MockLLMClient(responses={"AntiSpuriousCheck": "{not valid json"}),
            trace_writer=LLMTraceWriter(tmp_path, enabled=True),
        ),
        failure_mode=failure_mode,  # type: ignore[arg-type]
    )


def test_llm_anti_spurious_strict_raises_validation_error(tmp_path) -> None:
    """Strict mode should raise invalid structured output."""
    event = StructuredEvent(event_type="ai_export_control")
    chain = CausalChain(event_id=event.event_id)

    with pytest.raises(LLMOutputValidationError):
        _agent("strict", tmp_path).check(event, chain)


def test_llm_anti_spurious_fallback_returns_rule_based_check(tmp_path) -> None:
    """Fallback mode should use rule-based anti-spurious and expose warnings."""
    raw_news = RawNews(
        title="美国升级 AI 芯片出口管制",
        source="Reuters",
        source_type="mainstream_media",
        raw_text="Reuters 报道，美国宣布升级 AI 芯片和 GPU 出口管制。",
    )

    result = run_event_pipeline(
        raw_news,
        persist=False,
        anti_spurious_agent=_agent("fallback", tmp_path),
    )

    assert result["anti_spurious_check"].event_id == result["structured_event"].event_id
    assert result["anti_spurious_warnings"]
    assert "fell back to rule-based anti-spurious" in result["anti_spurious_warnings"][0]
