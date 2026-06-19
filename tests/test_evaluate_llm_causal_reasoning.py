"""Tests for LLM causal reasoning evaluator."""

from __future__ import annotations

from eventalpha.agents import LLMCausalReasoningAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from scripts.evaluate_llm_causal_reasoning import evaluate_causal_cases
from scripts.evaluate_llm_extraction_gold import load_gold_cases


def test_llm_causal_evaluator_outputs_summary(tmp_path) -> None:
    """Offline causal evaluator should emit required summary metrics."""
    agent = LLMCausalReasoningAgent(
        runner=StructuredRunner(
            MockLLMClient(),
            trace_writer=LLMTraceWriter(tmp_path, enabled=True),
        ),
        failure_mode="fallback",
    )

    report = evaluate_causal_cases(load_gold_cases("0"), agent)
    summary = report["summary"]

    assert "affected_assets_overlap_avg" in summary
    assert "variable_type_coverage_avg" in summary
    assert "unsupported_asset_count" in summary
    assert "too_long_chain_count" in summary
    assert "low_confidence_for_rumor_count" in summary
    assert "failed_case_count" in summary
    assert "passes_quality_gate" in summary
