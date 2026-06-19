"""OpenAI-compatible LLM client with Pydantic validation."""

from __future__ import annotations

import json
import os
from typing import Any, TypeVar

from pydantic import BaseModel

from .errors import LLMCallError, LLMConfigurationError, LLMOutputValidationError
from .schema_utils import (
    pydantic_to_json_schema,
    schema_name,
    validate_structured_output,
)


T = TypeVar("T", bound=BaseModel)


class OpenAICompatibleLLMClient:
    """Call OpenAI-compatible chat completions and validate JSON output."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self._load_dotenv()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.provider_base_url = base_url or os.getenv("OPENAI_BASE_URL") or None
        self.model = model or os.getenv("OPENAI_MODEL") or ""
        self.last_raw_output: str | None = None
        self._client = None

        if not self.api_key:
            raise LLMConfigurationError(
                "OPENAI_API_KEY is not configured. Set it in local .env or environment."
            )
        if not self.model:
            raise LLMConfigurationError(
                "OPENAI_MODEL is not configured. Set it in local .env or pass --model."
            )

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 2,
    ) -> T:
        """Return a Pydantic object from a real OpenAI-compatible API call."""
        last_error: Exception | None = None
        for _ in range(max_retries + 1):
            raw_output = self._call_with_best_response_format(
                prompt=prompt,
                schema=schema,
                system_prompt=system_prompt,
                temperature=temperature,
            )
            try:
                self.last_raw_output = raw_output
                return validate_structured_output(raw_output, schema)
            except LLMOutputValidationError as exc:
                last_error = exc
        raise LLMOutputValidationError(str(last_error) if last_error else "LLM output failed validation")

    def _call_with_best_response_format(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: str | None,
        temperature: float,
    ) -> str:
        """Try the strictest supported structured output mode first."""
        try:
            return self._call_chat_completion(
                prompt=prompt,
                schema=schema,
                system_prompt=system_prompt,
                temperature=temperature,
                use_json_schema=True,
                include_response_format=True,
            )
        except LLMCallError as exc:
            if not self._looks_like_response_format_unsupported(exc):
                raise

        fallback_prompt = self._prompt_with_schema(prompt, schema)
        try:
            return self._call_chat_completion(
                prompt=fallback_prompt,
                schema=schema,
                system_prompt=system_prompt,
                temperature=temperature,
                use_json_schema=False,
                include_response_format=True,
            )
        except LLMCallError as exc:
            if not self._looks_like_response_format_unsupported(exc):
                raise

        return self._call_chat_completion(
            prompt=fallback_prompt,
            schema=schema,
            system_prompt=system_prompt,
            temperature=temperature,
            use_json_schema=False,
            include_response_format=False,
        )

    def _call_chat_completion(
        self,
        prompt: str,
        schema: type[BaseModel],
        system_prompt: str | None,
        temperature: float,
        use_json_schema: bool,
        include_response_format: bool = True,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        request = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if include_response_format:
            request["response_format"] = self._response_format(
                schema,
                use_json_schema=use_json_schema,
            )
        try:
            completion = self._get_client().chat.completions.create(**request)
        except Exception as exc:
            raise LLMCallError(self._sanitize_error(exc)) from exc

        try:
            content = completion.choices[0].message.content
        except Exception as exc:
            raise LLMCallError("LLM response did not contain choices[0].message.content") from exc
        if not content:
            raise LLMOutputValidationError("LLM returned empty content")
        return content

    def _response_format(self, schema: type[BaseModel], use_json_schema: bool) -> dict[str, Any]:
        if not use_json_schema:
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {
                "name": schema_name(schema),
                "schema": pydantic_to_json_schema(schema),
                "strict": True,
            },
        }

    def _prompt_with_schema(self, prompt: str, schema: type[BaseModel]) -> str:
        return (
            f"{prompt}\n\n"
            "请只返回一个 JSON object，且必须符合下面的 JSON Schema：\n"
            f"{json.dumps(pydantic_to_json_schema(schema), ensure_ascii=False)}"
        )

    def _get_client(self):
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise LLMConfigurationError("openai is not installed. Please run: pip install openai") from exc
            self._client = OpenAI(api_key=self.api_key, base_url=self.provider_base_url)
        return self._client

    def _load_dotenv(self) -> None:
        try:
            from dotenv import load_dotenv
        except ImportError:
            return
        load_dotenv()

    def _sanitize_error(self, exc: Exception) -> str:
        text = str(exc)
        if self.api_key:
            text = text.replace(self.api_key, "[REDACTED_API_KEY]")
        return text

    def _looks_like_response_format_unsupported(self, exc: Exception) -> bool:
        text = str(exc).lower()
        if "response_format" not in text:
            return False
        unsupported_markers = [
            "json_schema",
            "unsupported",
            "unavailable",
            "not support",
            "not_supported",
            "invalid_request_error",
        ]
        return any(marker in text for marker in unsupported_markers)
