"""LLM-specific exceptions."""

from __future__ import annotations


class LLMError(Exception):
    """Base class for LLM infrastructure errors."""


class LLMConfigurationError(LLMError):
    """Raised when required LLM configuration is missing or invalid."""


class LLMCallError(LLMError):
    """Raised when the upstream LLM call fails."""


class LLMOutputValidationError(LLMError):
    """Raised when model output cannot be validated against a schema."""

