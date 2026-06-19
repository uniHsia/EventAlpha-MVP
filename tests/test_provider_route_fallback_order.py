"""Provider route fallback ordering tests."""

from __future__ import annotations

from pathlib import Path

from eventalpha.data_sources import ProviderRouter


def _write_mapping(path: Path) -> None:
    path.write_text(
        """
test_event:
  description: test
  candidates:
    - asset_name: 测试资产
      proxy_asset_name: CSV代理
      provider: csv
      provider_symbol: 国产 AI 芯片
      asset_type: theme
      benchmark: 沪深300
      direction: up
      relation: fallback_csv
      confidence: 0.95
      mapping_status: candidate
      validation_status: cache_only
      fallback_rank: 0
      rationale: csv fallback
    - asset_name: 测试资产
      proxy_asset_name: AkShare代理
      provider: akshare
      provider_type: index
      provider_symbol: "000300"
      asset_type: index
      benchmark: 沪深300
      direction: up
      relation: primary_verified
      confidence: 0.50
      mapping_status: verified
      validation_status: live_ok
      fallback_rank: 10
      rationale: verified live route
    - asset_name: 失败资产
      proxy_asset_name: AkShare失败代理
      provider: akshare
      provider_type: index
      provider_symbol: "399967"
      asset_type: index
      benchmark: 沪深300
      direction: up
      relation: failed_verified
      confidence: 0.70
      mapping_status: verified
      validation_status: live_failed
      fallback_rank: 0
      rationale: failed live route
    - asset_name: 失败资产
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


def test_verified_live_ok_route_sorts_before_higher_confidence_candidate(tmp_path) -> None:
    """verified/live_ok should outrank candidate/cache_only despite lower confidence."""
    mapping_path = tmp_path / "proxy.yaml"
    _write_mapping(mapping_path)
    router = ProviderRouter(proxy_mapping_path=mapping_path, default_event_type="test_event")

    routes = router.resolve_asset_candidates("测试资产")

    assert [route.proxy_asset_name for route in routes[:2]] == ["AkShare代理", "CSV代理"]


def test_live_failed_verified_route_still_precedes_candidate_for_runtime_fallback(tmp_path) -> None:
    """A verified live_failed route is tried before lower mapping_status CSV fallback."""
    mapping_path = tmp_path / "proxy.yaml"
    _write_mapping(mapping_path)
    router = ProviderRouter(proxy_mapping_path=mapping_path, default_event_type="test_event")

    routes = router.resolve_asset_candidates("失败资产")

    assert [route.proxy_asset_name for route in routes[:2]] == ["AkShare失败代理", "国产 AI 芯片"]
