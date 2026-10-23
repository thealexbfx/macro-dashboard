from __future__ import annotations

from datetime import date
from macro_engine.decision.historical_models import HistoricalEvidence
from macro_engine.decision.fx_config import get_fx_config
from macro_engine.decision.models import DecisionEvidence, ResearchIdea
from macro_engine.models.environment import MacroEnvironmentResult
from macro_engine.cache.storage import load_cache

from macro_engine.decision.historical_engine import (
    load_historical_evidence,
)

DIRECTION_THRESHOLD = 0.10


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def _direction_from_score(score: float) -> str:
    if score >= DIRECTION_THRESHOLD:
        return "Bullish"

    if score <= -DIRECTION_THRESHOLD:
        return "Bearish"

    return "Neutral"


def _build_difference_evidence(
    *,
    code: str,
    category: str,
    difference: float,
    base_name: str,
    quote_name: str,
    base_value: float,
    quote_value: float,
) -> DecisionEvidence:
    if difference > 0:
        direction = "bullish"
        stronger_economy = base_name
    elif difference < 0:
        direction = "bearish"
        stronger_economy = quote_name
    else:
        direction = "neutral"
        stronger_economy = "Neither economy"

    return DecisionEvidence(
        code=code,
        category=category,
        message=(
            f"{stronger_economy} has the stronger {category.lower()} "
            f"backdrop. {base_name}: {base_value:+.2f}; "
            f"{quote_name}: {quote_value:+.2f}."
        ),
        direction=direction,
        strength=_clamp(abs(difference), 0.0, 1.0),
        source="Macro Environment Engine",
    )


def build_fx_research_idea_from_results(
    *,
    asset: str,
    base_name: str,
    quote_name: str,
    base_result: MacroEnvironmentResult,
    quote_result: MacroEnvironmentResult,
    horizon_months: int = 3,
) -> ResearchIdea:
    """
    Build a provisional FX research idea from two macro environments.

    A positive score favours the base currency.
    A negative score favours the quote currency.
    """
    activity_difference = (
        base_result.activity_score
        - quote_result.activity_score
    )

    inflation_difference = (
        base_result.inflation_impulse_score
        - quote_result.inflation_impulse_score
    )

    financial_difference = (
        base_result.financial_impulse_score
        - quote_result.financial_impulse_score
    )

    directional_score = (
        0.40 * activity_difference
        + 0.30 * inflation_difference
        + 0.30 * financial_difference
    )

    directional_score = _clamp(
        directional_score,
        -1.0,
        1.0,
    )

    model_direction = _direction_from_score(
        directional_score
    )

    model_confidence = (
        base_result.confidence_score
        + quote_result.confidence_score
    ) / 2

    model_conviction = (
        base_result.environment_conviction_score
        + quote_result.environment_conviction_score
    ) / 2

    evidence = (
        _build_difference_evidence(
            code="fx_activity_difference",
            category="Activity",
            difference=activity_difference,
            base_name=base_name,
            quote_name=quote_name,
            base_value=base_result.activity_score,
            quote_value=quote_result.activity_score,
        ),
        _build_difference_evidence(
            code="fx_inflation_difference",
            category="Inflation impulse",
            difference=inflation_difference,
            base_name=base_name,
            quote_name=quote_name,
            base_value=base_result.inflation_impulse_score,
            quote_value=quote_result.inflation_impulse_score,
        ),
        _build_difference_evidence(
            code="fx_financial_difference",
            category="Financial conditions",
            difference=financial_difference,
            base_name=base_name,
            quote_name=quote_name,
            base_value=base_result.financial_impulse_score,
            quote_value=quote_result.financial_impulse_score,
        ),
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
            f"The current relative macro backdrop favours "
            f"{base_name} over {quote_name}. This produces a "
            f"provisional bullish bias for {asset} over a "
            f"{horizon_months}-month horizon."
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
            f"The current relative macro backdrop favours "
            f"{quote_name} over {base_name}. This produces a "
            f"provisional bearish bias for {asset} over a "
            f"{horizon_months}-month horizon."
        )

    else:
        supporting_evidence = tuple(
            item
            for item in evidence
            if item.direction != "neutral"
        )
        contradicting_evidence = ()
        thesis = (
            f"The relative macro evidence between {base_name} "
            f"and {quote_name} is currently balanced. MacroLens "
            f"therefore assigns a neutral bias to {asset}."
        )

    limitations = [
        "The current version does not yet include valuation or positioning."
    ]

    if model_conviction < 0.50:
        limitations.append(
            "Average environment conviction is below 50%, "
            "which limits the strength of the research idea."
        )

    as_of_dates = [
        result.as_of_date
        for result in (base_result, quote_result)
        if result.as_of_date is not None
    ]

    as_of_date = (
        min(as_of_dates)
        if as_of_dates
        else date.today()
    )

    return ResearchIdea(
        as_of_date=as_of_date,
        asset=asset,
        model_direction=model_direction,
        horizon_months=horizon_months,
        directional_score=directional_score,
        model_confidence=model_confidence,
        model_conviction=model_conviction,
        historical_support="Pending",
        thesis=thesis,
        supporting_evidence=supporting_evidence,
        contradicting_evidence=contradicting_evidence,
        limitations=tuple(limitations),
    )

