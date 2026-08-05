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


DXY_MODEL_SPEC = CrossAssetModelSpec(
    asset_key="dxy",
    display_name="DXY",
    factor_weights={
        "dxy_growth_support": 0.25,
        "dxy_policy_support": 0.30,
        "dxy_inflation_support": 0.15,
        "dxy_liquidity_pressure": 0.20,
        "dxy_macro_quality": 0.10,
    },
    bullish_thesis=(
        "The combined DXY factor model currently produces a "
        "provisional bullish dollar bias over a "
        "{horizon_months}-month horizon. US growth, policy, "
        "inflation, liquidity and macro quality are assessed together."
    ),
    bearish_thesis=(
        "The combined DXY factor model currently produces a "
        "provisional bearish dollar bias over a "
        "{horizon_months}-month horizon. The current US macro "
        "backdrop is unfavorable for broad dollar strength."
    ),
    neutral_thesis=(
        "The DXY factor model is currently balanced. Supportive and "
        "restrictive dollar drivers broadly offset one another, so "
        "MacroLens assigns a neutral bias over a "
        "{horizon_months}-month horizon."
    ),
    limitations=(
        (
            "The current model is US-centered and does not yet "
            "explicitly compare the United States with the Euro Area, "
            "United Kingdom and Japan."
        ),
        (
            "The model does not directly include interest-rate "
            "differentials, positioning or global risk-aversion flows."
        ),
        (
            "The model does not account for the fixed currency "
            "weights used in the DXY index."
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


def build_dxy_factors(
    result: MacroEnvironmentResult,
) -> tuple[AssetFactor, ...]:
    policy_score = _get_pillar_state_score(
        result,
        "usa_policy",
    )

    growth_support = clamp(
        result.activity_score
    )

    # Negative policy scores represent restrictive policy.
    # Invert the score so restrictive policy becomes dollar support.
    policy_support = clamp(
        -policy_score
    )

    inflation_support = clamp(
        result.inflation_impulse_score
    )

    # Easier financial conditions can reduce dollar support,
    # so invert the financial impulse.
    liquidity_pressure = clamp(
        -result.financial_impulse_score
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
            code="dxy_growth_support",
            name="Growth Support",
            score=growth_support,
            explanation=(
                "Stronger US activity can attract capital and support "
                "the dollar relative to other major currencies."
            ),
        ),
        AssetFactor(
            code="dxy_policy_support",
            name="Policy Support",
            score=policy_support,
            explanation=(
                "More restrictive US policy can support the dollar "
                "through higher relative rates."
            ),
        ),
        AssetFactor(
            code="dxy_inflation_support",
            name="Inflation Support",
            score=inflation_support,
            explanation=(
                "Stronger inflation pressure can support expectations "
                "for tighter policy and higher US yields."
            ),
        ),
        AssetFactor(
            code="dxy_liquidity_pressure",
            name="Liquidity Pressure",
            score=liquidity_pressure,
            explanation=(
                "More supportive liquidity can reduce demand for the "
                "dollar, while tighter financial conditions can support it."
            ),
        ),
        AssetFactor(
            code="dxy_macro_quality",
            name="Macro Quality",
            score=macro_quality,
            explanation=(
                "Model confidence and environment conviction are "
                "combined to assess the reliability of the current "
                "US macro backdrop."
            ),
        ),
    )


def build_dxy_research_idea_from_result(
    *,
    result: MacroEnvironmentResult,
    horizon_months: int = 3,
):
    factors = build_dxy_factors(result)

    return build_cross_asset_research_idea(
        result=result,
        factors=factors,
        spec=DXY_MODEL_SPEC,
        horizon_months=horizon_months,
    )


def build_dxy_research_idea(
    horizon_months: int = 3,
):
    usa_result = load_cache(
        "usa_environment"
    )

    idea = build_dxy_research_idea_from_result(
        result=usa_result,
        horizon_months=horizon_months,
    )

    return add_cross_asset_historical_evidence(
        idea=idea,
        asset_key="dxy",
        environment=usa_result.environment_label,
        horizon_months=horizon_months,
        spec=DXY_MODEL_SPEC,
    )