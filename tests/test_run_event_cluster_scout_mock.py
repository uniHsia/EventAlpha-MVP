"""Tests for the Phase 4B event cluster scout helper."""

from __future__ import annotations

import sqlite3

from eventalpha.news import NewsFetchResult, NewsItem, NewsSourceRegistry
from eventalpha.services import LedgerService
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
    assert "candidate_priority" in analysis


def test_run_event_cluster_scout_with_credibility_outputs_reports() -> None:
    """Cluster scout should optionally include credibility reports."""
    result = run_event_cluster_scout(limit=10, with_credibility=True)

    assert result["credibility_reports"]
    first_cluster = result["clusters"][0]
    assert first_cluster.cluster_id in result["credibility_reports"]


def test_run_event_cluster_scout_analyze_top_with_credibility_metadata() -> None:
    """Analyze-top should carry credibility report into RawNews metadata."""
    result = run_event_cluster_scout(limit=10, analyze_top=1, with_credibility=True)

    metadata = result["analyses"][0]["raw_news"].metadata
    assert "cluster_credibility_score" in metadata
    assert "cluster_credibility_status" in metadata
    assert "claim_consistency_status" in metadata
    assert "candidate_priority" in metadata


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


def test_run_event_cluster_scout_persist_writes_source_cluster_and_evidence_rows(tmp_path) -> None:
    db_path = tmp_path / "scout.sqlite3"
    ledger = LedgerService(db_path)

    result = run_event_cluster_scout(
        limit=10,
        analyze_top=1,
        with_credibility=True,
        persist=True,
        ledger_service=ledger,
    )

    assert result["source_run_id"].startswith("SRCRUN_")
    with sqlite3.connect(db_path) as conn:
        source_count = conn.execute("SELECT COUNT(*) FROM news_sources").fetchone()[0]
        check_count = conn.execute("SELECT COUNT(*) FROM source_check_runs").fetchone()[0]
        raw_item_count = conn.execute("SELECT COUNT(*) FROM raw_news_items").fetchone()[0]
        cluster_count = conn.execute("SELECT COUNT(*) FROM event_clusters").fetchone()[0]
        evidence_count = conn.execute("SELECT COUNT(*) FROM credibility_evidence").fetchone()[0]
        event_card_count = conn.execute("SELECT COUNT(*) FROM event_cards").fetchone()[0]
        source_run_id = conn.execute("SELECT source_run_id FROM raw_news LIMIT 1").fetchone()[0]
        gate_status = conn.execute("SELECT prediction_gate_status FROM event_cards LIMIT 1").fetchone()[0]

    assert source_count >= 1
    assert check_count >= 1
    assert raw_item_count >= 1
    assert cluster_count >= 1
    assert evidence_count >= 1
    assert event_card_count >= 1
    assert source_run_id == result["source_run_id"]
    assert gate_status in {"written", "skipped_low_event_level", "skipped_low_confidence", "skipped_no_assets", "skipped_observation_cluster_type"}
