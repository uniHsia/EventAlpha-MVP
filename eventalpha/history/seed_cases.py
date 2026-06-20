"""Seed historical cases for MVP demos and tests."""

from __future__ import annotations

from datetime import date

from .schemas import HistoricalCase, HistoricalCausalAssessment, HistoricalOutcome


def build_seed_historical_cases() -> list[HistoricalCase]:
    """Build deterministic illustrative historical cases."""
    return [
        _case(
            title="US advanced chip export controls reshape AI hardware supply chains",
            event_type="ai_export_control",
            event_date=date(2022, 10, 7),
            region="US/China",
            summary="Illustrative case for advanced AI chip export controls and domestic substitution attention.",
            entities=["US Commerce Department", "China", "AI chip vendors"],
            industries=["semiconductors", "AI infrastructure"],
            affected_assets=["AI chips", "semiconductor equipment", "domestic semiconductor substitutes"],
            tags=["export_control", "AI_chip", "semiconductor"],
            causal_chain_summary=[
                "Policy restriction changes cross-border supply expectations.",
                "Advanced GPU availability becomes a constraint.",
                "Domestic substitution and equipment themes receive attention.",
            ],
            market_reaction_summary="Manual seed example: semiconductor supply-chain themes showed uneven reactions across short windows.",
            lessons=[
                "Separate direct chip restrictions from second-order equipment or EDA mapping.",
                "Check whether market pricing already reflected policy rumors.",
            ],
        ),
        _case(
            title="Middle East conflict raises oil supply risk premium",
            event_type="geopolitical_conflict",
            event_date=date(2023, 10, 9),
            region="Middle East",
            summary="Illustrative case for geopolitical conflict and crude oil risk premium.",
            entities=["Middle East producers", "shipping routes"],
            industries=["energy", "shipping"],
            affected_assets=["crude oil", "energy equities", "shipping"],
            tags=["conflict", "oil", "risk_premium"],
            causal_chain_summary=[
                "Conflict raises supply disruption risk.",
                "Oil market prices a geopolitical premium.",
                "Energy and shipping assets react to logistics uncertainty.",
            ],
            market_reaction_summary="Manual seed example: oil-related assets can react quickly, but reversals occur if supply disruption does not materialize.",
            lessons=[
                "Distinguish actual supply loss from risk-premium headlines.",
                "Watch shipping, inventory, and official production signals.",
            ],
        ),
        _case(
            title="Central bank rate cut supports duration-sensitive assets",
            event_type="rate_policy",
            event_date=date(2020, 3, 3),
            region="US",
            summary="Illustrative case for emergency monetary easing and cross-asset repricing.",
            entities=["Federal Reserve"],
            industries=["banks", "growth equities", "bonds"],
            affected_assets=["bonds", "growth equities", "banks", "USD"],
            tags=["rate_cut", "central_bank", "liquidity"],
            causal_chain_summary=[
                "Policy rate cut lowers discount-rate expectations.",
                "Duration-sensitive assets may benefit.",
                "Bank margins and currency effects can diverge.",
            ],
            market_reaction_summary="Manual seed example: rate cuts can support duration assets, but crisis context may dominate.",
            lessons=[
                "Rate cuts are not automatically risk-on when recession fear is rising.",
                "Separate policy impulse from macro stress backdrop.",
            ],
        ),
        _case(
            title="Federal Reserve holds rates steady while guidance stays restrictive",
            event_type="rate_policy",
            event_date=date(2023, 9, 20),
            region="US",
            summary="Illustrative case for unchanged rates with hawkish guidance.",
            entities=["Federal Reserve", "FOMC"],
            industries=["bonds", "banks", "technology"],
            affected_assets=["Treasury yields", "growth equities", "USD"],
            tags=["fed_hold", "guidance", "rates"],
            causal_chain_summary=[
                "Policy rate remains unchanged.",
                "Forward guidance shifts expected path.",
                "Yields and duration equities react to guidance rather than the headline hold.",
            ],
            market_reaction_summary="Manual seed example: a rate hold can still tighten financial conditions if guidance is hawkish.",
            lessons=[
                "Do not treat hold decisions as neutral without reading guidance.",
                "Market reaction often depends on dot plot and press conference language.",
            ],
        ),
        _case(
            title="Tariff announcement pressures import-reliant supply chains",
            event_type="trade_tariff",
            event_date=date(2018, 3, 22),
            region="US/China",
            summary="Illustrative case for tariff policy and supply-chain repricing.",
            entities=["United States", "China", "manufacturers"],
            industries=["manufacturing", "retail", "industrial goods"],
            affected_assets=["importers", "domestic substitutes", "industrial exporters"],
            tags=["tariff", "trade_policy", "supply_chain"],
            causal_chain_summary=[
                "Tariff raises expected import costs.",
                "Margin pressure hits import-reliant firms.",
                "Domestic substitutes may receive attention.",
            ],
            market_reaction_summary="Manual seed example: tariff headlines can create dispersion between importers and substitute suppliers.",
            lessons=[
                "Map exposure by cost structure, not only industry label.",
                "Retaliation risk can reverse first-order conclusions.",
            ],
        ),
        _case(
            title="Japan earthquake disrupts semiconductor materials supply chain",
            event_type="earthquake_supply_chain",
            event_date=date(2011, 3, 11),
            region="Japan",
            summary="Illustrative case for natural disaster and upstream electronics material disruption.",
            entities=["Japan", "semiconductor suppliers"],
            industries=["semiconductors", "autos", "electronics"],
            affected_assets=["semiconductor materials", "auto supply chain", "electronics"],
            tags=["earthquake", "supply_chain", "semiconductor"],
            causal_chain_summary=[
                "Earthquake disrupts upstream production and logistics.",
                "Component shortage risk spreads to downstream manufacturers.",
                "Substitute suppliers may gain attention if capacity is available.",
            ],
            market_reaction_summary="Manual seed example: supply-chain disruption effects depend on inventory buffers and restart speed.",
            lessons=[
                "Verify factory status and inventory coverage before extending the chain.",
                "Disaster impact often varies sharply by component bottleneck.",
            ],
        ),
        _case(
            title="Breakthrough AI model launch accelerates compute infrastructure demand",
            event_type="technology_breakthrough",
            event_date=date(2022, 11, 30),
            region="Global",
            summary="Illustrative case for a technology breakthrough increasing AI compute expectations.",
            entities=["AI labs", "cloud providers", "GPU vendors"],
            industries=["AI software", "cloud", "semiconductors"],
            affected_assets=["AI software", "cloud capex", "GPUs", "data centers"],
            tags=["AI", "technology_breakthrough", "cloud"],
            causal_chain_summary=[
                "New model demonstrates stronger capability.",
                "Enterprise AI adoption expectations rise.",
                "Compute, data center, and software themes receive attention.",
            ],
            market_reaction_summary="Manual seed example: infrastructure beneficiaries can react more strongly than application names in early phases.",
            lessons=[
                "Separate durable adoption from launch hype.",
                "Track cloud capex and GPU order signals.",
            ],
        ),
        _case(
            title="Red Sea shipping attacks increase rerouting and freight cost concerns",
            event_type="geopolitical_conflict",
            event_date=date(2023, 12, 18),
            region="Red Sea",
            summary="Illustrative case for shipping route disruption and logistics cost pass-through.",
            entities=["Red Sea shippers", "container carriers"],
            industries=["shipping", "logistics", "retail"],
            affected_assets=["shipping rates", "container carriers", "importers", "oil"],
            tags=["red_sea", "shipping", "conflict"],
            causal_chain_summary=[
                "Attacks raise route safety concerns.",
                "Ships reroute around longer paths.",
                "Freight rates and delivery times become verification indicators.",
            ],
            market_reaction_summary="Manual seed example: shipping rates may react before broader import-price data confirms impact.",
            lessons=[
                "Watch actual rerouting and freight indices.",
                "Avoid assuming all importers face the same pass-through.",
            ],
        ),
        _case(
            title="Election result changes renewable energy policy expectations",
            event_type="election_policy",
            event_date=date(2020, 11, 4),
            region="US",
            summary="Illustrative case for election-driven policy expectation changes.",
            entities=["US administration", "renewable energy firms"],
            industries=["renewable energy", "utilities", "autos"],
            affected_assets=["renewables", "EV supply chain", "traditional energy"],
            tags=["election", "policy", "renewables"],
            causal_chain_summary=[
                "Election changes policy probability distribution.",
                "Subsidy and regulation expectations shift.",
                "Sector winners and losers reprice before legislation is finalized.",
            ],
            market_reaction_summary="Manual seed example: policy expectation trades can front-run actual legislation and later fade.",
            lessons=[
                "Track legislative feasibility, not just campaign pledges.",
                "Policy beneficiaries can become crowded quickly.",
            ],
        ),
        _case(
            title="Cloud providers raise AI capital expenditure plans",
            event_type="cloud_ai_capex",
            event_date=date(2024, 4, 25),
            region="US",
            summary="Illustrative case for cloud AI capex guidance and compute supply-chain demand.",
            entities=["cloud providers", "GPU vendors", "data center operators"],
            industries=["cloud", "semiconductors", "data centers", "power equipment"],
            affected_assets=["cloud capex", "GPUs", "data centers", "power equipment"],
            tags=["AI_capex", "cloud", "GPU", "data_center"],
            causal_chain_summary=[
                "Cloud guidance raises AI infrastructure demand expectations.",
                "GPU and networking demand assumptions are revised.",
                "Power, cooling, and data center constraints become second-order checks.",
            ],
            market_reaction_summary="Manual seed example: capex guidance can support supplier sentiment, but margin concerns may offset cloud names.",
            lessons=[
                "Validate capex with orders, backlog, and supplier commentary.",
                "Separate cloud customer margin pressure from supplier revenue upside.",
            ],
        ),
    ]


