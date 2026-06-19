"""Provider validation report tests."""

from __future__ import annotations

import json
from datetime import date

from eventalpha.schemas import PricePoint, PriceSeries
from scripts.validate_provider_routes import build_validation_report, write_validation_report


class FakeLiveProvider:
    """Return a deterministic live-like price series."""

    def get_price_series(self, asset_name: str, start_date: str, end_date: str) -> PriceSeries:
        return PriceSeries(
            asset_name=asset_name,
            points=[
                PricePoint(date=date(2024, 1, 1), close=100),
                PricePoint(date=date(2024, 1, 2), close=101),
                PricePoint(date=date(2024, 1, 3), close=102),
                PricePoint(date=date(2024, 1, 4), close=103),
                PricePoint(date=date(2024, 1, 5), close=104),
            ],
        )


def test_provider_validation_report_builds_and_writes(tmp_path) -> None:
    """Validation report should summarize successful mocked AkShare routes."""
    mapping_path = tmp_path / "proxy.yaml"
    mapping_path.write_text(
        """
test_event:
  candidates:
    - asset_name: 测试资产
      proxy_asset_name: 沪深300
      provider: akshare
      provider_type: index
      provider_symbol: "000300"
      asset_type: index
      benchmark: 沪深300
      direction: neutral
      relation: test
      confidence: 0.7
      mapping_status: verified
      validation_status: not_checked
      min_price_points: 5
      fallback_rank: 0
      rationale: test route
""",
        encoding="utf-8",
    )

    report = build_validation_report(
        mapping_path=mapping_path,
        start_date="2024-01-01",
        end_date="2024-01-10",
        provider=FakeLiveProvider(),  # type: ignore[arg-type]
    )
    json_path, md_path = write_validation_report(report, tmp_path / "reports")

    assert report["summary"]["total_routes"] == 1
    assert report["summary"]["live_ok_count"] == 1
    assert report["results"][0]["price_points"] == 5
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary"]["live_ok_count"] == 1
    assert "Provider Validation Report" in md_path.read_text(encoding="utf-8")
