"""Calibration rules for LLM anti-spurious risk tiers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from eventalpha.schemas import (
    AntiSpuriousCheck,
    CausalChain,
    EventVerification,
    MarketMapping,
    SpuriousRisk,
    StructuredEvent,
)
from eventalpha.services.asset_normalization_service import AssetNormalizationService

from .critique_compression_service import CritiqueCompressionService, normalize_text


HIGH_CONFIDENCE_STATUSES = {"confirmed", "high_confidence"}
LOW_VERIFICATION_STATUSES = {"needs_confirmation", "low_confidence", "rumor"}


@dataclass(frozen=True)
class AntiSpuriousCalibrationResult:
    """Calibrated anti-spurious risk and diagnostics."""

    spurious_risk: SpuriousRisk
    adjusted_confidence: float
    warnings: list[str] = field(default_factory=list)
    calibration_applied: bool = False


class AntiSpuriousCalibrationService:
    """Calibrate LLM anti-spurious output without replacing safety guardrails."""

    def __init__(
        self,
        asset_normalizer: AssetNormalizationService | None = None,
        critique_service: CritiqueCompressionService | None = None,
    ) -> None:
        self.asset_normalizer = asset_normalizer or AssetNormalizationService()
        self.critique_service = critique_service or CritiqueCompressionService()

    def calibrate_check(
        self,
        check: AntiSpuriousCheck,
        structured_event: StructuredEvent,
        verification: EventVerification | None,
        causal_chain: CausalChain,
        market_mapping: MarketMapping | None = None,
        extraction_warnings: list[str] | None = None,
        causal_warnings: list[str] | None = None,
        supported_assets: list[str] | None = None,
    ) -> AntiSpuriousCalibrationResult:
        """Apply conservative single-step risk calibration."""
        warnings: list[str] = []
        risk = check.spurious_risk
        adjusted = self._clamp(check.adjusted_confidence)
        warning_count = len(extraction_warnings or []) + len(causal_warnings or [])
        supported = self._supported_assets(structured_event, supported_assets)
        unsupported_mentions = self._unsupported_mentions(
            texts=check.issues + check.required_verifications,
            allowed_assets=supported | self._normalize_set(causal_chain.affected_assets),
        )
        issue_concepts = self.critique_service.issue_concepts(check.issues)
        affected_assets_supported = self._affected_assets_supported(
            causal_chain=causal_chain,
            market_mapping=market_mapping,
            supported_assets=supported,
        )
        watch_assets_in_chain = self._watch_assets_in_chain(causal_chain, market_mapping)

        floor_medium = (
            structured_event.status == "rumor"
            or (
                verification is not None
                and verification.verification_status in LOW_VERIFICATION_STATUSES
            )
            or warning_count >= 3
            or watch_assets_in_chain
            or not check.required_verifications
            or any(concept in issue_concepts for concept in self._blocked_issue_concepts())
            or len(causal_chain.logic) > 5
        )

        if floor_medium and risk == "low":
            warnings.append(
                "anti_spurious calibration applied: risk low -> medium because the case "
                "still requires conservative review"
            )
            return AntiSpuriousCalibrationResult(
                spurious_risk="medium",
                adjusted_confidence=adjusted,
                warnings=warnings,
                calibration_applied=True,
            )

        downgrade_eligible = (
            risk in {"medium", "high"}
            and structured_event.status in {"announced", "happened"}
            and verification is not None
            and verification.verification_status in HIGH_CONFIDENCE_STATUSES
            and verification.credibility_score >= 0.65
            and len(causal_chain.logic) <= 4
            and not unsupported_mentions
            and not any(concept in issue_concepts for concept in self._blocked_issue_concepts())
            and affected_assets_supported
            and adjusted >= 0.55
            and not floor_medium
        )

        if downgrade_eligible:
            target = "low" if risk == "medium" else "medium"
            warnings.append(
                "anti_spurious calibration applied: "
                f"risk {risk} -> {target} for a direct, credible, short-chain event"
            )
            return AntiSpuriousCalibrationResult(
                spurious_risk=target,
                adjusted_confidence=adjusted,
                warnings=warnings,
                calibration_applied=True,
            )

        return AntiSpuriousCalibrationResult(
            spurious_risk=risk,
            adjusted_confidence=adjusted,
            warnings=warnings,
            calibration_applied=False,
        )

    @staticmethod
    def _blocked_issue_concepts() -> set[str]:
        return {
            "insufficient_evidence",
            "priced_in",
            "asset_mapping_too_far",
            "second_order_watch",
            "direct_jump_long_chain",
            "over_optimistic_direction",
        }

    def _affected_assets_supported(
        self,
        causal_chain: CausalChain,
        market_mapping: MarketMapping | None,
        supported_assets: set[str],
    ) -> bool:
        if not causal_chain.affected_assets:
            return False
        mapped_relations = {
            normalize_text(asset.asset_name): str(asset.relation)
            for asset in (market_mapping.mapped_assets if market_mapping else [])
        }
        for asset_name in causal_chain.affected_assets:
            normalized = normalize_text(asset_name)
            relation = mapped_relations.get(normalized, "")
            if normalized in supported_assets:
                continue
            if "watch" in relation or "second_order" in relation:
                return False
            return False
        return True

    def _watch_assets_in_chain(
        self,
        causal_chain: CausalChain,
        market_mapping: MarketMapping | None,
    ) -> bool:
        if market_mapping is None:
            return False
        chain_assets = self._normalize_set(causal_chain.affected_assets)
        for asset in market_mapping.mapped_assets:
            relation = str(asset.relation)
            if normalize_text(asset.asset_name) not in chain_assets:
                continue
            if "watch" in relation or "second_order" in relation:
                return True
        return False

    def _unsupported_mentions(self, texts: list[str], allowed_assets: set[str]) -> list[str]:
        joined = " ".join(texts)
        compact = normalize_text(joined)
        mentions: list[str] = []
        for asset in self.asset_normalizer.standard_names:
            normalized = normalize_text(asset)
            if normalized in allowed_assets:
                continue
            if asset in joined or normalized in compact:
                mentions.append(asset)
        return self._unique(mentions)

    def _supported_assets(
        self,
        structured_event: StructuredEvent,
        supported_assets: list[str] | None,
    ) -> set[str]:
        base_assets = list(structured_event.affected_assets_hint) + list(supported_assets or [])
        return self._normalize_set(base_assets)

    @staticmethod
    def _normalize_set(values: list[str]) -> set[str]:
        return {normalize_text(value) for value in values if str(value).strip()}

    @staticmethod
    def _unique(values: list[str]) -> list[str]:
        results: list[str] = []
        seen: set[str] = set()
        for value in values:
            key = normalize_text(value)
            if key in seen:
                continue
            seen.add(key)
            results.append(value)
        return results

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, round(float(value), 4)))
