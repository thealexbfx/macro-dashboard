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


US10Y_MODEL_SPEC = CrossAssetModelSpec(
    asset_key="us10y",
    display_name="US 10Y",
    factor_weights={
        "us10y_inflation_pressure": 0.30,
        "us10y_policy_pressure": 0.25,
        "us10y_growth_pressure": 0.20,
        "us10y_liquidity_pressure": 0.15,
        "us10y_macro_quality": 0.10,
    },
    bullish_thesis=(
        "The combined US 10Y factor model currently produces a "
        "provisional bullish yield bias over a "
        "{horizon_months}-month horizon. Inflation, policy, growth, "
        "liquidity and macro quality are assessed together."
    ),
    bearish_thesis=(
        "The combined US 10Y factor model currently produces a "
        "provisional bearish yield bias over a "
        "{horizon_months}-month horizon. The current macro backdrop "
        "is more consistent with lower Treasury yields."
    ),
    neutral_thesis=(
        "The US 10Y factor model is currently balanced. Upward and "
        "downward yield pressures broadly offset one another, so "
        "MacroLens assigns a neutral yield bias over a "
        "{horizon_months}-month horizon."
    ),
    limitations=(
        (
            "The model does not yet include Treasury term premium, "
            "auction dynamics or foreign demand directly."
        ),
        (
            "The model does not yet include market-implied inflation "
            "expectations or a direct decomposition of real yields."
        ),
        (
            "The current price context uses the Yahoo Finance US 10Y "
            "yield series rather than a bond total-return index."
        ),
    ),
    historical_outcome_unit="basis_points",
    historical_outcome_name="yield change",
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


def build_us10y_factors(
    result: MacroEnvironmentResult,
) -> tuple[AssetFactor, ...]:
    policy_score = _get_pillar_state_score(
        result,
        "usa_policy",
    )

    inflation_pressure = clamp(
        result.inflation_impulse_score
    )

    # Restrictive policy is negative in MacroLens.
    # Invert it so restrictive policy becomes upward yield pressure.
    policy_pressure = clamp(
        -policy_score
    )

    growth_pressure = clamp(
        result.activity_score
    )

    # Easier liquidity can reduce upward yield pressure,
    # so the financial impulse is inverted.
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
            code="us10y_inflation_pressure",
            name="Inflation Pressure",
            score=inflation_pressure,
            explanation=(
                "Stronger inflation pressure tends to push nominal "
                "Treasury yields higher."
            ),
        ),
        AssetFactor(
            code="us10y_policy_pressure",
            name="Policy Pressure",
            score=policy_pressure,
            explanation=(
                "More restrictive policy generally creates upward "
                "pressure on Treasury yields."
            ),
        ),
        AssetFactor(
            code="us10y_growth_pressure",
            name="Growth Pressure",
            score=growth_pressure,
            explanation=(
                "Stronger activity can increase expected policy rates "
                "and term yields."
            ),
        ),
        AssetFactor(
            code="us10y_liquidity_pressure",
            name="Liquidity Pressure",
            score=liquidity_pressure,
            explanation=(
                "More supportive liquidity can reduce upward yield "
                "pressure, while tighter financial conditions can "
                "push yields higher."
            ),
        ),
        AssetFactor(
            code="us10y_macro_quality",
            name="Macro Quality",
            score=macro_quality,
            explanation=(
                "Model confidence and conviction are combined to "
                "assess how reliable the current macro classification is."
            ),
        ),
    )


def build_us10y_research_idea_from_result(
    *,
    result: MacroEnvironmentResult,
    horizon_months: int = 3,
):
    factors = build_us10y_factors(result)

    return build_cross_asset_research_idea(
        result=result,
        factors=factors,
        spec=US10Y_MODEL_SPEC,
        horizon_months=horizon_months,
    )


def build_us10y_research_idea(
    horizon_months: int = 3,
):
    usa_result = load_cache(
        "usa_environment"
    )

    idea = build_us10y_research_idea_from_result(
        result=usa_result,
        horizon_months=horizon_months,
    )

    return add_cross_asset_historical_evidence(
        idea=idea,
        asset_key="us10y",
        environment=usa_result.environment_label,
        horizon_months=horizon_months,
        spec=US10Y_MODEL_SPEC,
    )