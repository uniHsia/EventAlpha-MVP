"""Event-type-specific entity keyword completion from raw text."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from eventalpha.config import PROJECT_ROOT


class EntityKeywordCompletionService:
    """Complete missing entities only when configured keywords appear in raw text."""

    def __init__(
        self,
        keyword_path: str | Path = "eventalpha/rules/entity_keywords.yaml",
    ) -> None:
        self.keyword_path = Path(keyword_path)
        if not self.keyword_path.is_absolute():
            self.keyword_path = PROJECT_ROOT / self.keyword_path
        self.warnings: list[str] = []
        self._keywords = self._load_keywords()

    def complete_entities(
        self,
        event_type: str,
        existing_entities: list[str],
        raw_title: str,
        raw_text: str,
    ) -> list[str]:
        """Append configured keywords that are explicitly present in title or text."""
        self.warnings = []
        completed = list(existing_entities)
        seen = {self._normalize_key(item) for item in completed}
        text = f"{raw_title} {raw_text}"
        compact_text = self._normalize_key(text)

        added: list[str] = []
        for keyword in self._keywords.get(str(event_type), []):
            keyword_key = self._normalize_key(keyword)
            if keyword_key in seen:
                continue
            if keyword in text or keyword_key in compact_text:
                completed.append(keyword)
                seen.add(keyword_key)
                added.append(keyword)

        if added:
            self.warnings.append(
                "Completed entities from event-type keywords: " + ", ".join(added)
            )
        return completed

    def _load_keywords(self) -> dict[str, list[str]]:
        if not self.keyword_path.exists():
            raise FileNotFoundError(f"Entity keyword file not found: {self.keyword_path}")
        payload = yaml.safe_load(self.keyword_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"Entity keyword file must be a mapping: {self.keyword_path}")
        keywords: dict[str, list[str]] = {}
        for event_type, items in payload.items():
            if not isinstance(items, list):
                raise ValueError(f"Entity keywords for {event_type} must be a list")
            keywords[str(event_type)] = [str(item).strip() for item in items if str(item).strip()]
        return keywords

    @staticmethod
    def _normalize_key(value: str) -> str:
        return re.sub(r"\s+", "", str(value)).casefold()
