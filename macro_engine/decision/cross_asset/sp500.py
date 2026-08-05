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


SP500_MODEL_SPEC = CrossAssetModelSpec(
    asset_key="sp500",
    display_name="S&P 500",
    factor_weights={
        "sp500_growth_support": 0.30,
        "sp500_liquidity_support": 0.25,
        "sp500_policy_support": 0.20,
        "sp500_inflation_balance": 0.10,
        "sp500_macro_quality": 0.15,
    },
    bullish_thesis=(
        "The combined S&P 500 factor model currently produces a "
        "provisional bullish bias over a {horizon_months}-month "
        "horizon. Growth, liquidity, policy conditions, inflation "
        "and overall macro quality are assessed together."
    ),
    bearish_thesis=(
        "The combined S&P 500 factor model currently produces a "
        "provisional bearish bias over a {horizon_months}-month "
        "horizon. The current balance of growth, liquidity, policy, "
        "inflation and macro quality is unfavorable for US equities."
    ),
    neutral_thesis=(
        "The S&P 500 factor model is currently balanced. Supportive "
        "and restrictive macro forces broadly offset one another, "
        "so MacroLens assigns a neutral bias over a "
        "{horizon_months}-month horizon."
    ),
    limitations=(
        (
            "The model does not yet include equity valuation, "
            "earnings revisions or profit-margin expectations."
        ),
        (
            "The model does not yet include positioning, market "
            "breadth or volatility-market indicators."
        ),
        (
            "The inflation factor is a simplified macro assessment "
            "and does not distinguish all sector-level effects."
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


def build_sp500_factors(
    result: MacroEnvironmentResult,
) -> tuple[AssetFactor, ...]:
    policy_score = _get_pillar_state_score(
        result,
        "usa_policy",
    )

    growth_support = clamp(
        result.activity_score,
    )

    liquidity_support = clamp(
        result.financial_impulse_score,
    )

    # In the MacroLens policy pillar, negative values represent
    # restrictive policy. Therefore, the raw policy score already
    # behaves as an equity-support score.
    policy_support = clamp(
        policy_score,
    )

    # Moderate inflation is usually manageable for equities.
    # Very strong inflation pressure becomes increasingly negative.
    inflation_balance = clamp(
        0.25 - abs(result.inflation_impulse_score),
    )

    confidence_component = (
        2.0 * result.confidence_score - 1.0
    )

    conviction_component = (
        2.0 * result.environment_conviction_score - 1.0
    )

    macro_quality = clamp(
        0.60 * confidence_component
        + 0.40 * conviction_component,
    )

    return (
        AssetFactor(
            code="sp500_growth_support",
            name="Growth Support",
            score=growth_support,
            explanation=(
                "Stronger economic activity generally supports "
                "corporate revenues and earnings expectations."
            ),
        ),
        AssetFactor(
            code="sp500_liquidity_support",
            name="Liquidity Support",
            score=liquidity_support,
            explanation=(
                "Supportive liquidity and financial conditions can "
                "support equity valuations and risk appetite."
            ),
        ),
        AssetFactor(
            code="sp500_policy_support",
            name="Policy Support",
            score=policy_support,
            explanation=(
                "More accommodative policy supports valuations, "
                "while restrictive policy weighs on equities."
            ),
        ),
        AssetFactor(
            code="sp500_inflation_balance",
            name="Inflation Balance",
            score=inflation_balance,
            explanation=(
                "Moderate inflation can coexist with healthy earnings, "
                "while elevated inflation may pressure margins and "
                "increase the risk of tighter policy."
            ),
        ),
        AssetFactor(
            code="sp500_macro_quality",
            name="Macro Quality",
            score=macro_quality,
            explanation=(
                "Model confidence and environment conviction are "
                "combined to assess the quality and consistency of "
                "the current macro backdrop."
            ),
        ),
    )


def build_sp500_research_idea_from_result(
    *,
    result: MacroEnvironmentResult,
    horizon_months: int = 3,
):
    factors = build_sp500_factors(result)

    return build_cross_asset_research_idea(
        result=result,
        factors=factors,
        spec=SP500_MODEL_SPEC,
        horizon_months=horizon_months,
    )


def build_sp500_research_idea(
    horizon_months: int = 3,
):
    usa_result = load_cache(
        "usa_environment"
    )

    idea = build_sp500_research_idea_from_result(
        result=usa_result,
        horizon_months=horizon_months,
    )

    return add_cross_asset_historical_evidence(
        idea=idea,
        asset_key="sp500",
        environment=usa_result.environment_label,
        horizon_months=horizon_months,
        spec=SP500_MODEL_SPEC,
    )