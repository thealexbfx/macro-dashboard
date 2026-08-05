from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from macro_engine.decision.cross_asset.factors import (
    AssetFactor,
)
from macro_engine.decision.cross_asset.historical import (
    load_cross_asset_historical_evidence,
)
from macro_engine.decision.models import (
    DecisionEvidence,
    ResearchIdea,
)
from macro_engine.models.environment import (
    MacroEnvironmentResult,
)


DIRECTION_THRESHOLD = 0.10


@dataclass(frozen=True)
class CrossAssetModelSpec:
    asset_key: str
    display_name: str

    factor_weights: dict[str, float]

    bullish_thesis: str
    bearish_thesis: str
    neutral_thesis: str

    limitations: tuple[str, ...] = ()

    historical_outcome_unit: str = "percent"
    historical_outcome_name: str = "return"

def format_historical_outcome(
    value: float | None,
    unit: str,
) -> str:
    if value is None:
        return "unavailable"

    if unit == "basis_points":
        return f"{value:+.1f} bp"

    return f"{value:+.1%}"

def clamp(
    value: float,
    lower: float = -1.0,
    upper: float = 1.0,
) -> float:
    return max(
        lower,
        min(value, upper),
    )


def direction_from_score(
    score: float,
) -> str:
    if score >= DIRECTION_THRESHOLD:
        return "Bullish"

    if score <= -DIRECTION_THRESHOLD:
        return "Bearish"

    return "Neutral"


def historical_support_label(
    observations: int,
) -> str:
    if observations >= 20:
        return "Direct"

    if observations >= 10:
        return "Partial"

    if observations >= 5:
        return "Limited"

    return "Insufficient"


def validate_factor_weights(
    *,
    factors: tuple[AssetFactor, ...],
    weights: dict[str, float],
) -> None:
    factor_codes = {
        factor.code
        for factor in factors
    }

    weight_codes = set(weights)

    missing_weights = factor_codes.difference(
        weight_codes
    )

    unknown_weights = weight_codes.difference(
        factor_codes
    )

    if missing_weights:
        missing = ", ".join(
            sorted(missing_weights)
        )

        raise ValueError(
            f"Missing factor weights for: {missing}"
        )

    if unknown_weights:
        unknown = ", ".join(
            sorted(unknown_weights)
        )

        raise ValueError(
            f"Unknown factor weights supplied for: {unknown}"
        )

    total_weight = sum(
        weights.values()
    )

    if abs(total_weight - 1.0) > 0.0001:
        raise ValueError(
            "Cross-asset factor weights must sum to 1.0. "
            f"Current total: {total_weight:.4f}"
        )

    if any(
        weight < 0
        for weight in weights.values()
    ):
        raise ValueError(
            "Cross-asset factor weights cannot be negative."
        )


def build_factor_evidence(
    factors: tuple[AssetFactor, ...],
) -> tuple[DecisionEvidence, ...]:
    return tuple(
        DecisionEvidence(
            code=factor.code,
            category=factor.name,
            message=(
                f"{factor.explanation} "
                f"Current factor score: "
                f"{factor.score:+.2f}."
            ),
            direction=factor.direction,
            strength=factor.strength,
            source="Cross-Asset Macro Factor Model",
        )
        for factor in factors
    )


