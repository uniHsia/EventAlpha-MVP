"""Tests for the Phase 4B event cluster scout helper."""

from __future__ import annotations

from eventalpha.news import NewsFetchResult, NewsItem, NewsSourceRegistry
from scripts.run_event_cluster_scout import run_event_cluster_scout


def test_run_event_cluster_scout_mock_collects_clusters_offline() -> None:
    """Default cluster scout should use deterministic mock providers and no network."""
    result = run_event_cluster_scout(limit=10)

    assert result["fetch_result"].items
    assert result["filter_result"].after_count >= 5
    assert result["clusters"]
    assert result["analyses"] == []


def test_run_event_cluster_scout_mock_analyze_top_enters_pipeline() -> None:
    """Mock cluster scout should convert clusters and run existing pipeline."""
    result = run_event_cluster_scout(limit=10, analyze_top=1)

    assert len(result["analyses"]) == 1
    analysis = result["analyses"][0]
    assert analysis["raw_news"].metadata["cluster_id"] == analysis["cluster"].cluster_id
    assert analysis["pipeline_result"]["event_card"].risk_disclaimer
    assert analysis["pipeline_result"]["prediction_ledger_entry"].prediction_id


def test_run_event_cluster_scout_can_use_rss_source_selector() -> None:
    """Source selector should be passed through without touching real GDELT."""
    class _Provider:
        name = "rss_only"

        def fetch(self, query=None, limit=20):
            assert query == "AI chip export control"
            return NewsFetchResult(
                source_name=self.name,
                items=[
                    NewsItem(
                        title="AI chip export control update",
                        summary="Advanced GPU export control policy update.",
                        source="Fixture RSS",
                        source_type="mainstream_media",
                    )
                ],
            )

    result = run_event_cluster_scout(
        query="AI chip export control",
        real_fetch=True,
        source="rss",
        registry=NewsSourceRegistry([_Provider()]),
    )

    assert result["fetch_result"].errors == []
    assert len(result["clusters"]) == 1
