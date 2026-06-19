"""Tests for gold-based downstream alert metrics."""

from __future__ import annotations

from types import SimpleNamespace

from scripts.evaluate_extraction_downstream import (
    _is_severe_regression,
    summarize_downstream_results,
)


def test_downstream_summary_counts_gold_alert_metrics() -> None:
    """Summary should distinguish missed and over alerts from rule-based changes."""
    cases = [
        {
            "calibrated_llm": {"event_level": "B"},
            "metrics": {
                "event_level_changed": True,
                "trigger_alert_changed": True,
                "missed_alert": True,
                "over_alert": False,
                "gold_event_level_mismatch": True,
                "gold_trigger_alert_mismatch": True,
                "mapped_asset_overlap": 0.9,
                "impact_score_delta": 5,
                "severe_downstream_regression": True,
            },
        },
        {
            "calibrated_llm": {"event_level": "A"},
            "metrics": {
                "event_level_changed": False,
                "trigger_alert_changed": True,
                "missed_alert": False,
                "over_alert": True,
                "gold_event_level_mismatch": False,
                "gold_trigger_alert_mismatch": True,
                "mapped_asset_overlap": 1.0,
                "impact_score_delta": 3,
                "severe_downstream_regression": False,
            },
        },
    ]

    summary = summarize_downstream_results(cases)

    assert summary["missed_alert_count"] == 1
    assert summary["over_alert_count"] == 1
    assert summary["gold_event_level_mismatch_count"] == 1
    assert summary["gold_trigger_alert_mismatch_count"] == 2
    assert summary["severe_downstream_regression_count"] == 1


def test_missed_alert_is_severe_regression() -> None:
    """Gold expected alert missed by LLM should be severe."""
    severe = _is_severe_regression(
        case={"gold": {"expected_event_level": "A", "expected_trigger_alert": True}},
        rule_result={},
        llm_result={"impact_score": SimpleNamespace(event_level="B", trigger_alert=False)},
        mapped_asset_overlap=1.0,
        impact_score_delta=1,
    )

    assert severe is True
