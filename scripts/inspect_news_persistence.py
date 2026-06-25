"""Read-only inspection for persisted news/source clustering runs."""

from __future__ import annotations

import sqlite3
import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.config import get_db_path  # noqa: E402


def inspect_latest_run(db_path: str | Path | None = None) -> dict[str, object]:
    """Return latest source_run_id persistence stats without mutating state."""
    path = Path(db_path) if db_path else Path(get_db_path())
    if not path.exists():
        return {"status": "empty", "message": f"No SQLite database found at {path}."}

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        latest = conn.execute(
            """
            SELECT source_run_id, MAX(fetched_at) AS fetched_at
            FROM source_check_runs
            WHERE source_run_id IS NOT NULL
            GROUP BY source_run_id
            ORDER BY fetched_at DESC, source_run_id DESC
            LIMIT 1
            """
        ).fetchone()
        if latest is None or not latest["source_run_id"]:
            return {"status": "empty", "message": "No source_run_id records found in SQLite."}
        source_run_id = latest["source_run_id"]

        def _count(query: str) -> int:
            row = conn.execute(query, (source_run_id,)).fetchone()
            return int(row[0] or 0) if row is not None else 0

        gate_rows = conn.execute(
            """
            SELECT prediction_gate_status, COUNT(*) AS count
            FROM event_cards
            WHERE event_id IN (
                SELECT e.event_id
                FROM events e
                JOIN raw_news r ON r.raw_id = e.raw_id
                WHERE r.source_run_id = ?
            )
            GROUP BY prediction_gate_status
            ORDER BY count DESC, prediction_gate_status ASC
            """,
            (source_run_id,),
        ).fetchall()

        return {
            "status": "ok",
            "latest_source_run_id": source_run_id,
            "latest_checked_at": latest["fetched_at"],
            "news_sources_count": conn.execute("SELECT COUNT(*) FROM news_sources").fetchone()[0],
            "source_check_runs_count": _count("SELECT COUNT(*) FROM source_check_runs WHERE source_run_id = ?"),
            "raw_news_items_count": _count("SELECT COUNT(*) FROM raw_news_items WHERE source_run_id = ?"),
            "event_clusters_count": _count("SELECT COUNT(*) FROM event_clusters WHERE source_run_id = ?"),
            "cluster_news_links_count": _count("SELECT COUNT(*) FROM cluster_news_links WHERE source_run_id = ?"),
            "credibility_evidence_count": _count("SELECT COUNT(*) FROM credibility_evidence WHERE source_run_id = ?"),
            "event_cards_with_source_evidence_count": conn.execute(
                """
                SELECT COUNT(*)
                FROM event_cards
                WHERE event_id IN (
                    SELECT e.event_id
                    FROM events e
                    JOIN raw_news r ON r.raw_id = e.raw_id
                    WHERE r.source_run_id = ?
                )
                AND source_evidence_json IS NOT NULL
                AND source_evidence_json != '[]'
                """,
                (source_run_id,),
            ).fetchone()[0],
            "ledger_predictions_created_count": conn.execute(
                """
                SELECT COUNT(*)
                FROM prediction_ledger
                WHERE event_id IN (
                    SELECT e.event_id
                    FROM events e
                    JOIN raw_news r ON r.raw_id = e.raw_id
                    WHERE r.source_run_id = ?
                )
                """,
                (source_run_id,),
            ).fetchone()[0],
            "skipped_ledger_count": sum(
                int(row["count"] or 0)
                for row in gate_rows
                if row["prediction_gate_status"] and row["prediction_gate_status"] != "written"
            ),
            "skipped_ledger_reason_breakdown": {
                str(row["prediction_gate_status"] or "unknown"): int(row["count"] or 0)
                for row in gate_rows
                if row["prediction_gate_status"] and row["prediction_gate_status"] != "written"
            },
        }


def main() -> None:
    parser = ArgumentParser(description="Inspect latest persisted source_run_id in SQLite.")
    parser.add_argument("--latest", action="store_true", help="Inspect the latest source_run_id.")
    parser.add_argument("--db-path", default=None, help="Optional SQLite path override.")
    args = parser.parse_args()

    result = inspect_latest_run(args.db_path)
    if result.get("status") != "ok":
        print(result.get("message") or "No persisted news run data.")
        return

    print(f"latest_source_run_id: {result['latest_source_run_id']}")
    print(f"latest_checked_at: {result['latest_checked_at']}")
    print(f"news_sources count: {result['news_sources_count']}")
    print(f"source_check_runs count: {result['source_check_runs_count']}")
    print(f"raw_news_items count: {result['raw_news_items_count']}")
    print(f"event_clusters count: {result['event_clusters_count']}")
    print(f"cluster_news_links count: {result['cluster_news_links_count']}")
    print(f"credibility_evidence count: {result['credibility_evidence_count']}")
    print(f"event_cards with source_evidence count: {result['event_cards_with_source_evidence_count']}")
    print(f"ledger predictions created count: {result['ledger_predictions_created_count']}")
    print(f"skipped ledger count: {result['skipped_ledger_count']}")
    print(f"skipped ledger reason breakdown: {result['skipped_ledger_reason_breakdown']}")


if __name__ == "__main__":
    main()
