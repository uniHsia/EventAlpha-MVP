"""Tests for event pipeline with injected LLM anti-spurious critic."""

from __future__ import annotations

from eventalpha.agents import LLMAntiSpuriousAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews


def test_event_pipeline_with_llm_anti_spurious_generates_outputs(tmp_path) -> None:
    """Injected LLM critic should not break downstream pipeline outputs."""
    raw_news = RawNews(
        title="美国升级 AI 芯片出口管制",
        source="Reuters",
        source_type="mainstream_media",
        raw_text="Reuters 报道，美国宣布升级 AI 芯片和 GPU 出口管制。",
    )
    agent = LLMAntiSpuriousAgent(
        runner=StructuredRunner(
            MockLLMClient(),
            trace_writer=LLMTraceWriter(tmp_path, enabled=True),
        )
    )

    result = run_event_pipeline(raw_news, persist=False, anti_spurious_agent=agent)

    assert result["anti_spurious_check"].event_id == result["structured_event"].event_id
    assert result["anti_spurious_check"].chain_id == result["causal_chain"].chain_id
    assert result["event_card"].event_id == result["structured_event"].event_id
    assert result["prediction_ledger_entry"].event_id == result["structured_event"].event_id
    assert "anti_spurious_warnings" in result
