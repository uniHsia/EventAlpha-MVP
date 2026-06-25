"""Push outbox generation for local subscription matching."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel, new_id, utc_now

from .subscription import Subscriber


class PushMessage(EventAlphaModel):
    """One generated push message in the local outbox."""

    message_id: str = Field(default_factory=lambda: new_id("PUSH"))
    subscriber_id: str
    event_id: str | None = None
    title: str
    summary: str
    reason: str
    channel: str
    status: str = "pending"
    created_at: str = Field(default_factory=lambda: utc_now().isoformat())


PRIORITY_RANK = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1, "高": 4}


def match_event_to_subscribers(
    event_card: dict[str, Any],
    subscribers: list[Subscriber],
) -> list[tuple[Subscriber, str]]:
    """Return subscribers whose local preferences match an EventCard."""
    results: list[tuple[Subscriber, str]] = []
    for subscriber in subscribers:
        if not subscriber.enabled:
            continue
        if not _priority_passes(event_card, subscriber.min_priority):
            continue
        reason = _match_reason(event_card, subscriber)
        if reason:
            results.append((subscriber, reason))
    return results


def build_push_message(
    event_card: dict[str, Any],
    subscriber: Subscriber,
    *,
    reason: str,
) -> PushMessage:
    """Build one pending local push message."""
    return PushMessage(
        subscriber_id=subscriber.subscriber_id,
        event_id=_value(event_card, "事件ID", "event_id"),
        title=_value(event_card, "标题", "event_title") or "未记录事件",
        summary=_value(event_card, "一句话摘要", "one_sentence", "摘要") or "暂无摘要",
        reason=reason,
        channel=subscriber.channel,
        status="pending",
    )


def write_push_outbox(
    messages: list[PushMessage],
    *,
    reports_dir: str | Path = "reports",
    report_date: date | None = None,
    demo_mode: bool = False,
) -> dict[str, str]:
    """Write local push outbox files."""
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    stamp = (report_date or date.today()).strftime("%Y%m%d")
    json_path = reports_path / f"push_outbox_{stamp}.json"
    md_path = reports_path / f"push_outbox_{stamp}.md"
    payload = {
        "generated_at": utc_now().isoformat(),
        "demo_mode": demo_mode,
        "message_count": len(messages),
        "channel_note": "微信通道当前为 placeholder，已完成订阅匹配与推送消息生成。",
        "messages": [message.model_dump(mode="json") for message in messages],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_push_outbox_markdown(messages, demo_mode=demo_mode), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def render_push_outbox_markdown(messages: list[PushMessage], *, demo_mode: bool = False) -> str:
    """Render the local outbox as Markdown."""
    lines = [
        "# EventAlpha 推送 Outbox",
        "",
        f"- generated_at: {utc_now().isoformat()}",
        f"- demo_mode: {str(demo_mode).lower()}",
        f"- message_count: {len(messages)}",
        "- channel_note: 微信通道当前为 placeholder，已完成订阅匹配与推送消息生成。",
        "",
        "| Subscriber | Channel | Status | Event | Reason |",
        "|---|---|---|---|---|",
    ]
    for message in messages:
        lines.append(
            f"| {_md(message.subscriber_id)} | {_md(message.channel)} | {_md(message.status)} | "
            f"{_md(message.title)} | {_md(message.reason)} |"
        )
    if not messages:
        lines.append("| -- | -- | -- | 暂无待推送消息 | 未命中订阅条件 |")
    return "\n".join(lines).strip() + "\n"


def _match_reason(event_card: dict[str, Any], subscriber: Subscriber) -> str | None:
    text = _event_text(event_card)
    for keyword in subscriber.keywords:
        if keyword and keyword.casefold() in text:
            return f"命中关键词：{keyword}"
    for asset in subscriber.assets:
        if asset and asset.casefold() in text:
            return f"命中资产：{asset}"
    for industry in subscriber.industries:
        if industry and industry.casefold() in text:
            return f"命中行业：{industry}"
    event_type = _value(event_card, "事件类型", "event_type")
    if event_type and event_type in subscriber.event_types:
        return f"命中事件类型：{event_type}"
    return None


def _priority_passes(event_card: dict[str, Any], min_priority: str) -> bool:
    level = _value(event_card, "事件等级", "event_level") or "D"
    return PRIORITY_RANK.get(level, 0) >= PRIORITY_RANK.get(min_priority, 0)


def _event_text(event_card: dict[str, Any]) -> str:
    values = [
        event_card.get("标题"),
        event_card.get("event_title"),
        event_card.get("一句话摘要"),
        event_card.get("one_sentence"),
        event_card.get("事件类型"),
        event_card.get("event_type"),
        " ".join(event_card.get("可能影响资产") or event_card.get("possible_impacts") or []),
        " ".join(event_card.get("风险因素") or event_card.get("risk_factors") or []),
        " ".join(event_card.get("后续验证指标") or event_card.get("verification_indicators") or []),
    ]
    return " ".join(str(value or "") for value in values).casefold()


def _value(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in {None, "", "未记录", "暂无", "--"}:
            return str(value)
    return None


def _md(value: Any) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ")
