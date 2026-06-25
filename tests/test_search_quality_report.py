"""Tests for search quality reports."""

from __future__ import annotations

from eventalpha.news.search_quality import build_search_quality_report


def test_search_quality_offline_mock_counts_are_stable() -> None:
    report = build_search_quality_report(
        demo_mode=True,
        event_cards=[{"event_level": "A"}],
        ledger_rows=[{"prediction_id": "PRED_1"}],
    )

    assert report.demo_mode is True
    assert report.raw_news_count > 0
    assert report.after_dedup_count > 0
    assert report.cluster_count > 0
    assert report.event_card_count == 1
    assert report.high_priority_event_count == 1
    assert report.ledger_prediction_count == 1
    assert report.source_breakdown


def test_search_quality_empty_registry_returns_zeroes() -> None:
    from eventalpha.news import NewsFetchResult, NewsSourceRegistry

    class _EmptyProvider:
        name = "empty"

        def fetch(self, query=None, limit=20):
            return NewsFetchResult(source_name=self.name, items=[], errors=[])

    report = build_search_quality_report(registry=NewsSourceRegistry([_EmptyProvider()]))

    assert report.raw_news_count == 0
    assert report.after_dedup_count == 0
    assert report.cluster_count == 0
