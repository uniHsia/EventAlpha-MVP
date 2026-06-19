"""Tests for LLM extraction evaluation helpers."""

from __future__ import annotations

from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from eventalpha.agents import LLMExtractionAgent
from scripts.evaluate_llm_extraction import evaluate_cases, load_demo_news


def test_evaluate_llm_extraction_with_mock_client(tmp_path) -> None:
    """Mock LLM evaluation should produce a stable offline summary."""
    agent = LLMExtractionAgent(
        runner=StructuredRunner(
            MockLLMClient(),
            trace_writer=LLMTraceWriter(tmp_path / "traces", enabled=True),
        )
    )

    report = evaluate_cases(load_demo_news(), agent)

    assert report["summary"]["total_cases"] >= 4
    assert "event_type_match_count" in report["summary"]
    assert "asset_hint_overlap_avg" in report["summary"]
    assert "postprocess_warning_count" in report["summary"]
    assert len(report["cases"]) == report["summary"]["total_cases"]

