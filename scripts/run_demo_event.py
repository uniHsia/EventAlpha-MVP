"""Run the EventAlpha-MVP single-event demo."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.orchestration import run_event_pipeline
from eventalpha.schemas import RawNews
from eventalpha.services import LedgerService


def _print_model(title: str, value) -> None:
    print(f"\n## {title}")
    print(json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2))


def _to_jsonable(value):
    """Convert Pydantic models and lists into JSON-serializable values."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def main() -> None:
    """Run the first demo event through the full mock pipeline."""
    parser = ArgumentParser(description="Run EventAlpha-MVP mock event pipeline.")
    parser.add_argument("--case", type=int, default=0, help="Demo event index, 0-based.")
    parser.add_argument("--all", action="store_true", help="Run all bundled demo events.")
    args = parser.parse_args()

    demo_path = ROOT / "eventalpha" / "examples" / "demo_events.json"
    data = json.loads(demo_path.read_text(encoding="utf-8"))
    ledger = LedgerService()
    selected = data if args.all else [data[args.case]]

    for index, item in enumerate(selected):
        raw_news = RawNews(**item)
        result = run_event_pipeline(raw_news, ledger_service=ledger)

        print("EventAlpha-MVP Demo: 单事件分析最小闭环")
        print(f"\n## Demo Case {index if args.all else args.case}: {raw_news.title}")
        print("\n## 原始事件文本")
        print(raw_news.raw_text)
        _print_model("抽取后的结构化事件", result["structured_event"])
        _print_model("可信度", result["verification"])
        _print_model("事件评分", result["impact_score"])
        _print_model("因果链", result["causal_chain"])
        _print_model("伪相关检查", result["anti_spurious_check"])
        _print_model("资产映射", result["market_mapping"])
        _print_model("事件卡片", result["event_card"])
        _print_model("Prediction Ledger", result["prediction_ledger_entry"])
        _print_model("生成的 Review Tasks", result["review_tasks"])
        print(f"\nPrediction Ledger ID: {result['prediction_ledger_entry'].prediction_id}")


if __name__ == "__main__":
    main()
