"""Tests for the Phase 4A news scout helper."""

from __future__ import annotations

from eventalpha.news import NewsFetchResult, NewsItem, NewsSourceRegistry
from scripts.run_news_scout import run_news_scout


def test_run_news_scout_mock_collects_candidates_offline() -> None:
    """Default scout should use deterministic mock providers and no network."""
    result = run_news_scout(limit=10)

    assert result["fetch_result"].items
    assert result["dedup_result"].after_count >= 5
    assert result["filter_result"].after_count >= 5
    assert result["analyses"] == []


def test_run_news_scout_mock_analyze_top_enters_pipeline() -> None:
    """Mock scout should convert top candidates and run the existing pipeline."""
    result = run_news_scout(limit=10, analyze_top=1)

    assert len(result["analyses"]) == 1
    analysis = result["analyses"][0]
    assert analysis["raw_news"].metadata["news_id"] == analysis["news_item"].news_id
    assert analysis["pipeline_result"]["event_card"].risk_disclaimer
    assert analysis["pipeline_result"]["prediction_ledger_entry"].prediction_id


def test_run_news_scout_can_use_rss_only_real_source_without_gdelt() -> None:
    """Real-fetch source selection should allow skipping GDELT when it is rate-limited."""
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

    result = run_news_scout(
        query="AI chip export control",
        real_fetch=True,
        source="rss",
        registry=NewsSourceRegistry([_Provider()]),
    )

    assert result["fetch_result"].errors == []
    assert result["filter_result"].after_count == 1
