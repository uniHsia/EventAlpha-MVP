"""Tests for the daily briefing CLI helper."""

from __future__ import annotations

from datetime import date

from scripts.run_daily_briefing import build_daily_briefing


def test_run_daily_briefing_print_mode(tmp_path) -> None:
    """Default helper should build Markdown without writing reports."""
    result = build_daily_briefing(
        briefing_date=date(2026, 6, 21),
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=tmp_path / "missing.sqlite3",
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
    )

    assert "EventAlpha Daily Briefing - 2026-06-21" in result["markdown"]
    assert result["paths"] is None
    assert not (tmp_path / "missing.sqlite3").exists()


def test_run_daily_briefing_write_report(tmp_path) -> None:
    """Write mode should place reports in the requested temp directory."""
    result = build_daily_briefing(
        briefing_date=date(2026, 6, 21),
        write_report=True,
        reports_dir=tmp_path / "reports",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=tmp_path / "missing.sqlite3",
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
    )

    assert result["paths"]["markdown"].exists()
    assert result["paths"]["json"].exists()
    assert result["paths"]["markdown"].parent == tmp_path / "reports"
