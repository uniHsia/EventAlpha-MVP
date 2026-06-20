"""Tests for LLM anti-spurious evaluator."""

from __future__ import annotations

from eventalpha.agents import LLMAntiSpuriousAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from scripts.evaluate_llm_anti_spurious import evaluate_anti_spurious_cases
from scripts.evaluate_llm_extraction_gold import load_gold_cases


def test_llm_anti_spurious_evaluator_outputs_summary(tmp_path) -> None:
    """Offline anti-spurious evaluator should emit required summary metrics."""
    agent = LLMAntiSpuriousAgent(
        runner=StructuredRunner(
            MockLLMClient(),
            trace_writer=LLMTraceWriter(tmp_path, enabled=True),
        ),
        failure_mode="fallback",
    )

    report = evaluate_anti_spurious_cases(load_gold_cases("0"), agent)
    summary = report["summary"]

    assert "spurious_risk_distribution" in summary
    assert "low_risk_count" in summary
    assert "medium_risk_count" in summary
    assert "high_risk_count" in summary
    assert "adjusted_confidence_delta_avg" in summary
    assert "required_verification_count_avg" in summary
    assert "issue_count_avg" in summary
    assert "issue_count_after_compression_avg" in summary
    assert "required_verification_count_after_compression_avg" in summary
    assert "max_issue_count" in summary
    assert "max_required_verification_count" in summary
    assert "risk_calibration_count" in summary
    assert "event_card_risk_factor_count_avg" in summary
    assert "event_card_verification_indicator_count_avg" in summary
    assert "overconfident_rumor_count" in summary
    assert "second_order_issue_detected_count" in summary
    assert "failed_case_count" in summary
    assert "passes_quality_gate" in summary
    assert report["cases"][0]["metrics"]["issue_count_after_compression"] >= 0
