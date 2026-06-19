"""Industry normalization based on a small alias dictionary."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from eventalpha.config import PROJECT_ROOT


class IndustryNormalizationService:
    """Normalize industry labels independently from assets and entities."""

    def __init__(
        self,
        alias_path: str | Path = "eventalpha/rules/industry_aliases.yaml",
    ) -> None:
        self.alias_path = Path(alias_path)
        if not self.alias_path.is_absolute():
            self.alias_path = PROJECT_ROOT / self.alias_path
        self.warnings: list[str] = []
        self._lookup: dict[str, str] = {}
        self._standard_names: list[str] = []
        self._load_aliases()

    @property
    def standard_names(self) -> list[str]:
        """Return standard industry names in config order."""
        return list(self._standard_names)

    def normalize_industry_name(self, name: str) -> str:
        """Normalize one industry name, preserving unknown values."""
        raw_name = str(name).strip()
        if not raw_name:
            return raw_name
        normalized = self._lookup.get(self._normalize_key(raw_name))
        if normalized:
            return normalized
        self.warnings.append(f"Unknown industry alias preserved: {raw_name}")
        return raw_name

    def normalize_industry_list(self, names: list[str]) -> list[str]:
        """Normalize and deduplicate industry names while preserving order."""
        self.warnings = []
        results: list[str] = []
        seen: set[str] = set()
        for name in names:
            normalized = self.normalize_industry_name(name)
            key = self._normalize_key(normalized)
            if normalized and key not in seen:
                results.append(normalized)
                seen.add(key)
        return results

    def _load_aliases(self) -> None:
        if not self.alias_path.exists():
            raise FileNotFoundError(f"Industry alias file not found: {self.alias_path}")
        payload = yaml.safe_load(self.alias_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Industry alias file must be a mapping: {self.alias_path}")
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

