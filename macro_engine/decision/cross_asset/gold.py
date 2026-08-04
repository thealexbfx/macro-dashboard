from __future__ import annotations

from datetime import date

from macro_engine.cache.storage import load_cache
from macro_engine.decision.models import (
    DecisionEvidence,
    ResearchIdea,
)
from macro_engine.models.environment import (
    MacroEnvironmentResult,
)

from macro_engine.decision.cross_asset.historical import (
    load_cross_asset_historical_evidence,
)

from macro_engine.decision.cross_asset.factors import (
    AssetFactor,
)

DIRECTION_THRESHOLD = 0.10


def _clamp(
    value: float,
    lower: float,
    upper: float,
) -> float:
    return max(
        lower,
        min(value, upper),
    )


def _direction_from_score(
    score: float,
) -> str:
    if score >= DIRECTION_THRESHOLD:
        return "Bullish"

    if score <= -DIRECTION_THRESHOLD:
        return "Bearish"

    return "Neutral"


def _gold_historical_support_label(
    observations: int,
) -> str:
    if observations >= 20:
        return "Direct"

    if observations >= 10:
        return "Partial"

    if observations >= 5:
        return "Limited"

    return "Insufficient"

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

    inflation_support = _clamp(
        result.inflation_impulse_score,
        -1.0,
        1.0,
    )

    # Positive inflation supports Gold, while restrictive policy
    # is represented by a negative policy score and offsets that support.
    real_rate_support = _clamp(
        result.inflation_impulse_score
        + policy_score,
        -1.0,
        1.0,
    )

    liquidity_support = _clamp(
        result.financial_impulse_score,
        -1.0,
        1.0,
    )

    # Strong activity and restrictive policy can support the dollar.
    # Because restrictive policy is negative in the MacroLens model,
    # subtracting it increases the estimated dollar-strength pressure.
    estimated_dollar_strength = _clamp(
        0.60 * result.activity_score
        - 0.40 * policy_score,
        -1.0,
        1.0,
    )

    dollar_pressure = -estimated_dollar_strength

    defensive_demand = _clamp(
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
) -> ResearchIdea:
    """
    Build a provisional Gold research view from five macro factors:

    - Inflation support
    - Real-rate pressure
    - Liquidity support
    - Dollar pressure
    - Defensive demand

    Positive factor scores support Gold.
    Negative factor scores weigh on Gold.
    """
    factors = build_gold_factors(result)

    factor_weights = {
        "gold_inflation_support": 0.20,
        "gold_real_rate_support": 0.30,
        "gold_liquidity_support": 0.20,
        "gold_dollar_pressure": 0.20,
        "gold_defensive_demand": 0.10,
    }

    directional_score = sum(
        factor.score * factor_weights[factor.code]
        for factor in factors
    )

    directional_score = _clamp(
        directional_score,
        -1.0,
        1.0,
    )

    model_direction = _direction_from_score(
        directional_score
    )

    evidence = tuple(
        DecisionEvidence(
            code=factor.code,
            category=factor.name,
            message=(
                f"{factor.explanation} "
                f"Current factor score: {factor.score:+.2f}."
            ),
            direction=factor.direction,
            strength=factor.strength,
            source="Gold Macro Factor Model",
        )
        for factor in factors
    )

    if model_direction == "Bullish":
        supporting_evidence = tuple(
            item
            for item in evidence
            if item.direction == "bullish"
        )

        contradicting_evidence = tuple(
            item
            for item in evidence
            if item.direction == "bearish"
        )

        thesis = (
            "The combined Gold factor model currently produces a "
            f"provisional bullish bias over a {horizon_months}-month "
            "horizon. Real-rate conditions, inflation, liquidity, "
            "dollar pressure and defensive demand are assessed "
            "together rather than relying on a single macro variable."
        )

    elif model_direction == "Bearish":
        supporting_evidence = tuple(
            item
            for item in evidence
            if item.direction == "bearish"
        )

        contradicting_evidence = tuple(
            item
            for item in evidence
            if item.direction == "bullish"
        )

        thesis = (
            "The combined Gold factor model currently produces a "
            f"provisional bearish bias over a {horizon_months}-month "
            "horizon. The current balance of real-rate conditions, "
            "inflation, liquidity, dollar pressure and defensive "
            "demand is unfavorable for Gold."
        )

    else:
        supporting_evidence = tuple(
            item
            for item in evidence
            if item.direction == "bullish"
        )

        contradicting_evidence = tuple(
            item
            for item in evidence
            if item.direction == "bearish"
        )

        thesis = (
            "The Gold factor model is currently balanced. Inflation "
            "and liquidity provide support, while real-rate conditions, "
            "dollar pressure and the current activity backdrop offset "
            "that support. MacroLens therefore assigns a neutral bias "
            f"over a {horizon_months}-month horizon."
        )

    limitations = [
        (
            "Real-rate pressure is currently estimated using the "
            "relationship between the inflation and policy impulses "
            "rather than a direct market-based real-yield series."
        ),
        (
            "Dollar pressure is currently estimated from the US "
            "activity and policy backdrop rather than a dedicated "
            "broad-dollar model."
        ),
        (
            "The model does not yet include futures positioning, "
            "central-bank purchases or physical-demand data."
        ),
    ]

    if result.environment_conviction_score < 0.50:
        limitations.append(
            "The current US environment conviction is below 50%, "
            "which limits the strength of the Gold research idea."
        )

    as_of_date = (
        result.as_of_date
        if result.as_of_date is not None
        else date.today()
    )

    return ResearchIdea(
        as_of_date=as_of_date,
        asset="Gold",
        model_direction=model_direction,
        horizon_months=horizon_months,
        directional_score=directional_score,
        model_confidence=result.confidence_score,
        model_conviction=(
            result.environment_conviction_score
        ),
        historical_support="Pending",
        thesis=thesis,
        supporting_evidence=supporting_evidence,
        contradicting_evidence=contradicting_evidence,
        limitations=tuple(limitations),
    )


