"""Report file writing helpers for daily briefings."""

from __future__ import annotations

import json
from pathlib import Path

from .markdown_renderer import MarkdownBriefingRenderer
from .schemas import DailyBriefing


class JSONBriefingWriter:
    """Write Markdown and JSON briefing artifacts."""

    def __init__(self, reports_dir: str | Path = "reports") -> None:
        self.reports_dir = Path(reports_dir)

    def write(
        self,
        briefing: DailyBriefing,
        *,
        markdown: str | None = None,
    ) -> dict[str, Path]:
        """Write briefing Markdown and JSON files."""
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        stamp = briefing.briefing_date.strftime("%Y%m%d")
        md_path = self.reports_dir / f"daily_briefing_{stamp}.md"
        json_path = self.reports_dir / f"daily_briefing_{stamp}.json"
        md_text = markdown if markdown is not None else MarkdownBriefingRenderer().render(briefing)
        md_path.write_text(md_text, encoding="utf-8")
        json_path.write_text(
            json.dumps(briefing.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"markdown": md_path, "json": json_path}
