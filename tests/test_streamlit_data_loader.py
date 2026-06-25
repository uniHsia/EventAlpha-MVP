"""Tests for read-only Streamlit console data loading."""

from __future__ import annotations

import json
import sqlite3
from datetime import date

from eventalpha.news import EventLifecycleStore, TrackedEvent
from eventalpha.scheduler import SchedulerJobConfig, SchedulerRunRecord, SchedulerStateStore, TrackingPolicy
from eventalpha.schemas.base import utc_now
from eventalpha.ui import StreamlitDataLoader


def test_loader_handles_missing_files_without_creating_ledger(tmp_path) -> None:
    """Missing local files should become empty state, not writes."""
    missing_ledger = tmp_path / "missing.sqlite3"
    bundle = StreamlitDataLoader(
        reports_dir=tmp_path / "reports",
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=missing_ledger,
    ).load(briefing_date=date(2026, 6, 21))

    assert bundle["reports"] == []
    assert bundle["latest_report"] is None
    assert bundle["collected_data"].active_events == []
    assert bundle["top_events"] == []
    assert bundle["recent_reviews"] == []
    assert bundle["recent_rule_updates"] == []
    assert bundle["friendly_warnings"] == []
    assert "dashboard_metrics" in bundle
    assert not missing_ledger.exists()
    assert any("No local briefing reports" in note for note in bundle["notes"])


def test_loader_reads_briefing_report_files(tmp_path) -> None:
    """Markdown and JSON reports should be available to the console."""
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "daily_briefing_20260621.md").write_text("# Briefing", encoding="utf-8")
    (reports_dir / "daily_briefing_20260621.json").write_text(
        json.dumps({"title": "EventAlpha Daily Briefing - 2026-06-21"}),
        encoding="utf-8",
    )

    bundle = StreamlitDataLoader(
        reports_dir=reports_dir,
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=tmp_path / "missing.sqlite3",
    ).load(briefing_date=date(2026, 6, 21))

    assert bundle["latest_report"].markdown == "# Briefing"
    assert bundle["latest_report"].json_payload["title"].endswith("2026-06-21")


def test_loader_reads_scheduler_lifecycle_and_tracking_state(tmp_path) -> None:
    """Scheduler runs, policies, and lifecycle events should load from local files."""
    now = utc_now()
    lifecycle_path = tmp_path / "lifecycle.json"
    lifecycle_store = EventLifecycleStore(lifecycle_path)
    lifecycle_store.upsert(
        TrackedEvent(
            canonical_title="AI export controls",
            lifecycle_stage="developing",
            first_seen_at=now,
            last_seen_at=now,
            sources=["Mock Wire"],
            source_count=1,
        )
    )
    lifecycle_store.save()

    scheduler_store = SchedulerStateStore(tmp_path / "state.json", tmp_path / "runs.jsonl")
    scheduler_store.save_config([SchedulerJobConfig(job_id="status", job_type="scheduler_status")])
    scheduler_store.save_tracking_policies(
        [
            TrackingPolicy(
                tracked_event_id=lifecycle_store.list_events()[0].tracked_event_id,
                tracking_mode="normal",
                scan_interval_minutes=60,
                analyze=True,
                reason="test",
            )
        ]
    )
    scheduler_store.append_run(
        SchedulerRunRecord(job_id="status", job_type="scheduler_status").finish("success")
    )

    bundle = StreamlitDataLoader(
        reports_dir=tmp_path / "reports",
        lifecycle_store_path=lifecycle_path,
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=tmp_path / "missing.sqlite3",
    ).load(briefing_date=date(2026, 6, 21))

    data = bundle["collected_data"]
    assert data.active_events[0].canonical_title == "AI export controls"
    assert data.scheduler_jobs[0].job_id == "status"
    assert data.recent_runs[0].status == "success"
    assert data.tracking_policies[0].tracking_mode == "normal"


