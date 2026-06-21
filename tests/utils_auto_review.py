"""Test helpers for scheduler auto-review fixtures."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import PredictedAsset, PredictionLedgerEntry, RawNews
from eventalpha.schemas.base import utc_now
from eventalpha.services import LedgerService


def seed_due_review_ledger(tmp_path, *, horizon: str = "T+1") -> LedgerService:
    """Create a temp ledger with an AI-export prediction and one due task."""
    ledger = LedgerService(tmp_path / "due_review.sqlite3")
    raw_news = RawNews(**json.loads((Path(__file__).parent / "fixtures/demo_events.json").read_text(encoding="utf-8"))[0])
    result = run_event_pipeline(raw_news, ledger_service=ledger)
    prediction = result["prediction_ledger_entry"]
    task = next(task for task in ledger.get_review_tasks(prediction.prediction_id) if task.horizon == horizon)
    with ledger.repo.connect() as conn:
        conn.execute(
            "UPDATE review_tasks SET due_at = ? WHERE task_id = ?",
            ((utc_now() - timedelta(minutes=1)).isoformat(), task.task_id),
        )
        conn.commit()
    return ledger


def seed_empty_prediction_due_task(tmp_path) -> LedgerService:
    """Create a temp ledger with a due task whose prediction has no assets."""
    ledger = LedgerService(tmp_path / "empty_prediction.sqlite3")
    prediction = PredictionLedgerEntry(
        event_id="EVT_EMPTY",
        event_title="Empty prediction",
        event_type="ai_export_control",
        predicted_assets=[],
        review_schedule=["T+1"],
    )
    ledger.save_prediction_ledger(prediction)
    task = ledger.create_review_tasks(prediction)[0]
    with ledger.repo.connect() as conn:
        conn.execute(
            "UPDATE review_tasks SET due_at = ? WHERE task_id = ?",
            ((utc_now() - timedelta(minutes=1)).isoformat(), task.task_id),
        )
        conn.commit()
    return ledger


def five_demo_assets() -> list[PredictedAsset]:
    """Return five T+3-like demo assets for direct tests."""
    return [
        PredictedAsset(asset_name=f"Asset {index}", direction="up", time_window="T+3")
        for index in range(5)
    ]
