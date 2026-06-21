"""Tests for the run_full_demo CLI helpers."""

from __future__ import annotations

from pathlib import Path

from eventalpha.demo.demo_runner import STREAMLIT_DEMO_INSTRUCTION
from eventalpha.demo.demo_state import DemoStatePaths
from scripts.run_full_demo import _format_summary, run_full_demo_cli


def test_run_full_demo_cli_helper_writes_summary(tmp_path, monkeypatch) -> None:
    paths = _temp_demo_paths(tmp_path)
    monkeypatch.setattr("scripts.run_full_demo._run_full_demo", lambda **kwargs: _run_with_paths(paths, **kwargs))

    summary = run_full_demo_cli(
        scenario_id="ai_export_control",
        reset_demo_state=True,
        write_summary=True,
    )
    output = _format_summary(summary, include_open_instructions=True)

    assert "EventAlpha Full Demo Completed" in output
    assert STREAMLIT_DEMO_INSTRUCTION in output
    assert "ReviewResults: 5" in output
    assert summary.demo_summary_paths
    assert not (tmp_path / "eventalpha_mvp.sqlite3").exists()


def test_run_full_demo_reset_flag_is_supported(tmp_path, monkeypatch) -> None:
    paths = _temp_demo_paths(tmp_path)
    monkeypatch.setattr("scripts.run_full_demo._run_full_demo", lambda **kwargs: _run_with_paths(paths, **kwargs))

    summary = run_full_demo_cli(reset_demo_state=True, write_summary=False)

    assert summary.steps[0].step_name == "prepare_demo_state"
    assert summary.steps[0].counts["reset"] == 1
    assert paths.ledger_path.exists()


def _run_with_paths(paths: DemoStatePaths, **kwargs):
    from eventalpha.demo.demo_runner import run_full_demo

    return run_full_demo(
        scenario_id=kwargs.get("scenario_id", "ai_export_control"),
        reset_state=kwargs.get("reset_state", False),
        write_summary=kwargs.get("write_summary", False),
        use_default_state=False,
        paths=paths,
    )


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