def test_loader_reads_ledger_rows_read_only(tmp_path) -> None:
    """Ledger-backed rows should be loaded via read-only collector queries."""
    ledger_path = tmp_path / "ledger.sqlite3"
    _create_ui_ledger_fixture(ledger_path)

    bundle = StreamlitDataLoader(
        reports_dir=tmp_path / "reports",
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=ledger_path,
    ).load(briefing_date=date(2026, 6, 21))

    data = bundle["collected_data"]
    assert data.event_cards[0]["event_title"] == "AI export event"
    assert data.review_results[0]["asset_name"] == "AI chips"
    assert data.rule_updates[0]["rule_id"] == "RULE_AI_EXPORT_001"
    assert bundle["prediction_ledger_rows"][0]["prediction_id"] == "PRED_1"
    assert bundle["prediction_ledger_rows"][0]["asset_name"] == "AI chips"
    assert bundle["recent_reviews"][0]["资产"] == "AI chips"
    assert bundle["recent_rule_updates"][0]["RuleID"] == "RULE_AI_EXPORT_001"


def test_loader_reads_historical_cases_without_writes(tmp_path) -> None:
    """Historical cases should load from a local JSON store without seeding."""
    historical_path = tmp_path / "historical_cases.json"
    historical_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "case_id": "CASE_1",
                        "title": "AI export precedent",
                        "event_type": "ai_export_control",
                        "tags": ["manual_seed_demo"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    bundle = StreamlitDataLoader(
        reports_dir=tmp_path / "reports",
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=tmp_path / "missing.sqlite3",
        historical_cases_path=historical_path,
    ).load(briefing_date=date(2026, 6, 21))

    assert bundle["historical_cases"][0]["case_id"] == "CASE_1"
    assert bundle["data_status"]["historical_cases_exists"] is True


def test_loader_reads_capability_reports_when_present(tmp_path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "source_coverage_20260621.json").write_text(
        json.dumps({"demo_mode": True, "enabled_count": 1, "ok_count": 1, "failed_count": 0, "placeholder_count": 3, "items": []}),
        encoding="utf-8",
    )
    (reports_dir / "search_quality_20260621.json").write_text(
        json.dumps({"demo_mode": True, "raw_news_count": 2, "after_dedup_count": 2, "cluster_count": 1}),
        encoding="utf-8",
    )

    bundle = StreamlitDataLoader(
        reports_dir=reports_dir,
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=tmp_path / "missing.sqlite3",
    ).load(briefing_date=date(2026, 6, 21))

    assert bundle["capability_reports"]["source_coverage"]["ok_count"] == 1
    assert bundle["capability_reports"]["search_quality"]["cluster_count"] == 1
    assert bundle["capability_reports"]["source_coverage"]["_path"].endswith("source_coverage_20260621.json")


def test_loader_reads_source_cluster_and_evidence_rows_from_sqlite(tmp_path) -> None:
    ledger_path = tmp_path / "ledger.sqlite3"
    _create_source_cluster_fixture(ledger_path)

    bundle = StreamlitDataLoader(
        reports_dir=tmp_path / "reports",
        lifecycle_store_path=tmp_path / "missing_lifecycle.json",
        state_path=tmp_path / "state.json",
        runs_path=tmp_path / "runs.jsonl",
        ledger_path=ledger_path,
    ).load(briefing_date=date(2026, 6, 21))

    assert bundle["source_registry_rows"][0]["source_name"] == "sec_press_releases"
    assert bundle["source_check_runs"][0]["status"] == "ok"
    assert bundle["cluster_rows"][0]["cluster_id"] == "CLUSTER_1"
    assert bundle["credibility_evidence_rows"][0]["evidence_type"] == "source_summary"


def _create_ui_ledger_fixture(path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                event_type TEXT
            );
            CREATE TABLE event_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id TEXT,
                event_id TEXT,
                event_title TEXT,
                event_level TEXT,
                credibility_score REAL,
                one_sentence TEXT,
                what_happened TEXT,
                sources_json TEXT,
                causal_chain_summary_json TEXT,
                possible_impacts_json TEXT,
                risk_factors_json TEXT,
                verification_indicators_json TEXT,
                risk_disclaimer TEXT,
                created_at TEXT
            );
            CREATE TABLE market_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mapping_id TEXT,
                event_id TEXT,
                mapped_assets_json TEXT,
                watch_indicators_json TEXT,
                mapping_notes TEXT,
                created_at TEXT
            );
            CREATE TABLE prediction_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id TEXT,
                event_id TEXT,
                event_title TEXT,
                event_type TEXT,
                publish_time TEXT,
                event_level TEXT,
                credibility_score REAL,
                impact_score INTEGER,
                status TEXT,
                created_at TEXT
            );
            CREATE TABLE predicted_assets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id TEXT,
                asset_name TEXT,
                asset_type TEXT,
                direction TEXT,
                time_window TEXT,
                asset_confidence REAL,
                chain_confidence REAL,
                anti_spurious_adjusted_confidence REAL,
                final_confidence REAL,
                confidence REAL,
                benchmark TEXT,
                created_at TEXT
            );
            CREATE TABLE review_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                review_id TEXT,
                prediction_id TEXT,
                event_id TEXT,
                horizon TEXT,
                asset_name TEXT,
                predicted_direction TEXT,
                actual_return REAL,
                benchmark_return REAL,
                excess_return REAL,
                direction_correct INTEGER,
                outperformed_benchmark INTEGER,
                causal_validity TEXT,
                review_conclusion TEXT,
                error_type TEXT,
                created_at TEXT
            );
            CREATE TABLE prediction_review_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary_id TEXT,
                prediction_id TEXT,
                event_id TEXT,
                horizon TEXT,
                total_assets INTEGER,
                reviewed_assets INTEGER,
                direction_correct_count INTEGER,
                outperform_count INTEGER,
                average_excess_return REAL,
                conclusion_level TEXT,
                summary_text TEXT,
                error_types_json TEXT,
                rule_update_suggestions_json TEXT,
                created_at TEXT
            );
            CREATE TABLE rule_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                update_id TEXT,
                rule_id TEXT,
                prediction_id TEXT,
                review_id TEXT,
                summary_id TEXT,
                old_weight REAL,
                new_weight REAL,
                reason TEXT,
                update_action TEXT,
                created_at TEXT
            );
            INSERT INTO events (event_id, event_type) VALUES ('EVT_1', 'ai_export_control');
            INSERT INTO event_cards
            (card_id, event_id, event_title, event_level, credibility_score, one_sentence,
             what_happened, sources_json, causal_chain_summary_json, possible_impacts_json,
             risk_factors_json, verification_indicators_json, risk_disclaimer, created_at)
            VALUES ('CARD_1', 'EVT_1', 'AI export event', 'A', 0.8, 'summary',
                    'what happened', '["Mock Wire"]', '["policy restriction", "supply limit"]',
                    '["AI chips"]',
                    '["risk"]', '["verify"]', 'risk disclaimer', '2026-06-21T00:00:00Z');
            INSERT INTO market_mappings
            (mapping_id, event_id, mapped_assets_json, watch_indicators_json, mapping_notes, created_at)
            VALUES ('MAP_1', 'EVT_1', '[{"asset_name": "AI chips"}]', '["watch"]', 'notes',
                    '2026-06-21T00:00:00Z');
            INSERT INTO prediction_ledger
            (prediction_id, event_id, event_title, event_type, publish_time, event_level,
             credibility_score, impact_score, status, created_at)
            VALUES ('PRED_1', 'EVT_1', 'AI export event', 'ai_export_control',
                    '2026-06-21T00:00:00Z', 'A', 0.8, 80, 'tracking',
                    '2026-06-21T00:00:00Z');
            INSERT INTO predicted_assets
            (prediction_id, asset_name, asset_type, direction, time_window,
             asset_confidence, chain_confidence, anti_spurious_adjusted_confidence,
             final_confidence, confidence, benchmark, created_at)
            VALUES ('PRED_1', 'AI chips', 'theme', 'up', 'T+1',
                    0.8, 0.7, 0.6, 0.65, 0.65, 'CSI300',
                    '2026-06-21T00:00:00Z');
            INSERT INTO review_results
            (review_id, prediction_id, event_id, horizon, asset_name, predicted_direction,
             actual_return, benchmark_return, excess_return, direction_correct,
             outperformed_benchmark, causal_validity, review_conclusion, error_type, created_at)
            VALUES ('REV_1', 'PRED_1', 'EVT_1', 'T+1', 'AI chips', 'up',
                    0.03, 0.01, 0.02, 1, 1, 'valid', 'mock backed', 'none',
                    '2026-06-21T00:00:00Z');
            INSERT INTO prediction_review_summaries
            (summary_id, prediction_id, event_id, horizon, total_assets, reviewed_assets,
             direction_correct_count, outperform_count, average_excess_return,
             conclusion_level, summary_text, error_types_json, rule_update_suggestions_json, created_at)
            VALUES ('SUM_1', 'PRED_1', 'EVT_1', 'T+1', 1, 1, 1, 1, 0.02,
                    'valid', 'summary', '[]', '[]', '2026-06-21T00:00:00Z');
            INSERT INTO rule_updates
            (update_id, rule_id, prediction_id, review_id, summary_id, old_weight,
             new_weight, reason, update_action, created_at)
            VALUES ('UPD_1', 'RULE_AI_EXPORT_001', 'PRED_1', 'REV_1', 'SUM_1',
                    0.7, 0.75, 'worked', 'strengthen', '2026-06-21T00:00:00Z');
            """
        )


def _create_source_cluster_fixture(path) -> None:
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE news_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT,
                source_type TEXT,
                enabled INTEGER,
                region TEXT,
                language TEXT,
                credibility_base REAL,
                fetch_mode TEXT,
                notes TEXT,
                updated_at TEXT
            );
            CREATE TABLE source_check_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                check_run_id TEXT,
                source_run_id TEXT,
                source_name TEXT,
                query TEXT,
                status TEXT,
                fetched_at TEXT,
                item_count INTEGER,
                error_text TEXT,
                raw_result_notes TEXT,
                created_at TEXT
            );
            CREATE TABLE event_clusters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cluster_record_id TEXT,
                source_run_id TEXT,
                cluster_id TEXT,
                canonical_title TEXT,
                canonical_summary TEXT,
                source_count INTEGER,
                item_count INTEGER,
                unique_source_count INTEGER,
                mainstream_source_count INTEGER,
                cluster_type TEXT,
                independent_confirmation INTEGER,
                first_seen_at TEXT,
                last_seen_at TEXT,
                dominant_keywords_json TEXT,
                candidate_event_type TEXT,
                verification_status TEXT,
                confidence REAL,
                debug_reasons_json TEXT,
                created_at TEXT
            );
            CREATE TABLE credibility_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                evidence_record_id TEXT,
                source_run_id TEXT,
                cluster_id TEXT,
                event_id TEXT,
                evidence_key TEXT,
                source_name TEXT,
                evidence_type TEXT,
                claim_text TEXT,
                supporting_item_ids_json TEXT,
                supporting_sources_json TEXT,
                consistency_status TEXT,
                official_evidence_status TEXT,
                risk_flags_json TEXT,
                note_text TEXT,
                created_at TEXT
            );
            INSERT INTO news_sources
            (source_name, source_type, enabled, region, language, credibility_base, fetch_mode, notes, updated_at)
            VALUES ('sec_press_releases', 'official', 1, 'US', 'en', 0.9, 'rss', 'SEC RSS', '2026-06-21T00:00:00Z');
            INSERT INTO source_check_runs
            (check_run_id, source_run_id, source_name, query, status, fetched_at, item_count, error_text, raw_result_notes, created_at)
            VALUES ('SRCCHK_1', 'SRCRUN_1', 'sec_press_releases', 'chip export', 'ok', '2026-06-21T00:00:00Z', 4, NULL, 'feed_url=https://www.sec.gov/news/pressreleases.rss', '2026-06-21T00:00:00Z');
            INSERT INTO event_clusters
            (cluster_record_id, source_run_id, cluster_id, canonical_title, canonical_summary, source_count, item_count, unique_source_count, mainstream_source_count, cluster_type, independent_confirmation, first_seen_at, last_seen_at, dominant_keywords_json, candidate_event_type, verification_status, confidence, debug_reasons_json, created_at)
            VALUES ('CLSTR_1', 'SRCRUN_1', 'CLUSTER_1', 'AI export control cluster', 'summary', 2, 2, 2, 1, 'multi_source_event', 1, '2026-06-21T00:00:00Z', '2026-06-21T01:00:00Z', '[\"chip\", \"export\"]', 'ai_export_control', 'multi_source_supported', 0.82, '[\"multi-source\"]', '2026-06-21T01:00:00Z');
            INSERT INTO credibility_evidence
            (evidence_record_id, source_run_id, cluster_id, event_id, evidence_key, source_name, evidence_type, claim_text, supporting_item_ids_json, supporting_sources_json, consistency_status, official_evidence_status, risk_flags_json, note_text, created_at)
            VALUES ('EVID_1', 'SRCRUN_1', 'CLUSTER_1', 'EVT_1', 'source::sec_press_releases', 'sec_press_releases', 'source_summary', 'Source classified as high.', '[\"NEWS_1\"]', '[\"sec_press_releases\"]', 'consistent', 'official_source_present', '[\"none\"]', 'official', '2026-06-21T01:00:00Z');
            """
        )
