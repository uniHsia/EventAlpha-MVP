from __future__ import annotations

import sqlite3

from scripts.inspect_news_persistence import inspect_latest_run


def test_inspect_news_persistence_handles_missing_db(tmp_path) -> None:
    result = inspect_latest_run(tmp_path / "missing.sqlite3")
    assert result["status"] == "empty"


def test_inspect_news_persistence_reads_latest_run(tmp_path) -> None:
    db_path = tmp_path / "ledger.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE news_sources (id INTEGER PRIMARY KEY, source_name TEXT);
            CREATE TABLE source_check_runs (id INTEGER PRIMARY KEY, source_run_id TEXT, source_name TEXT, fetched_at TEXT, item_count INTEGER);
            CREATE TABLE raw_news_items (id INTEGER PRIMARY KEY, source_run_id TEXT, is_duplicate INTEGER DEFAULT 0);
            CREATE TABLE event_clusters (id INTEGER PRIMARY KEY, source_run_id TEXT, cluster_type TEXT, item_count INTEGER, unique_source_count INTEGER, independent_confirmation INTEGER, verification_status TEXT, confidence REAL);
            CREATE TABLE cluster_news_links (id INTEGER PRIMARY KEY, source_run_id TEXT);
            CREATE TABLE credibility_evidence (id INTEGER PRIMARY KEY, source_run_id TEXT);
            CREATE TABLE raw_news (id INTEGER PRIMARY KEY, raw_id TEXT, source_run_id TEXT);
            CREATE TABLE events (id INTEGER PRIMARY KEY, event_id TEXT, raw_id TEXT);
            CREATE TABLE event_cards (id INTEGER PRIMARY KEY, event_id TEXT, source_evidence_json TEXT, prediction_gate_status TEXT);
            CREATE TABLE prediction_ledger (id INTEGER PRIMARY KEY, event_id TEXT);
            INSERT INTO news_sources (source_name) VALUES ('rss_1');
            INSERT INTO source_check_runs (source_run_id, source_name, fetched_at, item_count) VALUES ('SRCRUN_1', 'rss_1', '2026-06-25T00:00:00Z', 3);
            INSERT INTO raw_news_items (source_run_id, is_duplicate) VALUES ('SRCRUN_1', 0), ('SRCRUN_1', 1);
            INSERT INTO event_clusters (source_run_id, cluster_type, item_count, unique_source_count, independent_confirmation, verification_status, confidence) VALUES ('SRCRUN_1', 'multi_source_event', 2, 2, 1, 'confirmed', 0.8);
            INSERT INTO cluster_news_links (source_run_id) VALUES ('SRCRUN_1');
            INSERT INTO credibility_evidence (source_run_id) VALUES ('SRCRUN_1');
            INSERT INTO raw_news (raw_id, source_run_id) VALUES ('RAW_1', 'SRCRUN_1');
            INSERT INTO events (event_id, raw_id) VALUES ('EVT_1', 'RAW_1');
            INSERT INTO event_cards (event_id, source_evidence_json, prediction_gate_status) VALUES ('EVT_1', '[{}]', 'written');
            INSERT INTO prediction_ledger (event_id) VALUES ('EVT_1');
            """
        )
    result = inspect_latest_run(db_path)
    assert result["status"] == "ok"
    assert result["latest_source_run_id"] == "SRCRUN_1"
    assert result["event_clusters_count"] == 1
    assert result["ledger_predictions_created_count"] == 1