def _case(
    *,
    title: str,
    event_type: str,
    event_date: date,
    region: str,
    summary: str,
    entities: list[str],
    industries: list[str],
    affected_assets: list[str],
    tags: list[str],
    causal_chain_summary: list[str],
    market_reaction_summary: str,
    lessons: list[str],
) -> HistoricalCase:
    return HistoricalCase(
        title=title,
        event_type=event_type,
        event_date=event_date,
        region=region,
        summary=summary,
        entities=entities,
        industries=industries,
        affected_assets=affected_assets,
        causal_chain_summary=causal_chain_summary,
        source_notes=[
            "MVP illustrative seed case for workflow demonstration.",
            "Outcome values are manual examples, not verified investment returns.",
        ],
        tags=tags + ["manual_seed_demo"],
        outcome=HistoricalOutcome(
            benchmark="illustrative benchmark",
            asset_returns={
                asset: {"T+1": 0.0, "T+3": 0.0, "T+7": 0.0}
                for asset in affected_assets[:3]
            },
            market_reaction_summary=market_reaction_summary,
            outcome_quality="manual_seed_demo",
        ),
        causal_assessment=HistoricalCausalAssessment(
            expected_direction="mixed",
            realized_direction="mixed",
            causal_validity="partially_valid",
            what_worked=causal_chain_summary[:2],
            what_failed=["Manual seed requires real-market validation in a later phase."],
            lessons=lessons,
        ),
    )
