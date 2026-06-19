"""Optional LLM-backed event extraction agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, get_args

from eventalpha.llm import PromptTemplate, StructuredRunner, pydantic_to_json_schema
from eventalpha.schemas import EventType, RawNews, StructuredEvent

from .extraction import RuleBasedExtractionAgent


FailureMode = Literal["strict", "fallback"]


class LLMExtractionAgent:
    """Extract StructuredEvent objects with a structured LLM runner."""

    def __init__(
        self,
        runner: StructuredRunner,
        prompt_path: str | Path = "eventalpha/prompts/extraction_event.md",
        fallback_agent=None,
        failure_mode: FailureMode = "strict",
    ) -> None:
        if failure_mode not in {"strict", "fallback"}:
            raise ValueError("failure_mode must be 'strict' or 'fallback'")
        self.runner = runner
        self.prompt_path = prompt_path
        self.fallback_agent = fallback_agent or RuleBasedExtractionAgent()
        self.failure_mode = failure_mode
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
            return event.model_copy(update={"raw_id": raw_news.raw_id})
        except Exception as exc:
            if self.failure_mode == "strict":
                raise
            warning = f"LLM extraction failed; fell back to rule-based extraction: {exc}"
            self.warnings.append(warning)
            return self.fallback_agent.extract(raw_news)

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
        )

