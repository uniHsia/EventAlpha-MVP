"""Helpers for converting analysis outputs into ledger records."""

from __future__ import annotations

from eventalpha.schemas import (
    AntiSpuriousCheck,
    CausalChain,
    EventVerification,
    ImpactScore,
    MarketMapping,
    PredictedAsset,
    PredictionLedgerEntry,
    StructuredEvent,
)


def build_prediction_entry(
    event: StructuredEvent,
    verification: EventVerification,
    score: ImpactScore,
    chain: CausalChain,
    anti_spurious: AntiSpuriousCheck,
    mapping: MarketMapping,
) -> PredictionLedgerEntry:
    """Build a ledger entry from the analysis result."""
    predicted_assets = [
        PredictedAsset(
            asset_name=asset.asset_name,
            asset_type=asset.asset_type,
            direction=asset.direction,
            time_window=chain.time_horizon,
            asset_confidence=asset.confidence,
            chain_confidence=chain.confidence,
            anti_spurious_adjusted_confidence=anti_spurious.adjusted_confidence,
            final_confidence=round(asset.confidence * anti_spurious.adjusted_confidence, 4),
            confidence=round(asset.confidence * anti_spurious.adjusted_confidence, 4),
            benchmark=asset.benchmark,
        )
        for asset in mapping.mapped_assets
    ]

    return PredictionLedgerEntry(
        event_id=event.event_id,
        event_title=event.event_title,
        event_type=event.event_type,
        event_level=score.event_level,
        credibility_score=verification.credibility_score,
        impact_score=score.impact_score,
        causal_chain_ids=[chain.chain_id],
        predicted_assets=predicted_assets,
        risk_flags=verification.risk_flags + anti_spurious.issues,
    )
