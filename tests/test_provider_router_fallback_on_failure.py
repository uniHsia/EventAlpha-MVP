"""ProviderRouter runtime fallback tests."""

from __future__ import annotations

from pathlib import Path

from eventalpha.data_sources import ProviderRouter
from eventalpha.schemas import MarketDataError


class FailingAkShareProvider:
    """AkShare provider stand-in that fails all requests."""

    def get_price_series(self, asset_name: str, start_date: str, end_date: str):
        raise MarketDataError("live provider failed")

    def get_asset_return(
        self,
        asset_name: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        raise MarketDataError("live provider failed")

    def get_benchmark_return(
        self,
        benchmark: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        raise MarketDataError("live provider failed")


def test_router_falls_back_to_csv_when_akshare_fails(tmp_path) -> None:
    """Router should try CSV fallback after an AkShare route raises MarketDataError."""
    proxy_mapping = tmp_path / "proxy.yaml"
    proxy_mapping.write_text(
        """
test_event:
  candidates:
    - asset_name: Fallback资产
      proxy_asset_name: AkShare代理
      provider: akshare
      provider_type: index
      provider_symbol: "399967"
      asset_type: index
      benchmark: 沪深300
      direction: up
      relation: primary
      confidence: 0.70
      mapping_status: verified
      validation_status: live_ok
      fallback_rank: 0
      rationale: primary live route
    - asset_name: Fallback资产
      proxy_asset_name: 国产 AI 芯片
      provider: csv
      provider_symbol: 国产 AI 芯片
      asset_type: theme
      benchmark: 沪深300
      direction: up
      relation: csv_fallback
      confidence: 0.60
      mapping_status: candidate
      validation_status: cache_only
      fallback_rank: 10
      rationale: csv fallback
""",
        encoding="utf-8",
    )
    csv_path = Path(__file__).parent / "fixtures" / "market_prices_demo.csv"
    router = ProviderRouter(
        proxy_mapping_path=proxy_mapping,
        csv_path=csv_path,
        akshare_provider=FailingAkShareProvider(),
        default_event_type="test_event",
    )

    value = router.get_asset_return("Fallback资产", "T+3", start_date="2026-06-18")

    assert value > 0
    assert router.last_route is not None
    assert router.last_route.provider == "csv"
    assert router.last_route.proxy_asset_name == "国产 AI 芯片"
    assert router.last_route_attempts[0].provider == "akshare"
    assert router.last_route_attempts[0].last_error == "live provider failed"
