"""Simple prompt template loader and renderer."""

from __future__ import annotations

from pathlib import Path

from eventalpha.config import PROJECT_ROOT


class PromptTemplate:
    """Markdown prompt with simple ``str.format`` variable substitution."""

    def __init__(self, template: str) -> None:
        self.template = template

    @classmethod
    def from_file(cls, path: str | Path) -> "PromptTemplate":
        """Load a prompt template from disk."""
        resolved = Path(path)
        if not resolved.is_absolute():
            resolved = PROJECT_ROOT / resolved
        if not resolved.exists():
            raise FileNotFoundError(f"Prompt template not found: {resolved}")
        return cls(resolved.read_text(encoding="utf-8"))

    def render(self, **kwargs: object) -> str:
        """Render the template and raise a clear error for missing variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as exc:
            missing = str(exc).strip("'")
            raise ValueError(f"Missing prompt template variable: {missing}") from exc

