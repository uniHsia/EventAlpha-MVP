"""Tests for the auto-review CLI demo fixture."""

from __future__ import annotations

from pathlib import Path

from scripts.run_scheduler import run_scheduler_once


def test_run_scheduler_auto_review_demo_fixture_generates_results(tmp_path) -> None:
    """Demo fixture should create a temp due review and generate results."""
    default_ledger = Path("eventalpha_mvp.sqlite3")
    before_mtime = default_ledger.stat().st_mtime_ns if default_ledger.exists() else None
    ledger_path = tmp_path / "demo_auto_review.sqlite3"

    result = run_scheduler_once(
        "auto_review_runner",
        execute=True,
        market_provider="mock",
        demo_create_due_review=True,
        ledger_path=ledger_path,
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
    )

    after_mtime = default_ledger.stat().st_mtime_ns if default_ledger.exists() else None
    notes = "\n".join(result["record"].notes)
    assert result["record"].status == "success"
    assert result["record"].candidate_items == 1
    assert result["record"].analyzed_events == 1
    assert "assets=5 results=5" in notes
    assert "ReviewResult count: 5" in notes
    assert before_mtime == after_mtime
