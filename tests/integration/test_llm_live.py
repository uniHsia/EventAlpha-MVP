"""Optional live LLM integration test."""

from __future__ import annotations

import os

import pytest

from eventalpha.llm import OpenAICompatibleLLMClient
from eventalpha.schemas import StructuredEvent


@pytest.mark.skipif(
    os.getenv("EVENTALPHA_RUN_LIVE_LLM") != "1" or not os.getenv("OPENAI_API_KEY"),
    reason="Live LLM test requires EVENTALPHA_RUN_LIVE_LLM=1 and OPENAI_API_KEY.",
)
def test_live_llm_structured_event() -> None:
    """Run only when explicitly enabled by the developer."""
    client = OpenAICompatibleLLMClient()
    event = client.generate_structured(
        "Extract a StructuredEvent for: Reuters reports an AI chip export control update.",
        StructuredEvent,
    )

    assert isinstance(event, StructuredEvent)