def build_gold_research_idea(
    horizon_months: int = 3,
) -> ResearchIdea:
    usa_result = load_cache(
        "usa_environment"
    )

    idea = build_gold_research_idea_from_result(
        result=usa_result,
        horizon_months=horizon_months,
    )

    historical_evidence = (
        load_cross_asset_historical_evidence(
            asset_key="gold",
            environment=usa_result.environment_label,
            horizon_months=horizon_months,
        )
    )

    if historical_evidence:
        evidence = historical_evidence[0]
        historical_support = (
            _gold_historical_support_label(
                evidence.observations
            )
        )
    else:
        evidence = None
        historical_support = "Insufficient"

    supporting_evidence = list(
        idea.supporting_evidence
    )

    contradicting_evidence = list(
        idea.contradicting_evidence
    )

    limitations = list(
        idea.limitations
    )

    if evidence is None:
        limitations.append(
            "No usable historical observations were found "
            "for the current US macro environment."
        )

    elif evidence.observations < 5:
        limitations.append(
            "The current US macro environment has fewer than "
            "five usable historical Gold observations."
        )

    elif evidence.average_return is not None:
        historical_direction = (
            "bullish"
            if evidence.average_return > 0
            else "bearish"
            if evidence.average_return < 0
            else "neutral"
        )

        historical_item = DecisionEvidence(
            code="gold_us_environment_history",
            category="Historical evidence",
            message=(
                f"The current US environment produced an average "
                f"{horizon_months}-month Gold return of "
                f"{evidence.average_return:+.1%} and a median "
                f"return of {evidence.median_return:+.1%} across "
                f"{evidence.observations} observations. Gold rose "
                f"in {evidence.up_rate:.0%} of observations."
            ),
            direction=historical_direction,
            strength=_clamp(
                evidence.observations / 20,
                0.0,
                1.0,
            ),
            source="Historical Validation Engine",
        )

        if (
            idea.model_direction == "Bullish"
            and historical_direction == "bullish"
        ) or (
            idea.model_direction == "Bearish"
            and historical_direction == "bearish"
        ):
            supporting_evidence.append(
                historical_item
            )

        elif historical_direction != "neutral":
            contradicting_evidence.append(
                historical_item
            )

    return ResearchIdea(
        as_of_date=idea.as_of_date,
        asset=idea.asset,
        model_direction=idea.model_direction,
        horizon_months=idea.horizon_months,
        directional_score=idea.directional_score,
        model_confidence=idea.model_confidence,
        model_conviction=idea.model_conviction,
        historical_support=historical_support,
        thesis=idea.thesis,
        supporting_evidence=tuple(
            supporting_evidence
        ),
        contradicting_evidence=tuple(
            contradicting_evidence
        ),
        limitations=tuple(
            limitations
        ),
    )