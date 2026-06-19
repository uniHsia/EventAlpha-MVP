"""Optional LLM-backed event extraction agent."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, get_args

from eventalpha.llm import PromptTemplate, StructuredRunner, pydantic_to_json_schema
from eventalpha.schemas import EventType, RawNews, StructuredEvent
from eventalpha.schemas.base import new_id, utc_now
from eventalpha.services import AssetNormalizationService

from .extraction import RuleBasedExtractionAgent


FailureMode = Literal["strict", "fallback"]

ENTITY_COMPLETION_KEYWORDS = {
    "AI 芯片": ["AI 芯片", "AI芯片", "人工智能芯片"],
    "GPU": ["GPU"],
    "EDA": ["EDA", "电子设计自动化"],
    "服务器": ["服务器", "AI服务器", "AI 服务器"],
    "出口管制": ["出口管制"],
    "美国": ["美国"],
    "中国": ["中国"],
}


class LLMExtractionAgent:
    """Extract StructuredEvent objects with a structured LLM runner."""

    def __init__(
        self,
        runner: StructuredRunner,
        prompt_path: str | Path = "eventalpha/prompts/extraction_event.md",
        fallback_agent=None,
        failure_mode: FailureMode = "strict",
        asset_normalizer: AssetNormalizationService | None = None,
    ) -> None:
        if failure_mode not in {"strict", "fallback"}:
            raise ValueError("failure_mode must be 'strict' or 'fallback'")
        self.runner = runner
        self.prompt_path = prompt_path
        self.fallback_agent = fallback_agent or RuleBasedExtractionAgent()
        self.failure_mode = failure_mode
        self.asset_normalizer = asset_normalizer or AssetNormalizationService()
        self.warnings: list[str] = []

    def extract(self, raw_news: RawNews) -> StructuredEvent:
        """Extract a StructuredEvent from RawNews."""
        self.warnings = []
        try:
            event = self.runner.run(
                prompt=self._render_prompt(raw_news),
                output_schema=StructuredEvent,
                system_prompt=(
                    "You are an EventAlpha extraction component. "
                    "Return only schema-valid JSON and no investment advice."
                ),
                prompt_name="extraction_event",
            )
            return self._post_process(event, raw_news)
        except Exception as exc:
            if self.failure_mode == "strict":
                raise
            warning = f"LLM extraction failed; fell back to rule-based extraction: {exc}"
            self.warnings.append(warning)
            return self.fallback_agent.extract(raw_news)

    def _post_process(self, event: StructuredEvent, raw_news: RawNews) -> StructuredEvent:
        """Apply system-controlled normalization after schema validation."""
        normalized_assets = self.asset_normalizer.normalize_asset_list(event.affected_assets_hint)
        if normalized_assets != event.affected_assets_hint:
            self.warnings.append(
                "normalized affected_assets_hint: "
                f"{event.affected_assets_hint} -> {normalized_assets}"
            )
        self.warnings.extend(self.asset_normalizer.warnings)

        entities = self._complete_entities(event.entities, raw_news)
        if entities != event.entities:
            added = [item for item in entities if self._norm(item) not in {self._norm(x) for x in event.entities}]
            self.warnings.append(f"completed entities from raw text: {added}")

        event_time = event.event_time
        if event_time is not None and not self._event_time_is_explicit(event_time, raw_news):
            self.warnings.append(
                "event_time removed because the extracted date was not explicit in raw text"
            )
            event_time = None

        return event.model_copy(
            update={
                "event_id": new_id("EVT"),
                "raw_id": raw_news.raw_id,
                "created_at": utc_now(),
                "event_time": event_time,
                "affected_assets_hint": normalized_assets,
                "entities": entities,
            }
        )

    def _complete_entities(self, entities: list[str], raw_news: RawNews) -> list[str]:
        text = f"{raw_news.title} {raw_news.raw_text}"
        completed = list(entities)
        seen = {self._norm(item) for item in completed}
        for canonical, aliases in ENTITY_COMPLETION_KEYWORDS.items():
            if self._norm(canonical) in seen:
                continue
            if any(alias in text for alias in aliases):
                completed.append(canonical)
                seen.add(self._norm(canonical))
        return completed

    def _event_time_is_explicit(self, event_time, raw_news: RawNews) -> bool:
        text = f"{raw_news.title} {raw_news.raw_text}"
        candidates = {
            event_time.strftime("%Y-%m-%d"),
            event_time.strftime("%Y/%m/%d"),
            f"{event_time.year}年{event_time.month}月{event_time.day}日",
            f"{event_time.year}年{event_time.month:02d}月{event_time.day:02d}日",
            f"{event_time.month}月{event_time.day}日",
            f"{event_time.month:02d}月{event_time.day:02d}日",
        }
        if any(candidate in text for candidate in candidates):
            return True
        compact_text = re.sub(r"\s+", "", text)
        compact_candidates = {re.sub(r"\s+", "", candidate) for candidate in candidates}
        return any(candidate in compact_text for candidate in compact_candidates)

    def _render_prompt(self, raw_news: RawNews) -> str:
        template = PromptTemplate.from_file(self.prompt_path)
        return template.render(
            json_schema=json.dumps(
                pydantic_to_json_schema(StructuredEvent),
                ensure_ascii=False,
            ),
            raw_news_json=json.dumps(
                raw_news.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            raw_title=raw_news.title,
            raw_text=raw_news.raw_text,
            source=raw_news.source,
            source_type=raw_news.source_type,
            publish_time=raw_news.publish_time.isoformat(),
            supported_event_types=", ".join(get_args(EventType)),
            supported_asset_names=self.asset_normalizer.supported_asset_names_text(),
        )

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"\s+", "", str(value)).casefold()
