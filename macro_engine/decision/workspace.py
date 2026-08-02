from __future__ import annotations

from dataclasses import dataclass

from macro_engine.cache.storage import load_cache

from macro_engine.decision.alignment import (
    EvidenceAlignment,
    build_evidence_alignment,
)


from macro_engine.decision.fx import (
    build_eurusd_research_idea,
    build_gbpusd_research_idea,
)


from macro_engine.decision.historical import (
    load_eurusd_historical_evidence,
    load_gbpusd_historical_evidence,
)

from macro_engine.decision.historical_context import (
    HistoricalContext,
    build_historical_context,
)
from macro_engine.decision.market_context import (
    MarketContext,
    build_eurusd_market_context,
    build_gbpusd_market_context,
)


from macro_engine.decision.models import ResearchIdea
from macro_engine.decision.pricing_assessment import (
    MarketPricingAssessment,
    build_market_pricing_assessment,
)


@dataclass(frozen=True)
class DecisionFramework:
    stance: str
    reason: str
    trigger: str
    invalidation: str


@dataclass(frozen=True)
class DecisionWorkspaceResult:
    asset_key: str
    display_name: str

    idea: ResearchIdea
    market: MarketContext
    alignment: EvidenceAlignment
    pricing: MarketPricingAssessment
    historical_context: HistoricalContext
    decision: DecisionFramework


def build_decision_framework(
    *,
    idea: ResearchIdea,
    market: MarketContext,
    alignment: EvidenceAlignment,
) -> DecisionFramework:
    if alignment.label == "Confirmed":
        stance = "READY FOR REVIEW"
        reason = (
            f"The {idea.model_direction.lower()} macro view is now broadly "
            "confirmed by price trend."
        )
        trigger = (
            "Complete the external news check and confirm that entry timing "
            "and risk-reward are acceptable."
        )

    elif alignment.label == "Divergent":
        stance = "WATCH"
        reason = (
            f"Macro evidence is {idea.model_direction.lower()}, but "
            f"{idea.asset} remains in an {market.trend_label.lower()}."
        )
        trigger = (
            "Price trend begins moving in the macro direction while the "
            "macro thesis remains intact."
        )

    else:
        stance = "REVIEW"
        reason = (
            "The available evidence is mixed and does not yet support a "
            "high-conviction decision."
        )
        trigger = (
            "Additional macro or price evidence creates clearer directional "
            "alignment."
        )

    if idea.model_direction == "Bearish":
        invalidation = (
            "The relative macro score returns to neutral or bullish, or "
            "the macro advantage materially weakens."
        )
    elif idea.model_direction == "Bullish":
        invalidation = (
            "The relative macro score returns to neutral or bearish, or "
            "the macro advantage materially weakens."
        )
    else:
        invalidation = (
            "No directional thesis is active until the macro score moves "
            "clearly away from neutral."
        )

    return DecisionFramework(
        stance=stance,
        reason=reason,
        trigger=trigger,
        invalidation=invalidation,
    )


def build_gbpusd_workspace(
    horizon_months: int = 3,
) -> DecisionWorkspaceResult:
    idea = build_gbpusd_research_idea(
        horizon_months=horizon_months,
    )

    market = build_gbpusd_market_context()

    alignment = build_evidence_alignment(
        idea=idea,
        market=market,
    )

    pricing = build_market_pricing_assessment(
        idea=idea,
        market=market,
        alignment=alignment,
    )

    usa_result = load_cache(
        "usa_environment"
    )

    uk_result = load_cache(
        "uk_environment"
    )

    historical_evidence = load_gbpusd_historical_evidence(
        us_environment=usa_result.environment_label,
        uk_environment=uk_result.environment_label,
        horizon_months=horizon_months,
    )

    historical_context = build_historical_context(
        evidence=historical_evidence,
        model_direction=idea.model_direction,
        horizon_months=horizon_months,
        primary_name="US",
        secondary_name="UK",
    )

    decision = build_decision_framework(
        idea=idea,
        market=market,
        alignment=alignment,
    )

    return DecisionWorkspaceResult(
        asset_key="gbpusd",
        display_name="GBP/USD",
        idea=idea,
        market=market,
        alignment=alignment,
        pricing=pricing,
        historical_context=historical_context,
        decision=decision,
    )
    
def build_eurusd_workspace(
    horizon_months: int = 3,
) -> DecisionWorkspaceResult:
    idea = build_eurusd_research_idea(
        horizon_months=horizon_months,
    )

    market = build_eurusd_market_context()

    alignment = build_evidence_alignment(
        idea=idea,
        market=market,
    )

    pricing = build_market_pricing_assessment(
        idea=idea,
        market=market,
        alignment=alignment,
    )

    usa_result = load_cache(
        "usa_environment"
    )

    euro_result = load_cache(
        "euro_environment"
    )

    historical_evidence = load_eurusd_historical_evidence(
        us_environment=usa_result.environment_label,
        euro_environment=euro_result.environment_label,
        horizon_months=horizon_months,
    )

    historical_context = build_historical_context(
        evidence=historical_evidence,
        model_direction=idea.model_direction,
        horizon_months=horizon_months,
        primary_name="US",
        secondary_name="Euro Area",
    )

    decision = build_decision_framework(
        idea=idea,
        market=market,
        alignment=alignment,
    )

    return DecisionWorkspaceResult(
        asset_key="eurusd",
        display_name="EUR/USD",
        idea=idea,
        market=market,
        alignment=alignment,
        pricing=pricing,
        historical_context=historical_context,
        decision=decision,
    )