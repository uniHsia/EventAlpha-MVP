"""Tests for gold extraction evaluation."""

from __future__ import annotations

from eventalpha.agents import LLMExtractionAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from scripts.evaluate_llm_extraction_gold import evaluate_gold_cases, load_gold_cases


def test_gold_cases_load() -> None:
    """Gold cases should be hand-written and broad enough for evaluation."""
    cases = load_gold_cases()

    assert len(cases) >= 12
    assert all("gold" in case for case in cases)
    assert {case["gold"]["event_type"] for case in cases}


def test_gold_evaluator_outputs_quality_gate(tmp_path) -> None:
    """Gold evaluator should run offline and output readiness fields."""
    agent = LLMExtractionAgent(
        runner=StructuredRunner(
            MockLLMClient(),
            trace_writer=LLMTraceWriter(tmp_path / "traces", enabled=True),
        )
    )

    report = evaluate_gold_cases(load_gold_cases(), agent)

    assert "ready_for_phase3c" in report["summary"]
    assert "blocking_issues" in report["summary"]
    assert report["summary"]["total_cases"] >= 12