def _historical_support_label(
    evidence: tuple[HistoricalEvidence, ...],
) -> str:
    exact_pair = next(
        (
            item
            for item in evidence
            if item.source == "Exact environment pair history"
        ),
        None,
    )

    if exact_pair is not None:
        if exact_pair.observations >= 10:
            return "Direct"
        if exact_pair.observations >= 5:
            return "Partial"
        return "Limited"

    usable_individual_rows = [
        item
        for item in evidence
        if item.observations >= 5
    ]

    if len(usable_individual_rows) >= 2:
        return "Partial"

    if usable_individual_rows:
        return "Limited"

    return "Insufficient"


def _format_return(value: float | None) -> str:
    if value is None:
        return "unavailable"

    return f"{value:+.1%}"


def _build_historical_decision_evidence(
    *,
    asset: str,
    primary_name: str,
    secondary_name: str,
    evidence: tuple[HistoricalEvidence, ...],
    model_direction: str,
    horizon_months: int,
) -> tuple[
    tuple[DecisionEvidence, ...],
    tuple[DecisionEvidence, ...],
    tuple[str, ...],
]:
    supporting: list[DecisionEvidence] = []
    contradicting: list[DecisionEvidence] = []
    limitations: list[str] = []

    expected_sign = -1 if model_direction == "Bearish" else 1

    exact_pair_found = False

    for item in evidence:
        if item.source == "Exact environment pair history":
            exact_pair_found = True

        if item.observations < 5:
            limitations.append(
                f"{item.source} for {item.label} has only "
                f"{item.observations} usable "
                f"{horizon_months}-month observation(s)."
            )
            continue

        average_return = item.average_return

        if average_return is None:
            continue

        direction = (
            "bullish"
            if average_return > 0
            else "bearish"
            if average_return < 0
            else "neutral"
        )

        historical_item = DecisionEvidence(
            code=(
                "historical_"
                + item.source.lower().replace(" ", "_")
            ),
            category="Historical evidence",
            message=(
                f"{item.source} for {item.label} produced an "
                f"average {horizon_months}-month {asset} return "
                f"of {_format_return(item.average_return)} and a "
                f"median return of {_format_return(item.median_return)} "
                f"across {item.observations} observations. {asset} "
                f"rose in {item.up_rate:.0%} of observations and fell "
                f"in {item.down_rate:.0%}."
            ),
            direction=direction,
            strength=_clamp(
                item.observations / 20,
                0.0,
                1.0,
            ),
            source="Historical Validation Engine",
        )

        historical_sign = (
            1
            if average_return > 0
            else -1
            if average_return < 0
            else 0
        )

        if historical_sign == expected_sign:
            supporting.append(historical_item)
        elif historical_sign == -expected_sign:
            contradicting.append(historical_item)

    if not exact_pair_found:
        limitations.append(
            f"No exact historical match was found for the current "
            f"{primary_name} and {secondary_name} environment combination."
        )

    return (
        tuple(supporting),
        tuple(contradicting),
        tuple(limitations),
    )

def build_fx_research_idea(
    asset_key: str,
    horizon_months: int = 3,
) -> ResearchIdea:
    config = get_fx_config(asset_key)

    base_result = load_cache(
        config.base_environment_cache
    )

    quote_result = load_cache(
        config.quote_environment_cache
    )

    idea = build_fx_research_idea_from_results(
        asset=config.display_name,
        base_name=config.base_name,
        quote_name=config.quote_name,
        base_result=base_result,
        quote_result=quote_result,
        horizon_months=horizon_months,
    )

    historical_evidence = load_historical_evidence(
        asset_key=config.key,
        primary_environment=(
            quote_result.environment_label
            if config.quote_environment_cache == "usa_environment"
            else base_result.environment_label
        ),
        secondary_environment=(
            base_result.environment_label
            if config.quote_environment_cache == "usa_environment"
            else quote_result.environment_label
        ),
        horizon_months=horizon_months,
    )

    (
        historical_supporting,
        historical_contradicting,
        historical_limitations,
    ) = _build_historical_decision_evidence(
        asset=config.display_name,
        primary_name=config.historical_primary_name,
        secondary_name=config.historical_secondary_name,
        evidence=historical_evidence,
        model_direction=idea.model_direction,
        horizon_months=horizon_months,
    )

    return ResearchIdea(
        as_of_date=idea.as_of_date,
        asset=idea.asset,
        model_direction=idea.model_direction,
        horizon_months=idea.horizon_months,
        directional_score=idea.directional_score,
        model_confidence=idea.model_confidence,
        model_conviction=idea.model_conviction,
        historical_support=_historical_support_label(
            historical_evidence
        ),
        thesis=idea.thesis,
        supporting_evidence=(
            idea.supporting_evidence
            + historical_supporting
        ),
        contradicting_evidence=(
            idea.contradicting_evidence
            + historical_contradicting
        ),
        limitations=(
            idea.limitations
            + historical_limitations
        ),
    )

def build_gbpusd_research_idea(
    horizon_months: int = 3,
) -> ResearchIdea:
    return build_fx_research_idea(
        asset_key="gbpusd",
        horizon_months=horizon_months,
    )


def build_eurusd_research_idea(
    horizon_months: int = 3,
) -> ResearchIdea:
    return build_fx_research_idea(
        asset_key="eurusd",
        horizon_months=horizon_months,
    )