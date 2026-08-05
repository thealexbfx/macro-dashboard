from __future__ import annotations



from macro_engine.cache.storage import load_cache

from macro_engine.models.environment import (
    MacroEnvironmentResult,
)

from macro_engine.decision.cross_asset.factors import (
    AssetFactor,
)

from macro_engine.decision.cross_asset.base import (
    CrossAssetModelSpec,
    add_cross_asset_historical_evidence,
    build_cross_asset_research_idea,
    clamp,
)

GOLD_MODEL_SPEC = CrossAssetModelSpec(
    asset_key="gold",
    display_name="Gold",
    factor_weights={
        "gold_inflation_support": 0.20,
        "gold_real_rate_support": 0.30,
        "gold_liquidity_support": 0.20,
        "gold_dollar_pressure": 0.20,
        "gold_defensive_demand": 0.10,
    },
    bullish_thesis=(
        "The combined Gold factor model currently produces a "
        "provisional bullish bias over a {horizon_months}-month "
        "horizon. Real-rate conditions, inflation, liquidity, "
        "dollar pressure and defensive demand are assessed together "
        "rather than relying on a single macro variable."
    ),
    bearish_thesis=(
        "The combined Gold factor model currently produces a "
        "provisional bearish bias over a {horizon_months}-month "
        "horizon. The current balance of real-rate conditions, "
        "inflation, liquidity, dollar pressure and defensive demand "
        "is unfavorable for Gold."
    ),
    neutral_thesis=(
        "The Gold factor model is currently balanced. Inflation and "
        "liquidity provide support, while real-rate conditions, "
        "dollar pressure and the current activity backdrop offset "
        "that support. MacroLens therefore assigns a neutral bias "
        "over a {horizon_months}-month horizon."
    ),
    limitations=(
        (
            "Real-rate conditions are currently estimated from the "
            "inflation and policy pillars rather than a direct "
            "market-based real-yield series."
        ),
        (
            "Dollar pressure is estimated from the US activity and "
            "policy backdrop rather than a dedicated broad-dollar model."
        ),
        (
            "The model does not yet include futures positioning, "
            "central-bank purchases or physical-demand data."
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
        f"Macro environment result does not contain pillar "
        f"'{pillar_id}'."
    )

def build_gold_factors(
    result: MacroEnvironmentResult,
) -> tuple[AssetFactor, ...]:
    policy_score = _get_pillar_state_score(
        result,
        "usa_policy",
    )

    inflation_support = clamp(
        result.inflation_impulse_score,
        -1.0,
        1.0,
    )

    # Positive inflation supports Gold, while restrictive policy
    # is represented by a negative policy score and offsets that support.
    real_rate_support = clamp(
        result.inflation_impulse_score
        + policy_score,
        -1.0,
        1.0,
    )

    liquidity_support = clamp(
        result.financial_impulse_score,
        -1.0,
        1.0,
    )

    # Strong activity and restrictive policy can support the dollar.
    # Because restrictive policy is negative in the MacroLens model,
    # subtracting it increases the estimated dollar-strength pressure.
    estimated_dollar_strength = clamp(
        0.60 * result.activity_score
        - 0.40 * policy_score,
        -1.0,
        1.0,
    )

    dollar_pressure = -estimated_dollar_strength

    defensive_demand = clamp(
        -result.activity_score,
        -1.0,
        1.0,
    )

    return (
        AssetFactor(
            code="gold_inflation_support",
            name="Inflation Support",
            score=inflation_support,
            explanation=(
                "Stronger inflation pressure can support Gold as "
                "a store of value."
            ),
        ),
        AssetFactor(
            code="gold_real_rate_support",
            name="Real-Rate Support",
            score=real_rate_support,
            explanation=(
                "Inflation and the policy stance are combined as "
                "a proxy for real-rate conditions. Restrictive "
                "policy offsets the support from inflation."
            ),
        ),
        AssetFactor(
            code="gold_liquidity_support",
            name="Liquidity Support",
            score=liquidity_support,
            explanation=(
                "More supportive liquidity and financial conditions "
                "are generally positive for Gold."
            ),
        ),
        AssetFactor(
            code="gold_dollar_pressure",
            name="Dollar Pressure",
            score=dollar_pressure,
            explanation=(
                "Strong US activity and restrictive policy can "
                "support the dollar and weigh on Gold."
            ),
        ),
        AssetFactor(
            code="gold_defensive_demand",
            name="Defensive Demand",
            score=defensive_demand,
            explanation=(
                "Weaker economic activity can increase demand for "
                "defensive and safe-haven assets."
            ),
        ),
    )
def build_gold_research_idea_from_result(
    *,
    result: MacroEnvironmentResult,
    horizon_months: int = 3,
):
    factors = build_gold_factors(result)

    return build_cross_asset_research_idea(
        result=result,
        factors=factors,
        spec=GOLD_MODEL_SPEC,
        horizon_months=horizon_months,
    )


def build_gold_research_idea(
    horizon_months: int = 3,
):
    usa_result = load_cache(
        "usa_environment"
    )

    idea = build_gold_research_idea_from_result(
        result=usa_result,
        horizon_months=horizon_months,
    )

    return add_cross_asset_historical_evidence(
        idea=idea,
        asset_key="gold",
        environment=usa_result.environment_label,
        horizon_months=horizon_months,
        spec=GOLD_MODEL_SPEC,
    )