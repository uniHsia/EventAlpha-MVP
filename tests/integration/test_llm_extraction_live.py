"""Optional live LLM extraction test."""

from __future__ import annotations

import os

import pytest

from eventalpha.agents import LLMExtractionAgent
from eventalpha.llm import OpenAICompatibleLLMClient, StructuredRunner
from eventalpha.schemas import RawNews, StructuredEvent


@pytest.mark.skipif(
    os.getenv("EVENTALPHA_RUN_LIVE_LLM") != "1" or not os.getenv("OPENAI_API_KEY"),
    reason="Live LLM extraction test requires EVENTALPHA_RUN_LIVE_LLM=1 and OPENAI_API_KEY.",
)
def test_live_llm_extraction_agent() -> None:
    """Run only when explicitly enabled by the developer."""
    raw_news = RawNews(
        title="美国宣布升级 AI 芯片出口管制",
        source="Reuters",
        source_type="mainstream_media",
        raw_text="Reuters reports that the U.S. upgraded AI chip export controls.",
    )
    agent = LLMExtractionAgent(runner=StructuredRunner(OpenAICompatibleLLMClient()))

    event = agent.extract(raw_news)

    assert isinstance(event, StructuredEvent)
    assert event.raw_id == raw_news.raw_id

