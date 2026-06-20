"""Helpers for compacting anti-spurious critiques and EventCard text."""

from __future__ import annotations

import re
from dataclasses import dataclass


ISSUE_KEYWORDS: dict[str, tuple[int, tuple[str, ...]]] = {
    "insufficient_evidence": (
        100,
        (
            "insufficient evidence",
            "lack evidence",
            "no evidence",
            "missing evidence",
            "证据不足",
            "缺少证据",
            "未经证实",
            "未获证实",
            "尚未确认",
        ),
    ),
    "priced_in": (
        90,
        (
            "priced in",
            "priced-in",
            "already priced",
            "提前定价",
            "提前反映",
            "市场已反映",
            "预期充分",
        ),
    ),
    "asset_mapping_too_far": (
        80,
        (
            "unsupported asset",
            "unsupported assets",
            "mapping too far",
            "asset mapping too far",
            "too far mapping",
            "unsupported mapping",
            "映射过远",
            "资产映射过远",
            "不支持资产",
            "过远映射",
        ),
    ),
    "second_order_watch": (
        70,
        (
            "second-order",
            "second order",
            "secondorder",
            "watch asset",
            "watch-only",
            "二阶",
            "二级",
            "观察资产",
            "间接映射",
        ),
    ),
    "direct_jump_long_chain": (
        60,
        (
            "direct jump",
            "jump directly",
            "too long chain",
            "long chain",
            "causal chain too long",
            "direct leap",
            "直接跳",
            "链条过长",
            "因果链过长",
            "链路过长",
        ),
    ),
    "over_optimistic_direction": (
        50,
        (
            "over-optimistic",
            "too optimistic",
            "direction too strong",
            "mixed/watch",
            "mixed or watch",
            "过度乐观",
            "方向过强",
            "过度自信",
            "应降为 mixed",
            "应降为 watch",
        ),
    ),
}

VERIFICATION_KEYWORDS: dict[str, tuple[int, tuple[str, ...]]] = {
    "official_evidence": (
        100,
        (
            "official",
            "official filing",
            "official notice",
            "regulator",
            "公告",
            "官方",
            "监管",
            "文件",
            "披露",
        ),
    ),
    "order_bid_capex_production": (
        90,
        (
            "order",
            "orders",
            "bid",
            "bidding",
            "capex",
            "capital expenditure",
            "production",
            "shipment",
            "inventory",
            "订单",
            "招标",
            "资本开支",
            "产能",
            "出货",
            "库存",
        ),
    ),
    "mapping_validation": (
        80,
        (
            "asset mapping",
            "proxy",
            "supplier list",
            "customer list",
            "watch asset",
            "mapping validation",
            "映射",
            "代理资产",
            "供应商名单",
            "客户名单",
            "二阶",
        ),
    ),
    "macro_confirmation": (
        70,
        (
            "yield curve",
            "fx",
            "exchange rate",
            "inflation",
            "employment",
            "oil price",
            "gold price",
            "freight rate",
            "收益率曲线",
            "汇率",
            "通胀",
            "就业",
            "油价",
            "金价",
            "运价",
        ),
    ),
}

GENERIC_FOLLOW_UP_KEYWORDS = (
    "follow up",
    "follow-up",
    "following up",
    "keep following",
    "continue to monitor",
    "need validation",
    "needs validation",
    "requires validation",
    "further verification",
    "more checks",
    "需跟踪",
    "需验证",
    "后续验证",
    "继续观察",
    "持续观察",
    "持续跟踪",
)

SEVERE_ISSUE_CONCEPTS = {
    "insufficient_evidence",
    "priced_in",
    "asset_mapping_too_far",
    "second_order_watch",
    "direct_jump_long_chain",
    "over_optimistic_direction",
}


@dataclass(frozen=True)
class CritiqueCompressionResult:
    """Compressed anti-spurious critique."""

    issues: list[str]
    required_verifications: list[str]
    raw_issue_count: int
    raw_required_verification_count: int


@dataclass(frozen=True)
class _RankedText:
    text: str
    concept: str
    score: int
    is_generic: bool
    index: int


