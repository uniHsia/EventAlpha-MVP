"""Evidence annotations for EventCard causal chains."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from eventalpha.schemas.base import EventAlphaModel


class CausalEvidenceItem(EventAlphaModel):
    """Evidence status for one causal-chain step."""

    chain_id: str
    step: str
    evidence_type: str
    evidence_text: str
    source: str | None = None
    confidence_adjustment: float = 0.0
    verification_needed: bool = False
    verification_indicator: str | None = None


class CausalEvidenceSummary(EventAlphaModel):
    """Evidence summary attached to a current EventCard."""

    event_id: str | None = None
    event_title: str = "未记录"
    items: list[CausalEvidenceItem] = Field(default_factory=list)
    verification_indicators: list[str] = Field(default_factory=list)
    source_kind: str = "real"
    source_label: str = "Causal Evidence Layer"
    notes: list[str] = Field(default_factory=list)


def build_causal_evidence_summary(
    event_card: dict[str, Any],
    *,
    historical_cases: list[dict[str, Any]] | None = None,
    review_results: list[dict[str, Any]] | None = None,
    ledger_rows: list[dict[str, Any]] | None = None,
) -> CausalEvidenceSummary:
    """Build evidence annotations from already-loaded local data."""
    title = _value(event_card, "标题", "event_title") or "未记录"
    event_id = _value(event_card, "事件ID", "event_id")
    chain_steps = _list_value(event_card, "因果链摘要", "causal_chain_summary")
    sources = _list_value(event_card, "信息来源", "sources")
    verification_indicators = _list_value(event_card, "后续验证指标", "verification_indicators", "验证指标")
    assets = _list_value(event_card, "可能影响资产", "possible_impacts")
    historical = historical_cases or []
    reviews = review_results or []
    ledger = ledger_rows or []

    if not chain_steps:
        chain_steps = [title]
    items: list[CausalEvidenceItem] = []
    for index, step in enumerate(chain_steps):
        if index == 0 and sources:
            items.append(
                CausalEvidenceItem(
                    chain_id=f"{event_id or 'CHAIN'}_{index}",
                    step=str(step),
                    evidence_type="source",
                    evidence_text=f"EventCard 记录了 {len(sources)} 个信息来源。",
                    source=", ".join(str(item) for item in sources[:3]),
                    confidence_adjustment=0.02,
                    verification_needed=False,
                    verification_indicator=None,
                )
            )
            continue
        matched_case = _match_historical_case(step, title, historical)
        if matched_case:
            items.append(
                CausalEvidenceItem(
                    chain_id=f"{event_id or 'CHAIN'}_{index}",
                    step=str(step),
                    evidence_type="historical_case",
                    evidence_text=f"历史案例中存在相近事件：{matched_case.get('案例名称') or matched_case.get('title') or matched_case.get('case_id')}",
                    source=matched_case.get("source_label") or matched_case.get("来源标签") or "Historical Case Store",
                    confidence_adjustment=0.01,
                    verification_needed=True,
                    verification_indicator=_indicator_for_step(step, verification_indicators),
                )
            )
            continue
        matched_ledger = _match_ledger(step, assets, ledger)
        if matched_ledger:
            items.append(
                CausalEvidenceItem(
                    chain_id=f"{event_id or 'CHAIN'}_{index}",
                    step=str(step),
                    evidence_type="market_data",
                    evidence_text=f"Prediction Ledger 已记录相关资产映射：{matched_ledger.get('资产') or matched_ledger.get('asset_name')}",
                    source=matched_ledger.get("source_label") or "Prediction Ledger",
                    confidence_adjustment=0.01,
                    verification_needed=True,
                    verification_indicator=_indicator_for_step(step, verification_indicators),
                )
            )
            continue
        matched_review = _match_review(step, assets, reviews)
        if matched_review:
            items.append(
                CausalEvidenceItem(
                    chain_id=f"{event_id or 'CHAIN'}_{index}",
                    step=str(step),
                    evidence_type="market_data",
                    evidence_text=f"ReviewResult 已有相关资产复盘：{matched_review.get('资产') or matched_review.get('asset_name')}",
                    source=matched_review.get("source_label") or "ReviewResult",
                    confidence_adjustment=0.01 if matched_review.get("因果有效性") == "valid" else -0.02,
                    verification_needed=True,
                    verification_indicator=_indicator_for_step(step, verification_indicators),
                )
            )
            continue
        evidence_type = "assumption" if index < len(chain_steps) - 1 else "missing"
        items.append(
            CausalEvidenceItem(
                chain_id=f"{event_id or 'CHAIN'}_{index}",
                step=str(step),
                evidence_type=evidence_type,
                evidence_text="当前本地数据尚不能直接证明该传导步骤。",
                source=None,
                confidence_adjustment=-0.01 if evidence_type == "missing" else 0.0,
                verification_needed=True,
                verification_indicator=_indicator_for_step(step, verification_indicators),
            )
        )

    return CausalEvidenceSummary(
        event_id=event_id,
        event_title=title,
        items=items,
        verification_indicators=verification_indicators,
        source_kind=event_card.get("source_kind") or "real",
        source_label="Causal Evidence Layer",
        notes=["证据层仅使用本地已加载数据；缺证据时标注 assumption / missing。"],
    )


def _value(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value not in {None, "", "未记录", "暂无", "--"}:
            return str(value)
    return None


def _list_value(row: dict[str, Any], *keys: str) -> list[str]:
    for key in keys:
        value = row.get(key)
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip() and value not in {"未记录", "暂无", "--"}:
            return [value]
    return []


def _match_historical_case(step: Any, title: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    text = f"{step} {title}".casefold()
    for row in rows:
        haystack = " ".join(
            str(value)
            for value in [
                row.get("案例名称"),
                row.get("title"),
                row.get("事件类型"),
                row.get("event_type"),
                row.get("摘要"),
                row.get("summary"),
                " ".join(row.get("因果链摘要") or row.get("causal_chain_summary") or []),
            ]
        ).casefold()
        if any(token and token in haystack for token in _tokens(text)):
            return row
    return None


def _match_ledger(step: Any, assets: list[str], rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    text = f"{step} {' '.join(assets)}".casefold()
    for row in rows:
        haystack = f"{row.get('事件') or row.get('event_title') or ''} {row.get('资产') or row.get('asset_name') or ''}".casefold()
        if any(token and token in haystack for token in _tokens(text)):
            return row
    return None


def _match_review(step: Any, assets: list[str], rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    text = f"{step} {' '.join(assets)}".casefold()
    for row in rows:
        haystack = f"{row.get('资产') or row.get('asset_name') or ''} {row.get('复盘解释') or ''}".casefold()
        if any(token and token in haystack for token in _tokens(text)):
            return row
    return None


def _indicator_for_step(step: Any, indicators: list[str]) -> str | None:
    if indicators:
        return indicators[0]
    text = str(step or "").strip()
    return f"继续验证：{text}" if text else "继续验证相关政策、订单、价格和公告。"


def _tokens(text: str) -> list[str]:
    raw = str(text or "").replace("/", " ").replace("_", " ").split()
    tokens = [item.strip().casefold() for item in raw if len(item.strip()) >= 2]
    return tokens[:12]
