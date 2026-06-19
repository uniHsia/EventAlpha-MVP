"""Asset coverage report tests."""

from __future__ import annotations

from scripts.check_asset_coverage import build_coverage_report


def test_asset_coverage_report_counts_statuses() -> None:
    """Coverage report should summarize verified, candidate, and missing routes."""
    report = build_coverage_report()
    summary = report["summary"]

    assert summary["total_assets"] > 0
    assert summary["verified_count"] >= 1
    assert summary["candidate_count"] >= 1
    assert summary["missing_count"] >= 1
    assert summary["csv_count"] >= 1
    assert summary["akshare_count"] >= 1
    assert 0 < summary["coverage_rate"] <= 1
