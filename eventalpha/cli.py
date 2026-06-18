"""Minimal package CLI entrypoint."""

from __future__ import annotations

import json
from pathlib import Path

from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews
from eventalpha.services import LedgerService


def main() -> None:
    """Run the bundled demo event through the package entrypoint."""
    root = Path(__file__).resolve().parent
    demo_path = root / "examples" / "demo_events.json"
    data = json.loads(demo_path.read_text(encoding="utf-8"))
    result = run_event_pipeline(RawNews(**data[0]), ledger_service=LedgerService())
    card = result["event_card"]
    prediction = result["prediction_ledger_entry"]
    print(card.one_sentence)
    print(f"Prediction Ledger ID: {prediction.prediction_id}")


if __name__ == "__main__":
    main()
