"""Asset name normalization based on a small alias dictionary."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from eventalpha.config import PROJECT_ROOT


class AssetNormalizationService:
    """Normalize LLM asset hints to EventAlpha standard asset names."""

    def __init__(
        self,
        alias_path: str | Path = "eventalpha/rules/asset_aliases.yaml",
    ) -> None:
        self.alias_path = Path(alias_path)
        if not self.alias_path.is_absolute():
            self.alias_path = PROJECT_ROOT / self.alias_path
        self.warnings: list[str] = []
        self._standard_names: list[str] = []
        self._lookup: dict[str, str] = {}
        self._load_aliases()

    @property
    def standard_names(self) -> list[str]:
        """Return standard asset names in config order."""
        return list(self._standard_names)

    def supported_asset_names_text(self) -> str:
        """Return a compact comma-separated list for prompts."""
        return ", ".join(self._standard_names)

    def is_known_asset(self, name: str) -> bool:
        """Return whether a name or alias is known."""
        return self._normalize_key(name) in self._lookup

    def normalize_asset_name(self, name: str) -> str:
        """Normalize one asset name, preserving unknown values."""
        raw_name = str(name).strip()
        if not raw_name:
            return raw_name
        normalized = self._lookup.get(self._normalize_key(raw_name))
        if normalized:
            return normalized
        self.warnings.append(f"Unknown asset alias preserved: {raw_name}")
        return raw_name

    def normalize_asset_list(self, names: list[str]) -> list[str]:
        """Normalize and deduplicate asset names while preserving order."""
        self.warnings = []
        results: list[str] = []
        seen: set[str] = set()
        for name in names:
            normalized = self.normalize_asset_name(name)
            key = self._normalize_key(normalized)
            if normalized and key not in seen:
                results.append(normalized)
                seen.add(key)
        return results

    def _load_aliases(self) -> None:
        if not self.alias_path.exists():
            raise FileNotFoundError(f"Asset alias file not found: {self.alias_path}")
        payload = yaml.safe_load(self.alias_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Asset alias file must be a mapping: {self.alias_path}")
        for standard_name, config in payload.items():
            standard = str(standard_name).strip()
            if not standard:
                continue
            self._standard_names.append(standard)
            self._lookup[self._normalize_key(standard)] = standard
            aliases = config.get("aliases", []) if isinstance(config, dict) else []
            for alias in aliases:
                alias_text = str(alias).strip()
                if alias_text:
                    self._lookup[self._normalize_key(alias_text)] = standard

    @staticmethod
    def _normalize_key(name: str) -> str:
        return re.sub(r"\s+", "", str(name)).casefold()