class CritiqueCompressionService:
    """Deduplicate and prioritize anti-spurious critique text."""

    def compress_anti_spurious(
        self,
        issues: list[str],
        required_verifications: list[str],
        issue_limit: int = 5,
        verification_limit: int = 5,
    ) -> CritiqueCompressionResult:
        """Compress issues and required verifications with concept-aware ranking."""
        cleaned_issues = self._compress_texts(
            texts=issues,
            concept_map=ISSUE_KEYWORDS,
            limit=issue_limit,
        )
        cleaned_required = self._compress_texts(
            texts=required_verifications,
            concept_map=VERIFICATION_KEYWORDS,
            limit=verification_limit,
        )
        return CritiqueCompressionResult(
            issues=cleaned_issues,
            required_verifications=cleaned_required,
            raw_issue_count=len([item for item in issues if str(item).strip()]),
            raw_required_verification_count=len(
                [item for item in required_verifications if str(item).strip()]
            ),
        )

    def compact_event_card_risk_factors(
        self,
        risk_flags: list[str],
        anti_spurious_issues: list[str],
        limit: int = 6,
    ) -> list[str]:
        """Keep policy risk flags and only the top anti-spurious issues."""
        compact_issues = self._compress_texts(
            texts=anti_spurious_issues,
            concept_map=ISSUE_KEYWORDS,
            limit=max(limit, 1),
        )
        combined = self._stable_unique(list(risk_flags) + compact_issues)
        return combined[:limit]

    def compact_event_card_verification_indicators(
        self,
        watch_indicators: list[str],
        required_verifications: list[str],
        limit: int = 8,
    ) -> list[str]:
        """Compact market indicators and required verifications together."""
        combined = self._compress_texts(
            texts=list(required_verifications) + list(watch_indicators),
            concept_map=VERIFICATION_KEYWORDS,
            limit=limit,
        )
        if combined:
            return combined[:limit]
        return self._stable_unique(list(watch_indicators) + list(required_verifications))[:limit]

    def is_severe_issue(self, text: str) -> bool:
        """Return whether a text maps to a high-severity anti-spurious concept."""
        return classify_issue_concept(text) in SEVERE_ISSUE_CONCEPTS

    def issue_concepts(self, texts: list[str]) -> set[str]:
        """Return recognized issue concepts for a list of texts."""
        return {
            classify_issue_concept(text)
            for text in texts
            if classify_issue_concept(text) != "other"
        }

    def _compress_texts(
        self,
        texts: list[str],
        concept_map: dict[str, tuple[int, tuple[str, ...]]],
        limit: int,
    ) -> list[str]:
        ranked = self._rank_texts(texts, concept_map)
        if not ranked:
            return []

        generics = [item for item in ranked if item.is_generic]
        specific = [item for item in ranked if not item.is_generic]
        selected = specific or generics[:1]
        selected.sort(key=lambda item: (-item.score, item.index))
        return [item.text for item in selected[:limit]]

    def _rank_texts(
        self,
        texts: list[str],
        concept_map: dict[str, tuple[int, tuple[str, ...]]],
    ) -> list[_RankedText]:
        best_by_concept: dict[str, _RankedText] = {}
        seen_texts: set[str] = set()

        for index, value in enumerate(texts):
            text = str(value).strip()
            if not text:
                continue
            normalized = normalize_text(text)
            if normalized in seen_texts:
                continue
            seen_texts.add(normalized)
            concept, base_score = classify_text(text, concept_map)
            generic = is_generic_follow_up(text)
            score = base_score + min(len(text), 20)
            candidate = _RankedText(
                text=text,
                concept=concept if not generic else f"{concept}:generic",
                score=score,
                is_generic=generic,
                index=index,
            )
            current = best_by_concept.get(candidate.concept)
            if current is None or candidate.score > current.score:
                best_by_concept[candidate.concept] = candidate

        return list(best_by_concept.values())

    @staticmethod
    def _stable_unique(values: list[str]) -> list[str]:
        items: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value).strip()
            if not text:
                continue
            key = normalize_text(text)
            if key in seen:
                continue
            seen.add(key)
            items.append(text)
        return items


def classify_issue_concept(text: str) -> str:
    """Expose issue concept matching for calibration rules."""
    concept, _ = classify_text(text, ISSUE_KEYWORDS)
    return concept


def classify_text(
    text: str,
    concept_map: dict[str, tuple[int, tuple[str, ...]]],
) -> tuple[str, int]:
    """Return the first matching concept and priority score."""
    normalized = normalize_text(text)
    best_concept = "other"
    best_score = 20
    for concept, (priority, keywords) in concept_map.items():
        if any(normalize_text(keyword) in normalized for keyword in keywords):
            if priority > best_score:
                best_concept = concept
                best_score = priority
    return best_concept, best_score


def is_generic_follow_up(text: str) -> bool:
    """Return whether a text is mostly a generic follow-up reminder."""
    normalized = normalize_text(text)
    return any(normalize_text(keyword) in normalized for keyword in GENERIC_FOLLOW_UP_KEYWORDS)


def normalize_text(text: str) -> str:
    """Normalize whitespace and case for heuristic matching."""
    return re.sub(r"\s+", "", str(text)).casefold()
