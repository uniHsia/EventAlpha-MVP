"""Coverage report validation metadata tests."""

from __future__ import annotations

from scripts.check_asset_coverage import build_coverage_report


def test_asset_coverage_report_includes_validation_and_fallback_counts() -> None:
    """Coverage summary should include Phase 2D validation/fallback fields."""
    report = build_coverage_report()
    summary = report["summary"]

    for key in [
        "live_ok_count",
        "live_failed_count",
        "cache_only_count",
        "not_checked_count",
        "fallback_available_count",
        "fully_reviewable_count",
        "reviewable_with_candidate_count",
        "missing_or_unverified_count",
    ]:
        assert key in summary

    assert summary["fallback_available_count"] >= 1
    assert summary["cache_only_count"] >= 1
    assert summary["not_checked_count"] >= 1
