"""Isolated filesystem state for the offline full demo."""

from __future__ import annotations

import shutil
from pathlib import Path

from pydantic import Field

from eventalpha.config import DEFAULT_DB_PATH, PROJECT_ROOT
from eventalpha.schemas.base import EventAlphaModel


class DemoStatePaths(EventAlphaModel):
    """All local paths used by one demo run."""

    project_root: Path = PROJECT_ROOT
    data_root: Path
    reports_dir: Path
    ledger_path: Path
    scheduler_state_path: Path
    scheduler_runs_path: Path
    lifecycle_store_path: Path
    cache_dir: Path | None = None
    isolated: bool = True
    notes: list[str] = Field(default_factory=list)


def default_demo_paths(project_root: str | Path | None = None) -> DemoStatePaths:
    """Return the default isolated demo paths."""
    root = Path(project_root) if project_root else PROJECT_ROOT
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
        notes=["Using isolated demo state under data/demo and reports/demo."],
    )


def default_state_paths(project_root: str | Path | None = None) -> DemoStatePaths:
    """Return opt-in default project state paths."""
    root = Path(project_root) if project_root else PROJECT_ROOT
    return DemoStatePaths(
        project_root=root,
        data_root=root / "data",
        reports_dir=root / "reports",
        ledger_path=DEFAULT_DB_PATH,
        scheduler_state_path=root / "data" / "scheduler_state.json",
        scheduler_runs_path=root / "data" / "scheduler_runs.jsonl",
        lifecycle_store_path=root / "data" / "event_lifecycle_store.json",
        cache_dir=root / "data" / "cache",
        isolated=False,
        notes=["Using default EventAlpha state because --use-default-state was provided."],
    )


def prepare_demo_state(paths: DemoStatePaths | None = None, *, reset: bool = False) -> DemoStatePaths:
    """Create required demo directories and optionally reset isolated state."""
    resolved = paths or default_demo_paths()
    if reset:
        reset_demo_state(resolved)
    resolved.data_root.mkdir(parents=True, exist_ok=True)
    resolved.reports_dir.mkdir(parents=True, exist_ok=True)
    resolved.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    resolved.scheduler_state_path.parent.mkdir(parents=True, exist_ok=True)
    resolved.scheduler_runs_path.parent.mkdir(parents=True, exist_ok=True)
    resolved.lifecycle_store_path.parent.mkdir(parents=True, exist_ok=True)
    if resolved.cache_dir is not None:
        resolved.cache_dir.mkdir(parents=True, exist_ok=True)
    return resolved


def reset_demo_state(paths: DemoStatePaths | None = None) -> None:
    """Remove only isolated demo data roots and demo report roots."""
    resolved = paths or default_demo_paths()
    _assert_safe_reset_path(resolved.data_root, expected_leaf="demo")
    _assert_safe_reset_path(resolved.reports_dir, expected_leaf="demo")
    _remove_path(resolved.data_root)
    _remove_path(resolved.reports_dir)


def _remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def _assert_safe_reset_path(path: Path, *, expected_leaf: str) -> None:
    """Guard against accidental deletion of non-demo project data."""
    resolved = path.resolve()
    parts = {part.casefold() for part in resolved.parts}
    if resolved.name.casefold() != expected_leaf or "demo" not in parts:
        raise ValueError(f"Refusing to reset non-demo path: {resolved}")
