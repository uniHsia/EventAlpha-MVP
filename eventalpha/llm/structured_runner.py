"""Structured LLM runner with bounded retry, repair prompt, and tracing."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from .base import LLMClient
from .errors import LLMOutputValidationError
from .schema_utils import schema_name, summarize_validation_error
from .trace import LLMTraceWriter, summarize_raw_output


T = TypeVar("T", bound=BaseModel)


class StructuredRunner:
    """Run a structured LLM call and return a validated Pydantic object."""

    def __init__(
        self,
        client: LLMClient,
        trace_writer: LLMTraceWriter | None = None,
    ) -> None:
        self.client = client
        self.trace_writer = trace_writer or LLMTraceWriter()

    def run(
        self,
        prompt: str,
        output_schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 2,
        prompt_name: str | None = None,
    ) -> T:
        """Call the client with bounded repair retries."""
        current_prompt = prompt
        last_error: Exception | None = None
        total_attempts = max_retries + 1

        for attempt in range(total_attempts):
            try:
                result = self.client.generate_structured(
                    prompt=current_prompt,
                    schema=output_schema,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_retries=0,
                )
                self._trace(
                    prompt_name=prompt_name,
                    schema=output_schema,
                    success=True,
                    validation_error=None,
                    retry_count=attempt,
                )
                return result
            except LLMOutputValidationError as exc:
                last_error = exc
                if attempt >= max_retries:
                    self._trace(
                        prompt_name=prompt_name,
                        schema=output_schema,
                        success=False,
                        validation_error=str(exc),
                        retry_count=attempt,
                    )
                    raise
                current_prompt = self._build_repair_prompt(prompt, exc)

        raise LLMOutputValidationError(str(last_error) if last_error else "LLM output failed")

    def _build_repair_prompt(self, original_prompt: str, error: Exception) -> str:
        return (
            "上一次输出未通过 JSON Schema 校验。请只返回符合 schema 的 JSON，不要解释。\n\n"
            "错误摘要：\n"
            f"{summarize_validation_error(error)}\n\n"
            "原任务：\n"
            f"{original_prompt}"
        )

    def _trace(
        self,
        prompt_name: str | None,
        schema: type[BaseModel],
        success: bool,
        validation_error: str | None,
        retry_count: int,
    ) -> None:
        self.trace_writer.write(
            {
                "model": getattr(self.client, "model", "unknown"),
                "provider_base_url": getattr(self.client, "provider_base_url", None),
                "prompt_name": prompt_name,
                "schema_name": schema_name(schema),
                "success": success,
                "validation_error": validation_error,
                "retry_count": retry_count,
                "raw_output": summarize_raw_output(getattr(self.client, "last_raw_output", None)),
            }
        )

