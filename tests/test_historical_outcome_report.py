"""Tests for historical outcome comparison reports."""

from __future__ import annotations

from eventalpha.history import (
    HistoricalOutcomeComparator,
    HistoricalOutcomeReportBuilder,
    build_seed_historical_cases,
    retrieve_analogies_for_query,
)
from eventalpha.schemas import RISK_DISCLAIMER


def test_outcome_report_contains_required_sections() -> None:
    """Report should include status, windows, reasons, seed warning, and disclaimer."""
    case = build_seed_historical_cases()[0]
    analogy = retrieve_analogies_for_query("AI chip export control", [case], limit=1)[0]
    comparison = HistoricalOutcomeComparator().compare(analogy, case)

    report = HistoricalOutcomeReportBuilder().build_text_report([comparison])

    assert "comparison_status=insufficient_current_outcome" in report
    assert "T+1" in report
    assert "T+3" in report
    assert "T+7" in report
    assert "mismatch_reasons=" in report
    assert "historical_data_quality=manual_seed_demo" in report
    assert "current_data_quality=missing" in report
    assert "comparison_reliability=insufficient" in report
    assert "demo_warning=" in report
    assert "manual_seed_demo" in report
    assert RISK_DISCLAIMER in report
