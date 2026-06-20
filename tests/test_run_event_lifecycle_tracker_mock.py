"""Tests for the lifecycle tracker helper."""

from __future__ import annotations

from scripts.run_event_lifecycle_tracker import run_event_lifecycle_tracker


def test_run_event_lifecycle_tracker_mock_offline(tmp_path) -> None:
    """Default lifecycle tracker should run on mock providers."""
    path = tmp_path / "lifecycle.json"

    result = run_event_lifecycle_tracker(store_path=path, limit=10)

    assert result["fetch_result"].items
    assert result["clusters"]
    assert result["active_events"]
    assert result["updates"]
    assert path.exists()


def test_run_event_lifecycle_tracker_reset_store(tmp_path) -> None:
    """Reset should clear the store when combined with list-active."""
    path = tmp_path / "lifecycle.json"
    run_event_lifecycle_tracker(store_path=path, limit=10)

    result = run_event_lifecycle_tracker(store_path=path, reset_store=True, list_active=True)

    assert result["active_events"] == []
    assert result["fetch_result"] is None


def test_run_event_lifecycle_tracker_list_active_does_not_fetch(tmp_path) -> None:
    """List-active should only read the JSON store."""
    path = tmp_path / "lifecycle.json"
    run_event_lifecycle_tracker(store_path=path, limit=10)

    result = run_event_lifecycle_tracker(store_path=path, list_active=True)

    assert result["fetch_result"] is None
    assert result["active_events"]


def test_repeated_mock_run_matches_existing_events(tmp_path) -> None:
    """A second mock run should match existing tracked events and append timeline."""
    path = tmp_path / "lifecycle.json"
    first = run_event_lifecycle_tracker(store_path=path, limit=10)
    second = run_event_lifecycle_tracker(store_path=path, limit=10)

    first_ids = {event.tracked_event_id for event in first["active_events"]}
    second_ids = {event.tracked_event_id for event in second["active_events"]}
    assert first_ids <= second_ids
    assert any(update.update_type == "matched_existing" for update in second["updates"])
    assert any(len(event.timeline) >= 2 for event in second["active_events"])


def test_run_event_lifecycle_tracker_analyze_updated(tmp_path) -> None:
    """Analyze-updated should enter the existing pipeline with persist disabled."""
    path = tmp_path / "lifecycle.json"

    result = run_event_lifecycle_tracker(store_path=path, limit=10, analyze_updated=1)

    assert len(result["analyses"]) == 1
    analysis = result["analyses"][0]
    assert analysis["raw_news"].metadata["tracked_event_id"] == analysis["tracked_event"].tracked_event_id
    assert analysis["pipeline_result"]["event_card"].risk_disclaimer
