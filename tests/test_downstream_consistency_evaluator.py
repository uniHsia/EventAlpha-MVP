"""Tests for downstream consistency evaluation."""

from __future__ import annotations

from eventalpha.agents import LLMExtractionAgent
from eventalpha.llm import LLMTraceWriter, MockLLMClient, StructuredRunner
from scripts.evaluate_extraction_downstream import (
    evaluate_downstream_cases,
    summarize_downstream_results,
)
from scripts.evaluate_llm_extraction_gold import load_gold_cases


def _agent(tmp_path, calibrated: bool = True) -> LLMExtractionAgent:
    return LLMExtractionAgent(
        runner=StructuredRunner(
            MockLLMClient(),
            trace_writer=LLMTraceWriter(tmp_path, enabled=True),
        ),
        enable_calibration=calibrated,
    )


def test_downstream_evaluator_outputs_required_metrics(tmp_path) -> None:
    """Downstream evaluator should produce regression metrics offline."""
    report = evaluate_downstream_cases(
        load_gold_cases("0"),
        _agent(tmp_path / "llm", calibrated=False),
        _agent(tmp_path / "calibrated", calibrated=True),
    )

    assert "event_level_changed_count" in report["summary"]
    assert "trigger_alert_changed_count" in report["summary"]
    assert "severe_downstream_regression_count" in report["summary"]


def test_downstream_summary_counts_severe_regression() -> None:
    """Summary should count severe downstream regressions."""
    cases = [
        {
            "calibrated_llm": {"event_level": "C"},
            "metrics": {
                "event_level_changed": True,
                "trigger_alert_changed": True,
                "mapped_asset_overlap": 0.0,
                "impact_score_delta": 20,
                "severe_downstream_regression": True,
            },
        }
    ]

    summary = summarize_downstream_results(cases)

    assert summary["event_level_changed_count"] == 1
    assert summary["trigger_alert_changed_count"] == 1
    assert summary["severe_downstream_regression_count"] == 1

