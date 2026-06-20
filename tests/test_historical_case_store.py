"""Tests for the historical case JSON store."""

from __future__ import annotations

from eventalpha.history import HistoricalCase, HistoricalCaseStore


def test_historical_case_store_load_save_upsert_get_list_reset(tmp_path) -> None:
    """Store should round-trip historical cases through JSON."""
    path = tmp_path / "historical_cases.json"
    case = HistoricalCase(
        title="AI chip export control example",
        event_type="ai_export_control",
        summary="Illustrative case.",
    )

    store = HistoricalCaseStore(path).load()
    assert store.list_cases() == []

    store.upsert(case)
    store.save()

    restored = HistoricalCaseStore(path).load()
    assert restored.get(case.case_id).title == case.title
    assert len(restored.list_cases()) == 1

    restored.reset()
    assert restored.list_cases() == []
    assert not path.exists()


def test_historical_case_store_missing_file_is_empty(tmp_path) -> None:
    """Missing store files should load as empty stores."""
    store = HistoricalCaseStore(tmp_path / "missing.json").load()

    assert store.list_cases() == []
