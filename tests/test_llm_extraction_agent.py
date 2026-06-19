"""Tests for LLMExtractionAgent."""

from __future__ import annotations

import json
from pathlib import Path

from eventalpha.agents import LLMExtractionAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.schemas import RawNews, StructuredEvent


def _raw_news() -> RawNews:
    fixture = Path(__file__).parent / "fixtures" / "demo_events.json"
    return RawNews(**json.loads(fixture.read_text(encoding="utf-8"))[0])


def test_llm_extraction_agent_returns_structured_event_and_preserves_raw_id(tmp_path) -> None:
    """Mock LLM extraction should produce a validated StructuredEvent."""
    raw_news = _raw_news()
    runner = StructuredRunner(
        MockLLMClient(),
        trace_writer=LLMTraceWriter(tmp_path, enabled=True),
    )
    agent = LLMExtractionAgent(runner=runner)

    event = agent.extract(raw_news)

    assert isinstance(event, StructuredEvent)
    assert event.raw_id == raw_news.raw_id
    assert event.event_type == "ai_export_control"
    assert agent.warnings == []
    assert list(tmp_path.glob("*.jsonl"))

