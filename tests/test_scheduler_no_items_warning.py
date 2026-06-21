"""Tests for scheduler no-items warning handling."""

from __future__ import annotations

from eventalpha.news import NewsFetchResult, NewsSourceRegistry
from eventalpha.scheduler import SchedulerJobConfig, SchedulerRunRecord, SchedulerStateStore, run_news_lifecycle_scan, run_scheduler_status


class NoItemsProvider:
    """Provider fixture that returns an RSS no-items message."""

    name = "no_items"

    def fetch(self, query: str | None = None, limit: int = 20) -> NewsFetchResult:
        return NewsFetchResult(
            source_name=self.name,
            items=[],
            errors=["RSS query matched no items."],
        )


def test_scheduler_treats_rss_no_items_as_warning(tmp_path) -> None:
    """RSS no-items should not become a hard scheduler error."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    registry = NewsSourceRegistry([NoItemsProvider()])

    record = run_news_lifecycle_scan(
        SchedulerJobConfig(job_id="scan", job_type="news_lifecycle_scan", dry_run=False),
        store,
        lifecycle_store_path=tmp_path / "lifecycle.json",
        registry=registry,
    )

    assert record.status == "success"
    assert record.errors == []
    assert record.warnings == ["RSS query matched no items."]
    assert any("RSS query matched no items" in note for note in record.notes)


def test_scheduler_status_downgrades_legacy_no_items_errors(tmp_path) -> None:
    """Old run-log no-items errors should display as warnings in status."""
    store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    legacy = SchedulerRunRecord(
        job_id="scan",
        job_type="news_lifecycle_scan",
        errors=["RSS query matched no items."],
    ).finish("success")
    store.append_run(legacy)

    record = run_scheduler_status(
        SchedulerJobConfig(job_id="status", job_type="scheduler_status"),
        store,
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
    )

    assert record.status == "success"
    assert record.errors == []
    assert "RSS query matched no items." in record.warnings
    assert any("Recent no-items warning" in note for note in record.notes)
