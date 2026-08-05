from __future__ import annotations

from dataclasses import dataclass

from macro_engine.cache.storage import load_cache

from macro_engine.decision.alignment import (
    EvidenceAlignment,
    build_evidence_alignment,
)

from macro_engine.decision.fx import (
    build_fx_research_idea,
)
from macro_engine.decision.fx_config import (
    get_fx_config,
)
from macro_engine.decision.historical_engine import (
    load_historical_evidence,
)
from macro_engine.decision.market_context import (
    MarketContext,
    build_fx_market_context_for_asset,
)

from macro_engine.decision.historical_context import (
    HistoricalContext,
    build_historical_context,
)


from macro_engine.decision.models import ResearchIdea
from macro_engine.decision.pricing_assessment import (
    MarketPricingAssessment,
    build_market_pricing_assessment,
)

from macro_engine.decision.cross_asset.config import (
    get_cross_asset_config,
)
from macro_engine.decision.cross_asset.gold import (
    build_gold_research_idea,
)
from macro_engine.decision.cross_asset.historical import (
    load_cross_asset_historical_evidence,
)
from macro_engine.decision.market_context import (
    build_cross_asset_market_context,
)

from macro_engine.decision.cross_asset.sp500 import (
    build_sp500_research_idea,
)

from macro_engine.decision.cross_asset.us10y import (
    build_us10y_research_idea,
)

from macro_engine.decision.cross_asset.wti import (
    build_wti_research_idea,
)

from macro_engine.decision.cross_asset.dxy import (
    build_dxy_research_idea,
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


def build_cross_asset_workspace(
    asset_key: str,
    horizon_months: int = 3,
) -> DecisionWorkspaceResult:
    config = get_cross_asset_config(asset_key)

    if asset_key == "gold":
        idea = build_gold_research_idea(
            horizon_months=horizon_months,
        )

    elif asset_key == "sp500":
        idea = build_sp500_research_idea(
            horizon_months=horizon_months,
        )

    elif asset_key == "us10y":
        idea = build_us10y_research_idea(
            horizon_months=horizon_months,
        )

    elif asset_key == "wti":
        idea = build_wti_research_idea(
            horizon_months=horizon_months,
        )
        
    elif asset_key == "dxy":
        idea = build_dxy_research_idea(
            horizon_months=horizon_months,
        )

    else:
        raise ValueError(
            f"No cross-asset research model exists yet for "
            f"{asset_key}."
        )

    market = build_cross_asset_market_context(
        asset_key
    )

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
        config.environment_cache
    )

    historical_evidence = (
        load_cross_asset_historical_evidence(
            asset_key=asset_key,
            environment=usa_result.environment_label,
            horizon_months=horizon_months,
        )
    )

    historical_context = build_historical_context(
        evidence=historical_evidence,
        model_direction=idea.model_direction,
        horizon_months=horizon_months,
        primary_name="US",
        secondary_name=config.display_name,
        outcome_unit=(
            "basis_points"
            if asset_key == "us10y"
            else "percent"
        ),
        outcome_name=(
            "yield change"
            if asset_key == "us10y"
            else "return"
        ),
        require_exact_pair=False,
    )

    decision = build_decision_framework(
        idea=idea,
        market=market,
        alignment=alignment,
    )

    return DecisionWorkspaceResult(
        asset_key=config.key,
        display_name=config.display_name,
        idea=idea,
        market=market,
        alignment=alignment,
        pricing=pricing,
        historical_context=historical_context,
        decision=decision,
    )

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

def build_fx_workspace(
    asset_key: str,
    horizon_months: int = 3,
) -> DecisionWorkspaceResult:
    config = get_fx_config(asset_key)

    idea = build_fx_research_idea(
        asset_key=asset_key,
        horizon_months=horizon_months,
    )

    market = build_fx_market_context_for_asset(
        asset_key
    )

    alignment = build_evidence_alignment(
        idea=idea,
        market=market,
    )

    pricing = build_market_pricing_assessment(
        idea=idea,
        market=market,
        alignment=alignment,
    )

    base_result = load_cache(
        config.base_environment_cache
    )

    quote_result = load_cache(
        config.quote_environment_cache
    )

    primary_environment = (
        quote_result.environment_label
        if config.quote_environment_cache == "usa_environment"
        else base_result.environment_label
    )

    secondary_environment = (
        base_result.environment_label
        if config.quote_environment_cache == "usa_environment"
        else quote_result.environment_label
    )

    historical_evidence = load_historical_evidence(
        asset_key=config.key,
        primary_environment=primary_environment,
        secondary_environment=secondary_environment,
        horizon_months=horizon_months,
    )

    historical_context = build_historical_context(
        evidence=historical_evidence,
        model_direction=idea.model_direction,
        horizon_months=horizon_months,
        primary_name=config.historical_primary_name,
        secondary_name=config.historical_secondary_name,
    )

    decision = build_decision_framework(
        idea=idea,
        market=market,
        alignment=alignment,
    )

    return DecisionWorkspaceResult(
        asset_key=config.key,
        display_name=config.display_name,
        idea=idea,
        market=market,
        alignment=alignment,
        pricing=pricing,
        historical_context=historical_context,
        decision=decision,
    )

def build_gbpusd_workspace(
    horizon_months: int = 3,
) -> DecisionWorkspaceResult:
    return build_fx_workspace(
        asset_key="gbpusd",
        horizon_months=horizon_months,
    )


def build_eurusd_workspace(
    horizon_months: int = 3,
) -> DecisionWorkspaceResult:
    return build_fx_workspace(
        asset_key="eurusd",
        horizon_months=horizon_months,
    )