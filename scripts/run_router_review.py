"""Run mixed-provider review through ProviderRouter."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.agents.review_learning import review_asset, summarize_reviews
from eventalpha.data_sources import ProviderRouter
from eventalpha.schemas import MarketDataError, RISK_DISCLAIMER
from eventalpha.services import LedgerService, update_rule_from_review


def _print_model(title: str, value: Any) -> None:
    print(f"\n## {title}")
    print(json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2))


def _to_jsonable(value: Any) -> Any:
    """Convert Pydantic models and containers into JSON-serializable values."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def main() -> None:
    """Review the latest prediction with ProviderRouter."""
    parser = ArgumentParser(description="Run EventAlpha-MVP mixed-provider review.")
    parser.add_argument("--prediction-id", default=None, help="Prediction Ledger ID.")
    parser.add_argument("--horizon", default="T+3", choices=["T+1", "T+3", "T+7"])
    parser.add_argument("--allow-unverified", action="store_true")
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Ignore proxy environment for EastMoney direct requests.",
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
        print(RISK_DISCLAIMER)
        return

    router = ProviderRouter(
        default_event_type=prediction.event_type,
        allow_unverified=args.allow_unverified,
        trust_env=not args.no_proxy,
    )

    review_results = []
    successful_assets = []
    route_records = []
    failed_assets = []

    candidates = [
        asset for asset in prediction.predicted_assets if asset.time_window == args.horizon
    ]
    for asset in candidates:
        try:
            review = review_asset(prediction, asset, router, horizon=args.horizon)
            route_records.append(
                {
                    "asset_name": asset.asset_name,
                    "used_route": router.last_route,
                    "attempts": router.last_route_attempts,
                }
            )
            review_results.append(review)
            successful_assets.append(asset)
        except (MarketDataError, RuntimeError) as exc:
            failed_assets.append(
                {
                    "asset_name": asset.asset_name,
                    "reason": str(exc),
                    "attempts": router.last_route_attempts,
                }
            )

    success_prediction = prediction.model_copy(
        update={"predicted_assets": successful_assets}
    )
    summary = summarize_reviews(success_prediction, review_results, horizon=args.horizon)
    rule_update = update_rule_from_review(success_prediction, summary)

    for review_result in review_results:
        ledger.save_review_result(review_result)
    ledger.save_review_summary(summary)
    ledger.save_rule_update(rule_update)

    print(f"EventAlpha-MVP Demo: Router {args.horizon} mixed-provider review")
    _print_model("Prediction Ledger", prediction)
    _print_model("Provider Routes", route_records)

    print(f"\n## Router {args.horizon} 市场表现")
    for review in review_results:
        print(f"\n资产: {review.asset_name}")
        print(f"预测方向: {review.predicted_direction}")
        print(f"资产收益: {review.actual_return:+.2%}")
        print(f"基准: {review.benchmark}")
        print(f"基准收益: {review.benchmark_return:+.2%}")
        print(f"超额收益: {review.excess_return:+.2%}")
        print(f"方向是否正确: {review.direction_correct}")
        print(f"因果是否成立: {review.causal_validity}")
        print(f"错误类型: {review.error_type}")

    if failed_assets:
        _print_model("Failed Assets", failed_assets)
    _print_model("Review Results", review_results)
    _print_model("Aggregate Review Summary", summary)
    _print_model("Rule Update", rule_update)
    print(RISK_DISCLAIMER)


if __name__ == "__main__":
    main()
