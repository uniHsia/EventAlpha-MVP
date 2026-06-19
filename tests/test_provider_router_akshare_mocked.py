"""ProviderRouter AkShare route tests without live network."""

from __future__ import annotations

from datetime import date

from eventalpha.data_sources import ProviderRouter
from eventalpha.schemas import PricePoint, PriceSeries


class FakeAkShareProvider:
    """Tiny fake AkShare provider for router tests."""

    def __init__(self) -> None:
        self.assets: list[str] = []

    def get_price_series(self, asset_name: str, start_date: str, end_date: str) -> PriceSeries:
        return PriceSeries(
            asset_name=asset_name,
            points=[
                PricePoint(date=date.fromisoformat(start_date), close=100.0),
                PricePoint(date=date.fromisoformat(end_date), close=101.0),
            ],
        )

    def get_asset_return(
        self,
        asset_name: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        self.assets.append(asset_name)
        return 0.03

    def get_benchmark_return(
        self,
        benchmark: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        return 0.01


def test_router_routes_akshare_asset_with_mocked_provider() -> None:
    """AkShare routes should delegate to the injected provider."""
    fake_provider = FakeAkShareProvider()
    router = ProviderRouter(
        akshare_provider=fake_provider,
        default_event_type="geopolitical_conflict",
    )

    route = router.resolve_asset("军工")
    value = router.get_asset_return("军工", "T+3", start_date="2026-06-18")

    assert route.provider == "akshare"
    assert route.proxy_asset_name == "中证军工"
    assert value == 0.03
    assert fake_provider.assets == ["中证军工"]
