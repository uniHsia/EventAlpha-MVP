from __future__ import annotations

from eventalpha.orchestration.event_pipeline import should_write_prediction_ledger
from eventalpha.schemas import EventCard, EventVerification, MarketMapping, RawNews


class _Mapping:
    mapped_assets = []


class _Prediction:
    predicted_assets = []


def test_d_level_no_assets_does_not_write_ledger() -> None:
    allowed, status, _ = should_write_prediction_ledger(
        event_card=EventCard(event_id="EVT_1", event_title="Observation", event_level="D", possible_impacts=[]),
        market_mapping=_Mapping(),
        verification=EventVerification(event_id="EVT_1", credibility_score=0.7, verification_status="confirmed"),
        raw_news=RawNews(raw_text="test", metadata={}),
        prediction_entry=_Prediction(),
    )
    assert allowed is False
    assert status == "skipped_low_event_level"


def test_low_confidence_does_not_write_ledger() -> None:
    allowed, status, _ = should_write_prediction_ledger(
        event_card=EventCard(event_id="EVT_1", event_title="Low confidence", event_level="A", possible_impacts=["AI chips"]),
        market_mapping=_Mapping(),
        verification=EventVerification(event_id="EVT_1", credibility_score=0.4, verification_status="single_source_low_confidence"),
        raw_news=RawNews(raw_text="test", metadata={}),
        prediction_entry=_Prediction(),
    )
    assert allowed is False
    assert status == "skipped_low_confidence"


def test_sufficient_quality_with_assets_writes_ledger() -> None:
    class _GoodMapping:
        mapped_assets = [object()]

    class _GoodPrediction:
        predicted_assets = [object()]

    allowed, status, _ = should_write_prediction_ledger(
        event_card=EventCard(event_id="EVT_1", event_title="Qualified", event_level="A", possible_impacts=["AI chips"]),
        market_mapping=_GoodMapping(),
        verification=EventVerification(event_id="EVT_1", credibility_score=0.68, verification_status="multi_source_observed"),
        raw_news=RawNews(raw_text="test", metadata={"cluster_type": "multi_source_event"}),
        prediction_entry=_GoodPrediction(),
    )
    assert allowed is True
    assert status == "written"
