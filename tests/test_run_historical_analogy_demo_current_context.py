"""Tests for Phase 5B.1 historical analogy demo context integration."""

from __future__ import annotations

from eventalpha.news import EventLifecycleStore, TrackedEvent
from eventalpha.schemas.base import utc_now
from scripts.run_historical_analogy_demo import run_historical_analogy_demo


def test_demo_current_ai_export_context_scores_above_query_only(tmp_path) -> None:
    """Combined current-event context should produce a richer analogy than query-only input."""
    query_result = run_historical_analogy_demo(
        query="AI chip export control",
        limit=1,
        store_path=tmp_path / "missing_cases.json",
    )
    combined_result = run_historical_analogy_demo(
        demo_current_ai_export=True,
        limit=1,
        store_path=tmp_path / "missing_cases.json",
    )

    query_top = query_result["analogies"][0]
    combined_top = combined_result["analogies"][0]
    non_query_hits = [
        score
        for score in combined_top.dimension_scores
        if score.dimension != "query_keywords" and score.score > 0
    ]
    suggestion_text = " ".join(combined_top.verification_suggestions).casefold()

    assert combined_top.historical_case_title.startswith("US advanced chip")
    assert combined_top.overall_score > query_top.overall_score
    assert non_query_hits
    assert "yield curve" not in suggestion_text
    assert "fx" not in suggestion_text
    assert combined_top.input_context is not None
    assert combined_top.input_context.context_label == "multi-dimensional"


def test_from_active_event_empty_store_returns_clear_message(tmp_path) -> None:
    """from_active_event should be read-only and clear when no lifecycle events exist."""
    lifecycle_store_path = tmp_path / "empty_lifecycle.json"
    result = run_historical_analogy_demo(
        from_active_event=1,
        lifecycle_store_path=lifecycle_store_path,
        store_path=tmp_path / "missing_cases.json",
    )

    assert result["analogies"] == []
    assert "No active tracked events found" in result["message"]
    assert not lifecycle_store_path.exists()


def test_from_active_event_uses_existing_tracked_event(tmp_path) -> None:
    """from_active_event should retrieve analogies from an active tracked event without fetching."""
    lifecycle_store_path = tmp_path / "lifecycle.json"
    now = utc_now()
    store = EventLifecycleStore(lifecycle_store_path).load()
    store.upsert(
        TrackedEvent(
            canonical_title="US expands AI chip export controls",
            current_summary="Advanced GPU restrictions may affect China AI supply chains.",
            first_seen_at=now,
            last_seen_at=now,
            sources=["Mock News"],
            source_count=1,
            latest_claims=["Export controls restrict advanced GPU supply."],
            dominant_keywords=["AI chips", "semiconductor", "export_control"],
        )
    )
    store.save()

    result = run_historical_analogy_demo(
        from_active_event=1,
        lifecycle_store_path=lifecycle_store_path,
        store_path=tmp_path / "missing_cases.json",
        limit=2,
    )

    assert result["selected_tracked_event"] is not None
    assert result["analogies"]
    assert result["analogies"][0].historical_case_title.startswith("US advanced chip")
