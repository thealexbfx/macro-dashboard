from __future__ import annotations

from macro_engine.cache.storage import load_cache
from macro_engine.decision.cross_asset.base import (
    CrossAssetModelSpec,
    add_cross_asset_historical_evidence,
    build_cross_asset_research_idea,
    clamp,
)
from macro_engine.decision.cross_asset.factors import (
    AssetFactor,
)
from macro_engine.models.environment import (
    MacroEnvironmentResult,
)


WTI_MODEL_SPEC = CrossAssetModelSpec(
    asset_key="wti",
    display_name="WTI",
    factor_weights={
        "wti_growth_demand": 0.35,
        "wti_inflation_momentum": 0.20,
        "wti_liquidity_support": 0.20,
        "wti_policy_pressure": 0.15,
        "wti_macro_quality": 0.10,
    },
    bullish_thesis=(
        "The combined WTI factor model currently produces a "
        "provisional bullish bias over a {horizon_months}-month "
        "horizon. Growth demand, inflation momentum, liquidity, "
        "policy conditions and macro quality are assessed together."
    ),
    bearish_thesis=(
        "The combined WTI factor model currently produces a "
        "provisional bearish bias over a {horizon_months}-month "
        "horizon. The current demand and financial backdrop is "
        "unfavorable for crude oil."
    ),
    neutral_thesis=(
        "The WTI factor model is currently balanced. Supportive "
        "and restrictive macro forces broadly offset one another, "
        "so MacroLens assigns a neutral bias over a "
        "{horizon_months}-month horizon."
    ),
    limitations=(
        (
            "The model does not directly include OPEC production, "
            "global inventories, spare capacity or geopolitical "
            "supply disruptions."
        ),
        (
            "The model primarily reflects the US macro backdrop and "
            "does not yet include a dedicated global-demand model."
        ),
        (
            "The model does not include futures-curve structure, "
            "positioning or refinery-demand indicators."
        ),
    ),
)


def _get_pillar_state_score(
    result: MacroEnvironmentResult,
    pillar_id: str,
) -> float:
    for pillar in result.pillar_results:
        if pillar.pillar_id == pillar_id:
            return float(pillar.state_score)

    raise ValueError(
        f"Macro environment result does not contain "
        f"pillar '{pillar_id}'."
    )


def build_wti_factors(
    result: MacroEnvironmentResult,
) -> tuple[AssetFactor, ...]:
    policy_score = _get_pillar_state_score(
        result,
        "usa_policy",
    )

    growth_demand = clamp(
        result.activity_score
    )

    inflation_momentum = clamp(
        result.inflation_impulse_score
    )

    liquidity_support = clamp(
        result.financial_impulse_score
    )

    # Negative policy scores represent restrictive policy.
    # The raw score therefore already behaves as a demand-support factor.
    policy_pressure = clamp(
        policy_score
    )

    confidence_component = (
        2.0 * result.confidence_score - 1.0
    )

    conviction_component = (
        2.0 * result.environment_conviction_score - 1.0
    )

    macro_quality = clamp(
        0.60 * confidence_component
        + 0.40 * conviction_component
    )

    return (
        AssetFactor(
            code="wti_growth_demand",
            name="Growth Demand",
            score=growth_demand,
            explanation=(
                "Stronger economic activity generally supports "
                "energy consumption and crude-oil demand."
            ),
        ),
        AssetFactor(
            code="wti_inflation_momentum",
            name="Inflation Momentum",
            score=inflation_momentum,
            explanation=(
                "Stronger inflation momentum can reflect broader "
                "commodity pressure and firmer nominal demand."
            ),
        ),
        AssetFactor(
            code="wti_liquidity_support",
            name="Liquidity Support",
            score=liquidity_support,
            explanation=(
                "Supportive liquidity and financial conditions can "
                "strengthen cyclical demand and commodity prices."
            ),
        ),
        AssetFactor(
            code="wti_policy_pressure",
            name="Policy Support",
            score=policy_pressure,
            explanation=(
                "Restrictive policy can weaken future demand, while "
                "more accommodative policy is generally supportive."
            ),
        ),
        AssetFactor(
            code="wti_macro_quality",
            name="Macro Quality",
            score=macro_quality,
            explanation=(
                "Model confidence and environment conviction are "
                "combined to assess the consistency of the current "
                "macro backdrop."
            ),
        ),
    )


def build_wti_research_idea_from_result(
    *,
    result: MacroEnvironmentResult,
    horizon_months: int = 3,
):
    factors = build_wti_factors(result)

    return build_cross_asset_research_idea(
        result=result,
        factors=factors,
        spec=WTI_MODEL_SPEC,
        horizon_months=horizon_months,
    )


def build_wti_research_idea(
    horizon_months: int = 3,
):
    usa_result = load_cache(
        "usa_environment"
    )

    idea = build_wti_research_idea_from_result(
        result=usa_result,
        horizon_months=horizon_months,
    )

    return add_cross_asset_historical_evidence(
        idea=idea,
        asset_key="wti",
        environment=usa_result.environment_label,
        horizon_months=horizon_months,
        spec=WTI_MODEL_SPEC,
    )