"""Tests for StructuredRunner retry, repair, and tracing."""

from __future__ import annotations

import pytest

from eventalpha.llm import LLMOutputValidationError, LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.schemas import StructuredEvent


def test_structured_runner_accepts_valid_json(tmp_path) -> None:
    """Runner should return validated output and write a success trace."""
    trace_writer = LLMTraceWriter(tmp_path, enabled=True)
    runner = StructuredRunner(MockLLMClient(), trace_writer=trace_writer)

    event = runner.run("extract", StructuredEvent, prompt_name="test_prompt")

    assert event.event_type == "ai_export_control"
    trace_files = list(tmp_path.glob("*.jsonl"))
    assert trace_files
    assert '"success": true' in trace_files[0].read_text(encoding="utf-8")


def test_structured_runner_repairs_after_first_invalid_output(tmp_path) -> None:
    """A fail-first mock should pass on retry."""
    client = MockLLMClient(fail_first=True)
    runner = StructuredRunner(client, trace_writer=LLMTraceWriter(tmp_path, enabled=True))

    event = runner.run("extract", StructuredEvent, max_retries=1)

    assert event.event_type == "ai_export_control"
    assert client.call_counts["StructuredEvent"] == 2


def test_structured_runner_raises_after_retry_exhausted(tmp_path) -> None:
    """Repeated invalid output should raise and trace failure."""
    client = MockLLMClient(responses={"StructuredEvent": "{bad json"})
    runner = StructuredRunner(client, trace_writer=LLMTraceWriter(tmp_path, enabled=True))

    with pytest.raises(LLMOutputValidationError):
        runner.run("extract", StructuredEvent, max_retries=1)

    trace_files = list(tmp_path.glob("*.jsonl"))
    assert trace_files
    text = trace_files[0].read_text(encoding="utf-8")
    assert '"success": false' in text
    assert '"retry_count": 1' in text

