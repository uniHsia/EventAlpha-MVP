"""Tests for isolated demo state handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from eventalpha.demo.demo_state import DemoStatePaths, prepare_demo_state, reset_demo_state


def test_reset_demo_state_only_clears_demo_paths(tmp_path) -> None:
    default_sqlite = tmp_path / "eventalpha_mvp.sqlite3"
    default_sqlite.write_text("keep", encoding="utf-8")
    paths = _temp_demo_paths(tmp_path)
    prepare_demo_state(paths)
    (paths.data_root / "scratch.txt").write_text("demo", encoding="utf-8")
    (paths.reports_dir / "summary.md").write_text("demo", encoding="utf-8")

    reset_demo_state(paths)

    assert not paths.data_root.exists()
    assert not paths.reports_dir.exists()
    assert default_sqlite.exists()
    assert default_sqlite.read_text(encoding="utf-8") == "keep"


def test_reset_demo_state_missing_paths_is_graceful(tmp_path) -> None:
    paths = _temp_demo_paths(tmp_path)

    reset_demo_state(paths)

    assert not paths.data_root.exists()
    assert not paths.reports_dir.exists()


def test_reset_refuses_non_demo_paths(tmp_path) -> None:
    paths = DemoStatePaths(
        project_root=tmp_path,
        data_root=tmp_path / "data",
        reports_dir=tmp_path / "reports",
        ledger_path=tmp_path / "eventalpha_mvp.sqlite3",
        scheduler_state_path=tmp_path / "data" / "scheduler_state.json",
        scheduler_runs_path=tmp_path / "data" / "scheduler_runs.jsonl",
        lifecycle_store_path=tmp_path / "data" / "event_lifecycle_store.json",
        isolated=True,
    )

    with pytest.raises(ValueError, match="Refusing"):
        reset_demo_state(paths)


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