def build_cross_asset_research_idea(
    *,
    result: MacroEnvironmentResult,
    factors: tuple[AssetFactor, ...],
    spec: CrossAssetModelSpec,
    horizon_months: int = 3,
) -> ResearchIdea:
    validate_factor_weights(
        factors=factors,
        weights=spec.factor_weights,
    )

    directional_score = sum(
        factor.score
        * spec.factor_weights[factor.code]
        for factor in factors
    )

    directional_score = clamp(
        directional_score
    )

    model_direction = direction_from_score(
        directional_score
    )

    evidence = build_factor_evidence(
        factors
    )

    bullish_evidence = tuple(
        item
        for item in evidence
        if item.direction == "bullish"
    )

    bearish_evidence = tuple(
        item
        for item in evidence
        if item.direction == "bearish"
    )

    if model_direction == "Bullish":
        thesis = spec.bullish_thesis.format(
            horizon_months=horizon_months
        )

        supporting_evidence = bullish_evidence
        contradicting_evidence = bearish_evidence

    elif model_direction == "Bearish":
        thesis = spec.bearish_thesis.format(
            horizon_months=horizon_months
        )

        supporting_evidence = bearish_evidence
        contradicting_evidence = bullish_evidence

    else:
        thesis = spec.neutral_thesis.format(
            horizon_months=horizon_months
        )

        supporting_evidence = bullish_evidence
        contradicting_evidence = bearish_evidence

    limitations = list(
        spec.limitations
    )

    if result.environment_conviction_score < 0.50:
        limitations.append(
            "The current US environment conviction is below "
            "50%, which limits the strength of the research idea."
        )

    as_of_date = (
        result.as_of_date
        if result.as_of_date is not None
        else date.today()
    )

    return ResearchIdea(
        as_of_date=as_of_date,
        asset=spec.display_name,
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


def add_cross_asset_historical_evidence(
    *,
    idea: ResearchIdea,
    asset_key: str,
    environment: str,
    horizon_months: int,
    spec: CrossAssetModelSpec,
) -> ResearchIdea:
    historical_evidence = (
        load_cross_asset_historical_evidence(
            asset_key=asset_key,
            environment=environment,
            horizon_months=horizon_months,
        )
    )

    supporting_evidence = list(
        idea.supporting_evidence
    )

    contradicting_evidence = list(
        idea.contradicting_evidence
    )

    limitations = list(
        idea.limitations
    )

    if not historical_evidence:
        historical_support = "Insufficient"

        limitations.append(
            "No usable historical observations were found "
            "for the current US macro environment."
        )

    else:
        evidence = historical_evidence[0]

        historical_support = (
            historical_support_label(
                evidence.observations
            )
        )

        if evidence.observations < 5:
            limitations.append(
                "The current US macro environment has fewer "
                "than five usable historical observations."
            )

        elif evidence.average_return is not None:
            historical_direction = (
                "bullish"
                if evidence.average_return > 0
                else "bearish"
                if evidence.average_return < 0
                else "neutral"
            )

            average_text = format_historical_outcome(
                evidence.average_return,
                spec.historical_outcome_unit,
            )

            median_text = format_historical_outcome(
                evidence.median_return,
                spec.historical_outcome_unit,
            )

            positive_rate_text = (
                f"{evidence.up_rate:.0%}"
                if evidence.up_rate is not None
                else "unavailable"
            )

            historical_item = DecisionEvidence(
                code=(
                    f"{asset_key}_us_environment_history"
                ),
                category="Historical evidence",
                message=(
                    f"The current US environment produced an "
                    f"average {horizon_months}-month "
                    f"{idea.asset} {spec.historical_outcome_name} of "
                    f"{average_text} and a median "
                    f"{spec.historical_outcome_name} of {median_text} across "
                    f"{evidence.observations} observations. "
                    f"{idea.asset} rose in "
                    f"{positive_rate_text} of observations."
                ),
                direction=historical_direction,
                strength=clamp(
                    evidence.observations / 20,
                    0.0,
                    1.0,
                ),
                source="Historical Validation Engine",
            )

            if idea.model_direction == "Bullish":
                if historical_direction == "bullish":
                    supporting_evidence.append(
                        historical_item
                    )
                elif historical_direction == "bearish":
                    contradicting_evidence.append(
                        historical_item
                    )

            elif idea.model_direction == "Bearish":
                if historical_direction == "bearish":
                    supporting_evidence.append(
                        historical_item
                    )
                elif historical_direction == "bullish":
                    contradicting_evidence.append(
                        historical_item
                    )

            else:
                if historical_direction == "bullish":
                    supporting_evidence.append(
                        historical_item
                    )
                elif historical_direction == "bearish":
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