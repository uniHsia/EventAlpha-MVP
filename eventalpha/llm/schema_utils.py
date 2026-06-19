"""Helpers for Pydantic JSON Schema and structured output validation."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from .errors import LLMOutputValidationError


T = TypeVar("T", bound=BaseModel)


def pydantic_to_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Return a strict-friendly JSON Schema for a Pydantic v2 model."""
    schema = deepcopy(model.model_json_schema())
    _require_all_properties(schema)
    _set_no_extra_properties(schema)
    return schema


def schema_name(model: type[BaseModel]) -> str:
    """Return the schema name used in prompts and API response_format."""
    return model.__name__


def validate_structured_output(raw_output: dict[str, Any] | str, schema: type[T]) -> T:
    """Validate raw dict/JSON output into a Pydantic object."""
    try:
        payload = _coerce_json_payload(raw_output)
        return schema.model_validate(payload)
    except LLMOutputValidationError:
        raise
    except ValidationError as exc:
        raise LLMOutputValidationError(summarize_validation_error(exc)) from exc
    except Exception as exc:
        raise LLMOutputValidationError(summarize_validation_error(exc)) from exc


def summarize_validation_error(exc: Exception) -> str:
    """Return a short validation error message safe for prompts and traces."""
    if isinstance(exc, ValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        loc = ".".join(str(part) for part in first.get("loc", [])) or "output"
        msg = first.get("msg", str(exc))
        return f"{loc}: {msg}"
    text = str(exc).strip()
    return text[:500] if text else exc.__class__.__name__


def _coerce_json_payload(raw_output: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(raw_output, dict):
        return raw_output
    if not isinstance(raw_output, str):
        raise LLMOutputValidationError(f"Expected dict or JSON string, got {type(raw_output).__name__}")

    text = _strip_json_fence(raw_output.strip())
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMOutputValidationError(f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise LLMOutputValidationError("Structured output must be a JSON object")
    return payload


def _strip_json_fence(text: str) -> str:
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else text


def _require_all_properties(schema: dict[str, Any]) -> None:
    properties = schema.get("properties")
    if isinstance(properties, dict) and properties:
        schema["required"] = list(properties.keys())
    for value in schema.values():
        if isinstance(value, dict):
            _require_all_properties(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _require_all_properties(item)


def _set_no_extra_properties(schema: dict[str, Any]) -> None:
    if "properties" in schema:
        schema.setdefault("additionalProperties", False)
    for value in schema.values():
        if isinstance(value, dict):
            _set_no_extra_properties(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _set_no_extra_properties(item)

