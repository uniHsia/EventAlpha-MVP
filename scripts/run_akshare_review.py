"""Run EventAlpha-MVP review with AkShare market data."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.data_sources import AkShareMarketDataProvider
from eventalpha.orchestration import run_review_pipeline
from eventalpha.schemas import MarketDataError, PredictionLedgerEntry, RISK_DISCLAIMER
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
    """Run AkShare-backed review or standalone asset return check."""
    parser = ArgumentParser(description="Run EventAlpha-MVP AkShare review pipeline.")
    parser.add_argument("--prediction-id", default=None, help="Prediction Ledger ID.")
    parser.add_argument("--horizon", default="T+3", choices=["T+1", "T+3", "T+7"])
    parser.add_argument("--refresh-cache", action="store_true", help="Refresh AkShare cache.")
    parser.add_argument(
        "--no-proxy",
        action="store_true",
        help="Ignore proxy environment for EastMoney direct requests.",
    )
    parser.add_argument("--asset", default=None, help="Run standalone AkShare asset return check.")
    parser.add_argument("--start-date", default="2024-06-18", help="Start date for --asset mode.")
    args = parser.parse_args()

    provider = AkShareMarketDataProvider(
        refresh_cache=args.refresh_cache,
        trust_env=not args.no_proxy,
    )

    try:
        if args.asset:
            _run_asset_check(provider, args.asset, args.horizon, args.start_date)
            return

        ledger = LedgerService()
        prediction = (
            ledger.get_prediction(args.prediction_id)
            if args.prediction_id
            else ledger.get_latest_prediction()
        )
        if prediction is None:
            print("未找到 Prediction Ledger。请先运行 python scripts/run_demo_event.py")
            return

        eligible_assets = []
        skipped_assets = []
        for asset in prediction.predicted_assets:
            if provider.is_akshare_asset(asset.asset_name):
                eligible_assets.append(asset)
            else:
                skipped_assets.append(asset.asset_name)

        if skipped_assets:
            print("以下资产没有 AkShare 映射或 provider 不是 akshare，已跳过：")
            for asset_name in skipped_assets:
                print(f"- {asset_name}")
        if not eligible_assets:
            print("当前 prediction 没有可用 AkShare 资产。可使用 --asset 沪深300 单独测试。")
            print(RISK_DISCLAIMER)
            return

        akshare_prediction = prediction.model_copy(
            update={"predicted_assets": eligible_assets}
        )
        result = run_review_pipeline(
            prediction=akshare_prediction,
            ledger_service=ledger,
            market_data=provider,
            horizon=args.horizon,
        )
    except (MarketDataError, RuntimeError) as exc:
        print(f"AkShare review failed: {exc}")
        print(RISK_DISCLAIMER)
        return

    reviews = result["review_results"]
    summary = result["review_summary"]
    update = result["rule_update"]

    print(f"EventAlpha-MVP Demo: AkShare {args.horizon} 多资产复盘")
    _print_model("读取预测账本", prediction)
    print(f"\n## AkShare {args.horizon} 市场表现")
    for review in reviews:
        print(f"\n资产: {review.asset_name}")
        print(f"预测方向: {review.predicted_direction}")
        print(f"资产收益: {review.actual_return:+.2%}")
        print(f"基准: {review.benchmark}")
        print(f"基准收益: {review.benchmark_return:+.2%}")
        print(f"超额收益: {review.excess_return:+.2%}")
        print(f"方向是否正确: {review.direction_correct}")
        print(f"因果是否成立: {review.causal_validity}")
        print(f"错误类型: {review.error_type}")
    _print_model("全部资产复盘结果", reviews)
    _print_model("Aggregate Review Summary", summary)
    _print_model("规则更新结果", update)
    print(RISK_DISCLAIMER)


def _run_asset_check(
    provider: AkShareMarketDataProvider,
    asset_name: str,
    horizon: str,
    start_date: str,
) -> None:
    """Run a standalone AkShare return check for one mapped asset."""
    try:
        asset_return = provider.get_asset_return(asset_name, horizon, start_date=start_date)
        config = provider.get_asset_config(asset_name)
        benchmark_name = config.get("benchmark")
        benchmark_return = (
            provider.get_benchmark_return(benchmark_name, horizon, start_date=start_date)
            if benchmark_name
            else None
        )
    except (MarketDataError, RuntimeError) as exc:
        print(f"AkShare asset check failed: {exc}")
        print(RISK_DISCLAIMER)
        return

    print(f"AkShare asset check: {asset_name} {horizon}")
    print(f"资产收益: {asset_return:+.2%}")
    if benchmark_return is not None:
        print(f"基准: {benchmark_name}")
        print(f"基准收益: {benchmark_return:+.2%}")
        print(f"超额收益: {asset_return - benchmark_return:+.2%}")
    print(RISK_DISCLAIMER)


if __name__ == "__main__":
    main()
