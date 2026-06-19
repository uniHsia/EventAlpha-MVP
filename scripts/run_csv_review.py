"""Run the EventAlpha-MVP CSV market data review demo."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.data_sources import CSVMarketDataProvider
from eventalpha.orchestration import run_review_pipeline
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
    """Review the latest ledger entry with local CSV price data."""
    parser = ArgumentParser(description="Run EventAlpha-MVP CSV review pipeline.")
    parser.add_argument("--prediction-id", default=None, help="Prediction Ledger ID.")
    parser.add_argument("--horizon", default="T+3", choices=["T+1", "T+3", "T+7"])
    parser.add_argument(
        "--csv-path",
        default=str(ROOT / "eventalpha" / "examples" / "market_prices_demo.csv"),
        help="Path to market price CSV.",
    )
    args = parser.parse_args()

    ledger = LedgerService()
    prediction = (
        ledger.get_prediction(args.prediction_id)
        if args.prediction_id
        else ledger.get_latest_prediction()
    )
    if prediction is None:
        print("未找到 Prediction Ledger。请先运行 python scripts/run_demo_event.py")
        return

    provider = CSVMarketDataProvider(args.csv_path)
    result = run_review_pipeline(
        prediction=prediction,
        ledger_service=ledger,
        market_data=provider,
        horizon=args.horizon,
    )
    reviews = result["review_results"]
    summary = result["review_summary"]
    update = result["rule_update"]

    print(f"EventAlpha-MVP Demo: CSV {args.horizon} 多资产复盘")
    _print_model("读取预测账本", prediction)
    print(f"\n## CSV {args.horizon} 市场表现")
    for review in reviews:
        print(f"\n资产: {review.asset_name}")
        print(f"预测方向: {review.predicted_direction}")
        print(f"资产收益: {review.actual_return:+.2%}")
        print(f"基准: {review.benchmark}")
        print(f"基准收益: {review.benchmark_return:+.2%}")
        print(f"超额收益: {review.excess_return:+.2%}")
        print(f"是否计入方向判断: {review.is_directional_call}")
        print(f"方向是否正确: {review.direction_correct}")
        print(f"因果是否成立: {review.causal_validity}")
        print(f"错误类型: {review.error_type}")
    _print_model("全部资产复盘结果", reviews)
    _print_model("Aggregate Review Summary", summary)
    _print_model("规则更新结果", update)


if __name__ == "__main__":
    main()
