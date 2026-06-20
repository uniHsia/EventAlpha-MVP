"""Tests for anti-spurious calibration service."""

from __future__ import annotations

from eventalpha.schemas import (
    AntiSpuriousCheck,
    CausalChain,
    CausalStep,
    EventVerification,
    MappedAsset,
    MarketMapping,
    StructuredEvent,
)
from eventalpha.services import AntiSpuriousCalibrationService


def _chain(event_id: str, affected_assets: list[str], steps: int = 3) -> CausalChain:
    return CausalChain(
        event_id=event_id,
        affected_assets=affected_assets,
        confidence=0.72,
        logic=[
            CausalStep(order=index + 1, description=f"step-{index + 1}")
            for index in range(steps)
        ],
    )


def test_calibration_downgrades_credible_short_chain() -> None:
    """Direct, credible, short-chain cases can move from medium to low risk."""
    service = AntiSpuriousCalibrationService()
    event = StructuredEvent(
        event_id="EVT_1",
        status="announced",
        affected_assets_hint=["Oil"],
    )
    verification = EventVerification(
        event_id="EVT_1",
        credibility_score=0.78,
        verification_status="high_confidence",
    )
    chain = _chain("EVT_1", ["Oil"], steps=3)
    mapping = MarketMapping(
        event_id="EVT_1",
        mapped_assets=[
            MappedAsset(
                asset_name="Oil",
                relation="direct_beneficiary",
                direction="up",
            )
        ],
    )
    check = AntiSpuriousCheck(
        event_id="EVT_1",
        chain_id=chain.chain_id,
        spurious_risk="medium",
        issues=["Follow up with shipment data to confirm the move."],
        required_verifications=["Check shipment data and inventory changes."],
        adjusted_confidence=0.66,
    )

    result = service.calibrate_check(
        check=check,
        structured_event=event,
        verification=verification,
        causal_chain=chain,
        market_mapping=mapping,
        supported_assets=["Oil"],
    )

    assert result.spurious_risk == "low"
    assert result.calibration_applied is True
    assert any(item.startswith("anti_spurious calibration applied:") for item in result.warnings)


def test_calibration_floors_rumor_cases_to_medium() -> None:
    """Rumor cases should not remain low risk after calibration."""
    service = AntiSpuriousCalibrationService()
    event = StructuredEvent(
        event_id="EVT_2",
        status="rumor",
        affected_assets_hint=["Oil"],
    )
    verification = EventVerification(
        event_id="EVT_2",
        credibility_score=0.48,
        verification_status="rumor",
    )
    chain = _chain("EVT_2", ["Oil"], steps=2)
    check = AntiSpuriousCheck(
        event_id="EVT_2",
        chain_id=chain.chain_id,
        spurious_risk="low",
        issues=["Need official confirmation."],
        required_verifications=["Check the official filing."],
        adjusted_confidence=0.52,
    )

    result = service.calibrate_check(
        check=check,
        structured_event=event,
        verification=verification,
        causal_chain=chain,
        supported_assets=["Oil"],
    )

    assert result.spurious_risk == "medium"
    assert result.calibration_applied is True


def test_calibration_does_not_over_downgrade_warning_heavy_cases() -> None:
    """Warning-heavy cases keep their original higher risk tier."""
    service = AntiSpuriousCalibrationService()
    event = StructuredEvent(
        event_id="EVT_3",
        status="announced",
        affected_assets_hint=["Oil"],
    )
    verification = EventVerification(
        event_id="EVT_3",
        credibility_score=0.82,
        verification_status="confirmed",
    )
    chain = _chain("EVT_3", ["Oil"], steps=3)
    check = AntiSpuriousCheck(
        event_id="EVT_3",
        chain_id=chain.chain_id,
        spurious_risk="high",
        issues=["Follow up with shipment data."],
        required_verifications=["Check shipment data."],
        adjusted_confidence=0.7,
    )

    result = service.calibrate_check(
        check=check,
        structured_event=event,
        verification=verification,
        causal_chain=chain,
        extraction_warnings=["warn-1", "warn-2"],
        causal_warnings=["warn-3"],
        supported_assets=["Oil"],
    )

    assert result.spurious_risk == "high"
    assert result.calibration_applied is False


def test_calibration_blocks_second_order_watch_assets() -> None:
    """Second-order watch assets in the active chain should block a downgrade."""
    service = AntiSpuriousCalibrationService()
    event = StructuredEvent(
        event_id="EVT_4",
        status="happened",
        affected_assets_hint=["Oil"],
    )
    verification = EventVerification(
        event_id="EVT_4",
        credibility_score=0.8,
        verification_status="high_confidence",
    )
    chain = _chain("EVT_4", ["Semiconductor Equipment"], steps=3)
    mapping = MarketMapping(
        event_id="EVT_4",
        mapped_assets=[
            MappedAsset(
                asset_name="Semiconductor Equipment",
                relation="second_order_watch",
                direction="watch",
            )
        ],
    )
    check = AntiSpuriousCheck(
        event_id="EVT_4",
        chain_id=chain.chain_id,
        spurious_risk="medium",
        issues=["Follow up with capex data."],
        required_verifications=["Check capex trends."],
        adjusted_confidence=0.68,
    )

    result = service.calibrate_check(
        check=check,
        structured_event=event,
        verification=verification,
        causal_chain=chain,
        market_mapping=mapping,
        supported_assets=["Oil"],
    )

    assert result.spurious_risk == "medium"
    assert result.calibration_applied is False
