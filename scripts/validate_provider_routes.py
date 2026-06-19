"""Validate live provider routes for asset proxy candidates."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eventalpha.data_sources import AkShareMarketDataProvider
from eventalpha.schemas import AssetProxyCandidate, MarketDataError, RISK_DISCLAIMER


DEFAULT_MAPPING_PATH = ROOT / "eventalpha" / "rules" / "event_asset_proxy_mapping.yaml"
DEFAULT_REPORT_DIR = ROOT / "reports"


def build_validation_report(
    mapping_path: str | Path = DEFAULT_MAPPING_PATH,
    event_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    refresh_cache: bool = False,
    trust_env: bool = True,
    provider: AkShareMarketDataProvider | None = None,
) -> dict[str, Any]:
    """Validate AkShare proxy candidates and return report data."""
    mapping_path = Path(mapping_path)
    raw_mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8")) or {}
    end = date.fromisoformat(end_date) if end_date else date.today()
    start = date.fromisoformat(start_date) if start_date else end - timedelta(days=60)
    provider = provider or AkShareMarketDataProvider(
        refresh_cache=refresh_cache,
        trust_env=trust_env,
    )
    checked_at = datetime.now(timezone.utc).isoformat()
    results = []

    for current_event_type, payload in raw_mapping.items():
        if event_type and current_event_type != event_type:
            continue
        for candidate_payload in payload.get("candidates", []):
            if candidate_payload.get("provider") != "akshare":
                continue
            candidate = AssetProxyCandidate(
                event_type=current_event_type,
                **candidate_payload,
            )
            min_points = candidate.min_price_points or 5
            result = {
                "event_type": current_event_type,
                "asset_name": candidate.asset_name,
                "proxy_asset_name": candidate.proxy_asset_name,
                "provider": candidate.provider,
                "provider_type": candidate.provider_type,
                "provider_symbol": candidate.provider_symbol,
                "mapping_status": candidate.mapping_status,
                "validation_status": "not_checked",
                "price_points": 0,
                "min_price_points": min_points,
                "checked_at": checked_at,
                "error": None,
            }
            try:
                series = provider.get_price_series(
                    candidate.proxy_asset_name,
                    start.isoformat(),
                    end.isoformat(),
                )
                result["price_points"] = len(series.points)
                if len(series.points) >= min_points:
                    result["validation_status"] = "live_ok"
                else:
                    result["validation_status"] = "live_failed"
                    result["error"] = (
                        f"Insufficient price points: {len(series.points)} < {min_points}"
                    )
            except (MarketDataError, RuntimeError) as exc:
                result["validation_status"] = "live_failed"
                result["error"] = str(exc)
            results.append(result)

    summary = {
        "total_routes": len(results),
        "live_ok_count": sum(1 for item in results if item["validation_status"] == "live_ok"),
        "live_failed_count": sum(
            1 for item in results if item["validation_status"] == "live_failed"
        ),
        "not_checked_count": sum(
            1 for item in results if item["validation_status"] == "not_checked"
        ),
    }
    return {
        "generated_at": checked_at,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "results": results,
        "summary": summary,
    }


def write_validation_report(
    report: dict[str, Any],
    report_dir: str | Path = DEFAULT_REPORT_DIR,
) -> tuple[Path, Path]:
    """Write JSON and Markdown validation reports."""
    report_dir = Path(report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "provider_validation_report.json"
    md_path = report_dir / "provider_validation_report.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# Provider Validation Report",
        "",
        f"generated_at: {report['generated_at']}",
        f"window: {report['start_date']} -> {report['end_date']}",
        "",
        "## Summary",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Routes"])
    for item in report["results"]:
        lines.append(
            "- "
            f"{item['event_type']} | {item['asset_name']} -> {item['proxy_asset_name']} | "
            f"{item['provider']}:{item['provider_symbol']} | "
            f"mapping={item['mapping_status']} | "
            f"validation={item['validation_status']} | "
            f"points={item['price_points']} | "
            f"error={item['error'] or ''}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def update_yaml_validation_metadata(
    report: dict[str, Any],
    mapping_path: str | Path = DEFAULT_MAPPING_PATH,
) -> None:
    """Write validation metadata back to mapping YAML."""
    mapping_path = Path(mapping_path)
    raw_mapping = yaml.safe_load(mapping_path.read_text(encoding="utf-8")) or {}
    result_by_key = {
        (
            item["event_type"],
            item["asset_name"],
            item["proxy_asset_name"],
            str(item["provider_symbol"]),
        ): item
        for item in report["results"]
    }
    for event_type, payload in raw_mapping.items():
        for candidate in payload.get("candidates", []):
            key = (
                event_type,
                candidate.get("asset_name"),
                candidate.get("proxy_asset_name"),
                str(candidate.get("provider_symbol")),
            )
            result = result_by_key.get(key)
            if not result:
                continue
            candidate["validation_status"] = result["validation_status"]
            candidate["last_checked_at"] = result["checked_at"]
            candidate["last_error"] = result["error"]
            candidate["min_price_points"] = result["min_price_points"]
    mapping_path.write_text(
        yaml.safe_dump(raw_mapping, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def print_validation_report(report: dict[str, Any]) -> None:
    """Print a readable validation report."""
    for item in report["results"]:
        print(
            f"{item['event_type']} | "
            f"{item['asset_name']} -> {item['proxy_asset_name']} | "
            f"{item['provider']}:{item['provider_symbol']} | "
            f"mapping={item['mapping_status']} | "
            f"validation={item['validation_status']} | "
            f"price_points={item['price_points']} | "
            f"error={item['error'] or ''}"
        )
    print("\nsummary:")
    for key, value in report["summary"].items():
        print(f"{key}: {value}")
    print(RISK_DISCLAIMER)


def main() -> None:
    """Validate provider routes from the command line."""
    parser = ArgumentParser(description="Validate EventAlpha provider routes.")
    parser.add_argument("--event-type", default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--no-proxy", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--update-yaml-validation", action="store_true")
    args = parser.parse_args()

    report = build_validation_report(
        event_type=args.event_type,
        start_date=args.start_date,
        end_date=args.end_date,
        refresh_cache=args.refresh_cache,
        trust_env=not args.no_proxy,
    )
    print_validation_report(report)
    if args.write_report:
        json_path, md_path = write_validation_report(report)
        print(f"Wrote report: {json_path}")
        print(f"Wrote report: {md_path}")
    if args.update_yaml_validation:
        update_yaml_validation_metadata(report)
        print(f"Updated validation metadata: {DEFAULT_MAPPING_PATH}")


if __name__ == "__main__":
    main()
