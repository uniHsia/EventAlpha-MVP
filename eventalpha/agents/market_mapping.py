"""Rule-seed based mock market mapping agent."""

from __future__ import annotations

from pathlib import Path

import yaml

from eventalpha.config import get_rules_dir
from eventalpha.schemas import CausalChain, MappedAsset, MarketMapping, StructuredEvent


def _load_mapping_rules(rules_dir: Path | None = None) -> dict:
    rules_dir = rules_dir or get_rules_dir()
    path = rules_dir / "asset_mapping_seed.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def map_event_to_markets(
    event: StructuredEvent,
    chain: CausalChain,
    rules_dir: Path | None = None,
) -> MarketMapping:
    """Map an event to observable market directions from seed rules."""
    rules = _load_mapping_rules(rules_dir)
    config = rules.get(event.event_type, {})
    assets = [
        MappedAsset(
            asset_name=item["asset_name"],
            asset_type=item.get("asset_type", "theme"),
            direction=item.get("direction", "mixed"),
            relation=item.get("relation", "watch"),
            rationale=item.get("rationale", ""),
            benchmark=item.get("benchmark", "沪深300"),
            confidence=item.get("confidence", chain.confidence),
        )
        for item in config.get("assets", [])
    ]
    return MarketMapping(
        event_id=event.event_id,
        mapped_assets=assets,
        watch_indicators=config.get("watch_indicators", []),
        mapping_notes="第一版使用 seed rules 进行 mock 映射，不构成投资建议。",
    )
