"""Common LLM client protocol."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    """Protocol for clients that only return validated structured objects."""

    def generate_structured(
        self,
        prompt: str,
        schema: type[T],
        system_prompt: str | None = None,
        temperature: float = 0.0,
        max_retries: int = 2,
    ) -> T:
        """Return a Pydantic object matching ``schema``."""
        ...

