"""Provider router for event-specific asset proxy mappings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from eventalpha.config import PROJECT_ROOT
from eventalpha.schemas import (
    AssetCoverageStatus,
    AssetProxyCandidate,
    AssetProxyRule,
    MarketDataError,
    PriceSeries,
    ProviderRoute,
)

from .akshare_provider import AkShareMarketDataProvider
from .base import MarketDataProvider
from .csv_provider import CSVMarketDataProvider
from .mock_provider import MockMarketDataProvider


class ProviderRouter(MarketDataProvider):
    """Route market data requests to mock, CSV, or AkShare providers."""

    def __init__(
        self,
        mock_provider: MarketDataProvider | None = None,
        csv_provider: MarketDataProvider | None = None,
        akshare_provider: MarketDataProvider | None = None,
        mapping_path: str | Path = "eventalpha/rules/asset_code_mapping.yaml",
        proxy_mapping_path: str | Path = "eventalpha/rules/event_asset_proxy_mapping.yaml",
        csv_path: str | Path = "eventalpha/examples/market_prices_demo.csv",
        default_event_type: str | None = None,
        allow_unverified: bool = False,
        trust_env: bool = True,
    ) -> None:
        self.mapping_path = self._resolve_path(mapping_path)
        self.proxy_mapping_path = self._resolve_path(proxy_mapping_path)
        self.default_event_type = default_event_type
        self.allow_unverified = allow_unverified
        self.mock_provider = mock_provider or MockMarketDataProvider()
        self.csv_provider = csv_provider or CSVMarketDataProvider(self._resolve_path(csv_path))
        self.akshare_provider = akshare_provider or AkShareMarketDataProvider(
            mapping_path=self.mapping_path,
            trust_env=trust_env,
        )
        self.asset_mapping = self._load_asset_mapping()
        self.proxy_rules = self._load_proxy_rules()
        self.alias_to_event_type = self._build_alias_map()
        self.last_route: ProviderRoute | None = None
        self.last_route_attempts: list[ProviderRoute] = []

    def resolve_asset(
        self,
        asset_name: str,
        event_type: str | None = None,
        allow_unverified: bool | None = None,
        raise_on_unusable: bool = True,
    ) -> ProviderRoute:
        """Resolve one predicted asset into a provider route."""
        routes = self.resolve_asset_candidates(
            asset_name,
            event_type=event_type,
            allow_unverified=allow_unverified,
            raise_on_unusable=False,
        )
        route = routes[0]
        if raise_on_unusable and not route.is_usable:
            raise MarketDataError(route.reason)
        return route

    def resolve_asset_candidates(
        self,
        asset_name: str,
        event_type: str | None = None,
        allow_unverified: bool | None = None,
        raise_on_unusable: bool = True,
    ) -> list[ProviderRoute]:
        """Resolve all sorted provider route candidates for one asset."""
        effective_event_type = self._resolve_event_type(event_type)
        routes = self._resolve_routes_from_proxy_mapping(asset_name, effective_event_type)
        if not routes:
            fallback_route = self._resolve_from_asset_mapping(asset_name, effective_event_type)
            routes = [fallback_route] if fallback_route else []
        if not routes:
            routes = [
                ProviderRoute(
                    asset_name=asset_name,
                    proxy_asset_name=asset_name,
                    provider="missing",
                    mapping_status="missing",
                    event_type=effective_event_type,
                    route_source="missing",
                    is_usable=False,
                    reason=f"No provider mapping found for asset: {asset_name}",
                )
            ]

        resolved_routes = [
            self._apply_usability(route, allow_unverified)
            for route in self._sort_routes(routes)
        ]
        if raise_on_unusable and not any(route.is_usable for route in resolved_routes):
            raise MarketDataError(resolved_routes[0].reason)
        return resolved_routes

    def get_asset_coverage(
        self,
        asset_name: str,
        event_type: str | None = None,
    ) -> AssetCoverageStatus:
        """Return non-throwing coverage status for one asset."""
        route = self.resolve_asset(
            asset_name,
            event_type=event_type,
            allow_unverified=False,
            raise_on_unusable=False,
        )
        routes = self.resolve_asset_candidates(
            asset_name,
            event_type=event_type,
            allow_unverified=False,
            raise_on_unusable=False,
        )
        return AssetCoverageStatus(
            event_type=route.event_type,
            asset_name=asset_name,
            proxy_asset_name=route.proxy_asset_name,
            provider=route.provider,
            mapping_status=route.mapping_status,
            validation_status=route.validation_status,
            route_source=route.route_source,
            fallback_available=len([candidate for candidate in routes if candidate.is_usable]) > 1,
            fallback_routes=routes[1:],
            is_usable=route.is_usable,
            reason=route.reason,
        )

    def get_price_series(
        self,
        asset_name: str,
        start_date: str,
        end_date: str,
        event_type: str | None = None,
    ) -> PriceSeries:
        """Return a routed price series for one predicted asset."""
        routes = self.resolve_asset_candidates(asset_name, event_type=event_type)
        return self._try_price_series_routes(routes, start_date, end_date, asset_name)

    def get_asset_return(
        self,
        asset_name: str,
        horizon: str,
        start_date: str | None = None,
        event_type: str | None = None,
    ) -> float:
        """Return a routed asset return for one predicted asset."""
        routes = self.resolve_asset_candidates(asset_name, event_type=event_type)
        return self._try_return_routes(routes, horizon, start_date, asset_name)

    def get_benchmark_return(
        self,
        benchmark: str,
        horizon: str,
        start_date: str | None = None,
    ) -> float:
        """Return a benchmark return, preferring the active asset provider."""
        active_route = self.last_route
        if active_route is not None:
            benchmark_name = active_route.benchmark or benchmark
            if benchmark_name:
                provider = self._provider_for_route(active_route)
                try:
                    return provider.get_benchmark_return(
                        benchmark_name,
                        horizon,
                        start_date=start_date,
                    )
                except MarketDataError:
                    pass

        route = self.resolve_asset(benchmark, event_type=None)
        return self._provider_for_route(route).get_benchmark_return(
            route.proxy_asset_name,
            horizon,
            start_date=start_date,
        )

    def _resolve_routes_from_proxy_mapping(
        self,
        asset_name: str,
        event_type: str | None,
    ) -> list[ProviderRoute]:
        if not event_type or event_type not in self.proxy_rules:
            return []
        candidates = [
            candidate
            for candidate in self.proxy_rules[event_type].candidates
            if candidate.asset_name == asset_name
        ]
        return [
            self._route_from_candidate(candidate, event_type, index)
            for index, candidate in enumerate(candidates)
        ]

    def _resolve_from_asset_mapping(
        self,
        asset_name: str,
        event_type: str | None,
    ) -> ProviderRoute | None:
        config = self.asset_mapping.get(asset_name)
        if not config:
            return None
        provider = config.get("provider", "missing")
        mapping_status = config.get(
            "mapping_status",
            "verified" if provider == "akshare" else "candidate",
        )
        return ProviderRoute(
            asset_name=asset_name,
            proxy_asset_name=config.get("provider_symbol", asset_name),
            provider=provider,
            provider_type=config.get("provider_type"),
            provider_symbol=config.get("provider_symbol"),
            asset_type=config.get("asset_type", "theme"),
            benchmark=config.get("benchmark"),
            direction=config.get("direction", "watch"),
            relation=config.get("relation", "asset_code_mapping"),
            confidence=float(config.get("confidence", 0.5)),
            mapping_status=mapping_status,
            validation_status=config.get("validation_status", "not_checked"),
            last_checked_at=config.get("last_checked_at"),
            last_error=config.get("last_error"),
            min_price_points=config.get("min_price_points"),
            fallback_rank=int(config.get("fallback_rank", 0)),
            event_type=event_type,
            route_source="asset_code",
            reason="Resolved from asset_code_mapping.yaml",
        )

    def _route_from_candidate(
        self,
        candidate: AssetProxyCandidate,
        event_type: str | None,
        index: int = 0,
    ) -> ProviderRoute:
        return ProviderRoute(
            asset_name=candidate.asset_name,
            proxy_asset_name=candidate.proxy_asset_name,
            provider=candidate.provider,
            provider_type=candidate.provider_type,
            provider_symbol=candidate.provider_symbol,
            asset_type=candidate.asset_type,
            benchmark=candidate.benchmark,
            direction=candidate.direction,
            relation=candidate.relation,
            confidence=candidate.confidence,
            mapping_status=candidate.mapping_status,
            validation_status=candidate.validation_status,
            last_checked_at=candidate.last_checked_at,
            last_error=candidate.last_error,
            min_price_points=candidate.min_price_points,
            fallback_rank=candidate.fallback_rank,
            event_type=event_type,
            route_source="event_proxy",
            reason=candidate.rationale or f"candidate_index={index}",
        )

    def _apply_usability(
        self,
        route: ProviderRoute,
        allow_unverified: bool | None,
    ) -> ProviderRoute:
        allow = self.allow_unverified if allow_unverified is None else allow_unverified
        allowed_status = {"verified", "candidate"}
        if allow:
            allowed_status.add("unverified")

        if route.provider in {"missing", "manual"}:
            return route.model_copy(
                update={
                    "is_usable": False,
                    "reason": route.reason or f"Provider {route.provider} is not executable",
                }
            )
        if route.mapping_status == "missing":
            return route.model_copy(
                update={
                    "is_usable": False,
                    "reason": route.reason or f"Missing mapping for {route.asset_name}",
                }
            )
        if route.mapping_status not in allowed_status:
            return route.model_copy(
                update={
                    "is_usable": False,
                    "reason": (
                        f"Mapping status {route.mapping_status} is not allowed for "
                        f"{route.asset_name}; pass --allow-unverified to include unverified mappings"
                    ),
                }
            )
        if route.provider not in {"mock", "csv", "akshare"}:
            return route.model_copy(
                update={
                    "is_usable": False,
                    "reason": f"Unsupported provider for routing: {route.provider}",
                }
            )
        return route.model_copy(update={"is_usable": True})

    def _try_return_routes(
        self,
        routes: list[ProviderRoute],
        horizon: str,
        start_date: str | None,
        asset_name: str,
    ) -> float:
        """Try route candidates until one returns a market return."""
        attempts: list[ProviderRoute] = []
        for route in routes:
            if not route.is_usable:
                attempts.append(route)
                continue
            try:
                value = self._provider_for_route(route).get_asset_return(
                    route.proxy_asset_name,
                    horizon,
                    start_date=start_date,
                )
            except (MarketDataError, RuntimeError) as exc:
                attempts.append(self._failed_route(route, exc))
                continue
            self.last_route = route
            self.last_route_attempts = attempts + [route]
            return value

        self.last_route = None
        self.last_route_attempts = attempts
        raise MarketDataError(self._all_routes_failed_message(asset_name, attempts))

    def _try_price_series_routes(
        self,
        routes: list[ProviderRoute],
        start_date: str,
        end_date: str,
        asset_name: str,
    ) -> PriceSeries:
        """Try route candidates until one returns a price series."""
        attempts: list[ProviderRoute] = []
        for route in routes:
            if not route.is_usable:
                attempts.append(route)
                continue
            try:
                series = self._provider_for_route(route).get_price_series(
                    route.proxy_asset_name,
                    start_date,
                    end_date,
                )
            except (MarketDataError, RuntimeError) as exc:
                attempts.append(self._failed_route(route, exc))
                continue
            self.last_route = route
            self.last_route_attempts = attempts + [route]
            return series

        self.last_route = None
        self.last_route_attempts = attempts
        raise MarketDataError(self._all_routes_failed_message(asset_name, attempts))

    def _failed_route(self, route: ProviderRoute, exc: Exception) -> ProviderRoute:
        return route.model_copy(
            update={
                "is_usable": False,
                "last_error": str(exc),
                "reason": str(exc),
            }
        )

    def _all_routes_failed_message(
        self,
        asset_name: str,
        attempts: list[ProviderRoute],
    ) -> str:
        details = [
            (
                f"{route.proxy_asset_name}/{route.provider}/"
                f"{route.mapping_status}/{route.validation_status}: "
                f"{route.last_error or route.reason or 'not usable'}"
            )
            for route in attempts
        ]
        return f"All provider routes failed for {asset_name}: " + " | ".join(details)

    def _provider_for_route(self, route: ProviderRoute) -> MarketDataProvider:
        if route.provider == "mock":
            return self.mock_provider
        if route.provider == "csv":
            return self.csv_provider
        if route.provider == "akshare":
            return self.akshare_provider
        raise MarketDataError(route.reason or f"Unsupported provider: {route.provider}")

    def _load_proxy_rules(self) -> dict[str, AssetProxyRule]:
        if not self.proxy_mapping_path.exists():
            return {}
        raw = yaml.safe_load(self.proxy_mapping_path.read_text(encoding="utf-8")) or {}
        rules = {}
        for event_type, payload in raw.items():
            candidates = [
                AssetProxyCandidate(event_type=event_type, **candidate)
                for candidate in payload.get("candidates", [])
            ]
            rules[event_type] = AssetProxyRule(
                event_type=event_type,
                description=payload.get("description", ""),
                aliases=payload.get("aliases", []),
                candidates=candidates,
            )
        return rules

    def _build_alias_map(self) -> dict[str, str]:
        aliases = {}
        for event_type, rule in self.proxy_rules.items():
            for alias in rule.aliases:
                aliases[alias] = event_type
        return aliases

    def _load_asset_mapping(self) -> dict[str, Any]:
        if not self.mapping_path.exists():
            return {}
        return yaml.safe_load(self.mapping_path.read_text(encoding="utf-8")) or {}

    def _resolve_event_type(self, event_type: str | None) -> str | None:
        candidate = event_type or self.default_event_type
        if candidate in self.proxy_rules:
            return candidate
        return self.alias_to_event_type.get(candidate, candidate)

    def _status_rank(self, status: str) -> int:
        return {
            "verified": 0,
            "candidate": 1,
            "unverified": 2,
            "missing": 3,
        }.get(status, 99)

    def _validation_rank(self, status: str) -> int:
        return {
            "live_ok": 0,
            "cache_only": 1,
            "not_checked": 2,
            "live_failed": 3,
        }.get(status, 99)

    def _sort_routes(self, routes: list[ProviderRoute]) -> list[ProviderRoute]:
        return [
            route
            for _, route in sorted(
                enumerate(routes),
                key=lambda item: (
                    self._status_rank(item[1].mapping_status),
                    self._validation_rank(item[1].validation_status),
                    item[1].fallback_rank,
                    -item[1].confidence,
                    item[0],
                ),
            )
        ]

    def _resolve_path(self, path: str | Path) -> Path:
        resolved = Path(path)
        if resolved.is_absolute():
            return resolved
        return PROJECT_ROOT / resolved
