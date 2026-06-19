"""JSONL trace writer for LLM calls."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eventalpha.config import PROJECT_ROOT


class LLMTraceWriter:
    """Append trace records to JSONL files for auditability."""

    def __init__(
        self,
        trace_dir: str | Path = "data/llm_traces",
        enabled: bool = True,
    ) -> None:
        self.trace_dir = self._resolve_path(trace_dir)
        self.enabled = enabled

    def write(self, record: dict[str, Any]) -> None:
        """Append one JSONL trace record."""
        if not self.enabled:
            return
        timestamp = datetime.now(timezone.utc)
        payload = {
            "timestamp": timestamp.isoformat(),
            **record,
        }
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        path = self.trace_dir / f"{timestamp.strftime('%Y%m%d')}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _resolve_path(self, path: str | Path) -> Path:
        resolved = Path(path)
        return resolved if resolved.is_absolute() else PROJECT_ROOT / resolved


def summarize_raw_output(raw_output: Any, limit: int = 2000) -> str | None:
    """Return a bounded raw output preview for traces."""
    if raw_output is None:
        return None
    if isinstance(raw_output, str):
        text = raw_output
    else:
        text = json.dumps(raw_output, ensure_ascii=False, default=str)
    return text[:limit]

