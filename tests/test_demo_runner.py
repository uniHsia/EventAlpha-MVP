"""Tests for the offline full demo runner."""

from __future__ import annotations

from pathlib import Path

from eventalpha.demo.demo_runner import run_full_demo
from eventalpha.demo.demo_state import DemoStatePaths
from eventalpha.services import LedgerService


def test_full_demo_runner_generates_demo_chain(tmp_path, monkeypatch) -> None:
    """The full demo should run offline into isolated temp paths."""
    monkeypatch.setattr("eventalpha.demo.demo_runner.write_demo_summary", _wrapped_write_demo_summary)
    paths = _temp_demo_paths(tmp_path)

    summary = run_full_demo(paths=paths, reset_state=True, write_summary=True)

    assert summary.scenario_id == "ai_export_control"
    assert summary.isolated_state is True
    assert summary.prediction["prediction_id"].startswith("PRED_")
    assert summary.event_card["card_id"].startswith("CARD_")
    assert summary.due_review_task["horizon"] == "T+1"
    assert summary.review_result_count == 5
    assert summary.rule_update_count == 1
    assert summary.streamlit_data_check["event_cards"] >= 1
    assert summary.streamlit_data_check["review_results"] == 5
    assert summary.streamlit_data_check["rule_updates"] == 1
    assert Path(summary.briefing_paths["markdown"]).exists()
    assert Path(summary.briefing_paths["json"]).exists()
    assert Path(summary.demo_summary_paths["markdown"]).exists()
    assert Path(summary.demo_summary_paths["json"]).exists()

    ledger = LedgerService(paths.ledger_path)
    rows = ledger.get_review_results(summary.prediction["prediction_id"])
    assert len(rows) == 5
    assert len(ledger.get_rule_updates(summary.prediction["prediction_id"])) == 1


def test_full_demo_runner_does_not_create_default_ledger(tmp_path) -> None:
    paths = _temp_demo_paths(tmp_path)
    default_ledger = tmp_path / "eventalpha_mvp.sqlite3"

    run_full_demo(paths=paths, reset_state=True, write_summary=False)

    assert paths.ledger_path.exists()
    assert not default_ledger.exists()


def _temp_demo_paths(root: Path) -> DemoStatePaths:
    data_root = root / "data" / "demo"
    reports_dir = root / "reports" / "demo"
    return DemoStatePaths(
        project_root=root,
        data_root=data_root,
        reports_dir=reports_dir,
        ledger_path=data_root / "eventalpha_demo.sqlite3",
        scheduler_state_path=data_root / "scheduler_state.json",
        scheduler_runs_path=data_root / "scheduler_runs.jsonl",
        lifecycle_store_path=data_root / "event_lifecycle_store.json",
        cache_dir=data_root / "cache",
        isolated=True,
    )


def _wrapped_write_demo_summary(summary, *, reports_dir, summary_date=None):
    from eventalpha.demo.demo_report import write_demo_summary

    return write_demo_summary(summary, reports_dir=reports_dir, summary_date=summary_date)
