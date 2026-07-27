from __future__ import annotations

from datetime import date
from statistics import fmean
from typing import Iterable

from macro_engine.models.environment import (
    EnvironmentSignal,
    MacroEnvironmentConfig,
    MacroEnvironmentHistory,
    MacroEnvironmentResult,
    MacroEnvironmentSnapshot,
    MacroRegimePeriod,
)

from macro_engine.models.pillar import PillarResult

def create_environment_snapshot(
    result: MacroEnvironmentResult,
) -> MacroEnvironmentSnapshot:
    if result.as_of_date is None:
        raise ValueError(
            "environment result must have an as_of_date "
            "before a snapshot can be created"
        )

    return MacroEnvironmentSnapshot(
        economy=result.economy,
        as_of_date=result.as_of_date,
        activity_score=result.activity_score,
        activity_label=result.activity_label,
        inflation_impulse_score=(
            result.inflation_impulse_score
        ),
        inflation_impulse_label=(
            result.inflation_impulse_label
        ),
        financial_impulse_score=(
            result.financial_impulse_score
        ),
        financial_impulse_label=(
            result.financial_impulse_label
        ),
        environment_label=result.environment_label,
        confidence_score=result.confidence_score,
        environment_conviction_score=(
            result.environment_conviction_score
        ),
        environment_conviction_label=(
            result.environment_conviction_label
        ),
        flags=result.flags,
    )

def build_regime_periods(
    history: MacroEnvironmentHistory,
) -> tuple[MacroRegimePeriod, ...]:
    """
    Convert ordered environment snapshots into consecutive regime periods.

    A new period begins whenever the environment label changes.
    The final period is marked as current.
    """

    snapshots = history.snapshots

    periods: list[MacroRegimePeriod] = []
    current_group: list[MacroEnvironmentSnapshot] = [
        snapshots[0]
    ]

    for snapshot in snapshots[1:]:
        previous_snapshot = current_group[-1]

        if (
            snapshot.environment_label
            == previous_snapshot.environment_label
        ):
            current_group.append(snapshot)
            continue

        periods.append(
            _build_regime_period(
                economy=history.economy,
                snapshots=tuple(current_group),
                is_current=False,
            )
        )

        current_group = [snapshot]

    periods.append(
        _build_regime_period(
            economy=history.economy,
            snapshots=tuple(current_group),
            is_current=True,
        )
    )

    return tuple(periods)


def _build_regime_period(
    economy: str,
    snapshots: tuple[MacroEnvironmentSnapshot, ...],
    is_current: bool,
) -> MacroRegimePeriod:
    if not snapshots:
        raise ValueError(
            "at least one snapshot is required "
            "to build a regime period"
        )

    environment_labels = {
        snapshot.environment_label
        for snapshot in snapshots
    }

    if len(environment_labels) != 1:
        raise ValueError(
            "all snapshots in a regime period "
            "must share the same environment label"
        )

    starting_snapshot = snapshots[0]
    ending_snapshot = snapshots[-1]

    return MacroRegimePeriod(
        economy=economy,
        environment_label=(
            starting_snapshot.environment_label
        ),
        start_date=starting_snapshot.as_of_date,
        end_date=ending_snapshot.as_of_date,
        observation_count=len(snapshots),
        average_confidence_score=round(
            fmean(
                snapshot.confidence_score
                for snapshot in snapshots
            ),
            4,
        ),
        average_conviction_score=round(
            fmean(
                snapshot.environment_conviction_score
                for snapshot in snapshots
            ),
            4,
        ),
        starting_snapshot=starting_snapshot,
        ending_snapshot=ending_snapshot,
        is_current=is_current,
    )


def _normalise_name(value: str) -> str:
    return value.strip().lower().replace(" ", "_")

def _canonical_pillar_name(
    result: PillarResult,
    economy: str | None = None,
) -> str:
    """
    Convert a pillar result into its canonical environment key.

    Examples:
        "usa_growth" -> "growth"
        "euro_inflation" -> "inflation"
        "uk_labor" -> "labor"
        "japan_policy" -> "policy"
    """

    pillar_id = _normalise_name(result.pillar_id)

    canonical_names = (
        "growth",
        "inflation",
        "labor",
        "liquidity",
        "policy",
    )

    for canonical_name in canonical_names:
        if (
            pillar_id == canonical_name
            or pillar_id.endswith(f"_{canonical_name}")
        ):
            return canonical_name

    return _normalise_name(result.name)

def validate_environment_inputs(
    config: MacroEnvironmentConfig,
    pillar_results: Iterable[PillarResult],
) -> tuple[PillarResult, ...]:
    """Validate and normalize pillar inputs for the environment engine."""

    results = tuple(pillar_results)

    if len(results) < config.minimum_pillars:
        raise ValueError(
            f"at least {config.minimum_pillars} pillar results are required"
        )

    pillar_names = [_normalise_name(result.name) for result in results]

    if len(set(pillar_names)) != len(pillar_names):
        raise ValueError("pillar results must contain unique pillar names")

    mismatched_economies = [
        result.name
        for result in results
        if result.economy.strip().upper() != config.economy.strip().upper()
    ]

    if mismatched_economies:
        raise ValueError(
            "all pillar results must match the configured economy"
        )

    return results


def calculate_environment_confidence(
    pillar_results: tuple[PillarResult, ...],
) -> float:
    """
    Calculate environment confidence.

    Confidence is the mean pillar confidence, reduced when pillar confidence
    is uneven across the environment.
    """

    confidence_values = [
        max(0.0, min(1.0, result.confidence_score))
        for result in pillar_results
    ]

    mean_confidence = fmean(confidence_values)
    confidence_range = max(confidence_values) - min(confidence_values)

    consistency_penalty = confidence_range * 0.15

    return round(
        max(0.0, min(1.0, mean_confidence - consistency_penalty)),
        4,
    )


def classify_environment_confidence(score: float) -> str:
    if score >= 0.80:
        return "High"

    if score >= 0.60:
        return "Moderate"

    if score >= 0.40:
        return "Low"

    return "Very Low"


def calculate_overall_direction(
    pillar_results: tuple[PillarResult, ...],
) -> str:
    """
    Classify the broad direction of the environment.

    Pillar trend scores are weighted by their individual confidence.
    """

    total_weight = sum(result.confidence_score for result in pillar_results)

    if total_weight <= 0.0:
        return "Unclear"

    weighted_trend = sum(
        result.trend_score * result.confidence_score
        for result in pillar_results
    ) / total_weight

    positive_count = sum(
        result.trend_score >= 0.20 for result in pillar_results
    )
    negative_count = sum(
        result.trend_score <= -0.20 for result in pillar_results
    )

    if positive_count >= 2 and negative_count >= 2:
        return "Mixed"

    if weighted_trend >= 0.50:
        return "Broadly Improving"

    if weighted_trend >= 0.15:
        return "Improving"

    if weighted_trend <= -0.50:
        return "Broadly Deteriorating"

    if weighted_trend <= -0.15:
        return "Deteriorating"

    return "Stable"


def detect_confirmations(
    pillar_map: dict[str, PillarResult],
) -> tuple[EnvironmentSignal, ...]:
    signals: list[EnvironmentSignal] = []

    growth = pillar_map.get("growth")
    labor = pillar_map.get("labor")
    inflation = pillar_map.get("inflation")
    liquidity = pillar_map.get("liquidity")

    if (
        growth is not None
        and labor is not None
        and growth.trend_score >= 0.20
        and labor.trend_score >= 0.20
    ):
        signals.append(
            EnvironmentSignal(
                code="growth_labor_improving",
                message=(
                    "Growth and labor are improving together, providing "
                    "confirmation of strengthening economic activity."
                ),
                pillars=("Growth", "Labor"),
                severity="positive",
            )
        )

    if (
        growth is not None
        and labor is not None
        and growth.trend_score <= -0.20
        and labor.trend_score <= -0.20
    ):
        signals.append(
            EnvironmentSignal(
                code="growth_labor_deteriorating",
                message=(
                    "Growth and labor are deteriorating together, confirming "
                    "broadening economic weakness."
                ),
                pillars=("Growth", "Labor"),
                severity="warning",
            )
        )

    if (
        growth is not None
        and liquidity is not None
        and growth.trend_score >= 0.20
        and liquidity.trend_score >= 0.20
    ):
        signals.append(
            EnvironmentSignal(
                code="growth_liquidity_supportive",
                message=(
                    "Growth and liquidity are improving together, creating "
                    "a more supportive macro backdrop."
                ),
                pillars=("Growth", "Liquidity"),
                severity="positive",
            )
        )

    if (
        inflation is not None
        and inflation.trend_score <= -0.20
        and inflation.breadth_score >= 0.50
    ):
        signals.append(
            EnvironmentSignal(
                code="broad_disinflation",
                message=(
                    "Inflation is easing with broad confirmation across "
                    "underlying inflation components."
                ),
                pillars=("Inflation",),
                severity="positive",
            )
        )

    return tuple(signals)


def detect_tensions(
    pillar_map: dict[str, PillarResult],
) -> tuple[EnvironmentSignal, ...]:
    signals: list[EnvironmentSignal] = []

    growth = pillar_map.get("growth")
    labor = pillar_map.get("labor")
    inflation = pillar_map.get("inflation")
    liquidity = pillar_map.get("liquidity")
    policy = pillar_map.get("policy")

    if (
        growth is not None
        and labor is not None
        and growth.trend_score >= 0.20
        and labor.trend_score <= -0.20
    ):
        signals.append(
            EnvironmentSignal(
                code="growth_labor_divergence",
                message=(
                    "Growth is improving while labor is deteriorating, "
                    "creating a meaningful divergence in the activity outlook."
                ),
                pillars=("Growth", "Labor"),
                severity="warning",
            )
        )

    if (
        growth is not None
        and labor is not None
        and growth.trend_score <= -0.20
        and labor.trend_score >= 0.20
    ):
        signals.append(
            EnvironmentSignal(
                code="labor_growth_divergence",
                message=(
                    "Labor is improving while broader growth is weakening, "
                    "suggesting uneven economic momentum."
                ),
                pillars=("Growth", "Labor"),
                severity="warning",
            )
        )

    if (
        growth is not None
        and liquidity is not None
        and growth.trend_score <= -0.20
        and liquidity.trend_score >= 0.20
    ):
        signals.append(
            EnvironmentSignal(
                code="weak_growth_improving_liquidity",
                message=(
                    "Liquidity is improving despite weakening growth, "
                    "creating a tension between economic and financial conditions."
                ),
                pillars=("Growth", "Liquidity"),
                severity="info",
            )
        )

    if (
        inflation is not None
        and policy is not None
        and inflation.trend_score <= -0.20
        and policy.state_score >= 0.35
    ):
        signals.append(
            EnvironmentSignal(
                code="easing_inflation_restrictive_policy",
                message=(
                    "Inflation is easing while policy remains restrictive, "
                    "raising the risk of an increasingly tight real policy stance."
                ),
                pillars=("Inflation", "Policy"),
                severity="warning",
            )
        )

    return tuple(signals)


def detect_transition_signals(
    pillar_results: tuple[PillarResult, ...],
) -> tuple[EnvironmentSignal, ...]:
    signals: list[EnvironmentSignal] = []

    positive = [
        result.name
        for result in pillar_results
        if result.trend_score >= 0.20
    ]
    negative = [
        result.name
        for result in pillar_results
        if result.trend_score <= -0.20
    ]

    if len(positive) >= 2 and len(negative) >= 2:
        signals.append(
            EnvironmentSignal(
                code="cross_pillar_transition",
                message=(
                    "The macro environment contains several improving and "
                    "deteriorating pillars, indicating a transitional state."
                ),
                pillars=tuple(positive + negative),
                severity="warning",
            )
        )

    weak_breadth = [
        result.name
        for result in pillar_results
        if abs(result.trend_score) >= 0.20
        and result.breadth_score < 0.40
    ]

    if weak_breadth:
        signals.append(
            EnvironmentSignal(
                code="narrow_pillar_movement",
                message=(
                    "One or more pillar movements lack broad internal "
                    "confirmation and may represent an early or fragile shift."
                ),
                pillars=tuple(weak_breadth),
                severity="info",
            )
        )

    return tuple(signals)


def identify_key_drivers(
    pillar_results: tuple[PillarResult, ...],
    limit: int = 3,
) -> tuple[str, ...]:
    """Return the pillars making the largest confidence-adjusted contribution."""

    ranked = sorted(
        pillar_results,
        key=lambda result: (
            abs(result.trend_score) * result.confidence_score,
            abs(result.state_score) * result.confidence_score,
        ),
        reverse=True,
    )

    drivers: list[str] = []

    for result in ranked[:limit]:
        direction = (
            "improving"
            if result.trend_score >= 0.15
            else "deteriorating"
            if result.trend_score <= -0.15
            else "stable"
        )

        drivers.append(
            f"{result.name}: {direction} "
            f"(trend={result.trend_score:.2f}, "
            f"confidence={result.confidence_score:.2f})"
        )

    return tuple(drivers)

def _confidence_weighted_average(
    components: tuple[tuple[float, float, float], ...],
) -> float:
    """
    Calculate a weighted average from:

        (score, model_weight, confidence)

    Confidence reduces the influence of weaker pillar readings.
    """

    numerator = 0.0
    denominator = 0.0

    for score, model_weight, confidence in components:
        effective_weight = model_weight * max(
            0.0,
            min(1.0, confidence),
        )

        numerator += score * effective_weight
        denominator += effective_weight

    if denominator <= 0.0:
        return 0.0

    return round(
        max(-1.0, min(1.0, numerator / denominator)),
        4,
    )


def calculate_activity_impulse(
    pillar_map: dict[str, PillarResult],
) -> float:
    """
    Calculate the activity impulse from Growth and Labor.

    Growth receives the larger weight because it directly measures broad
    economic activity. Labor provides confirmation and persistence.
    """

    growth = pillar_map.get("growth")
    labor = pillar_map.get("labor")

    components: list[tuple[float, float, float]] = []

    if growth is not None:
        components.append(
            (
                growth.trend_score,
                0.65,
                growth.confidence_score,
            )
        )

    if labor is not None:
        components.append(
            (
                labor.trend_score,
                0.35,
                labor.confidence_score,
            )
        )

    if not components:
        return 0.0

    return _confidence_weighted_average(tuple(components))


def classify_activity_impulse(score: float) -> str:
    if score >= 0.50:
        return "Strongly Expanding"

    if score >= 0.15:
        return "Expanding"

    if score <= -0.50:
        return "Contracting"

    if score <= -0.15:
        return "Slowing"

    return "Stable"


def calculate_inflation_impulse(
    pillar_map: dict[str, PillarResult],
) -> float:
    """
    Return the direction of inflation pressure.

    A positive score means inflation pressure is accelerating.
    A negative score means inflation pressure is easing.
    """

    inflation = pillar_map.get("inflation")

    if inflation is None:
        return 0.0

    return round(
        max(-1.0, min(1.0, inflation.trend_score)),
        4,
    )


def classify_inflation_impulse(score: float) -> str:
    if score >= 0.50:
        return "Strongly Accelerating"

    if score >= 0.15:
        return "Accelerating"

    if score <= -0.50:
        return "Strongly Easing"

    if score <= -0.15:
        return "Easing"

    return "Stable"


def calculate_financial_impulse(
    pillar_map: dict[str, PillarResult],
) -> float:
    """
    Calculate the financial impulse from Liquidity and Policy.

    Liquidity receives the larger weight because it measures current
    financial-system support. Policy provides the monetary-policy impulse.

    The current policy model is assumed to use a positive trend score when
    policy is becoming less restrictive and a negative score when policy is
    becoming more restrictive.
    """

    liquidity = pillar_map.get("liquidity")
    policy = pillar_map.get("policy")

    components: list[tuple[float, float, float]] = []

    if liquidity is not None:
        components.append(
            (
                liquidity.trend_score,
                0.60,
                liquidity.confidence_score,
            )
        )

    if policy is not None:
        components.append(
            (
                policy.trend_score,
                0.40,
                policy.confidence_score,
            )
        )

    if not components:
        return 0.0

    return _confidence_weighted_average(tuple(components))


def classify_financial_impulse(score: float) -> str:
    if score >= 0.50:
        return "Strongly Supportive"

    if score >= 0.15:
        return "Supportive"

    if score <= -0.50:
        return "Strongly Restrictive"

    if score <= -0.15:
        return "Restrictive"

    return "Neutral"


def classify_macro_environment(
    activity_score: float,
    inflation_impulse_score: float,
    financial_impulse_score: float,
) -> str:
    """
    Classify the economy using activity, inflation, and financial impulses.

    This deliberately avoids compressing every pillar into a generic
    good-versus-bad direction.
    """

    activity_positive = activity_score >= 0.15
    activity_negative = activity_score <= -0.15

    inflation_positive = inflation_impulse_score >= 0.15
    inflation_negative = inflation_impulse_score <= -0.15

    financial_supportive = financial_impulse_score >= 0.15
    financial_restrictive = financial_impulse_score <= -0.15

    if activity_positive and inflation_negative:
        if financial_supportive:
            return "Goldilocks Expansion"

        return "Disinflationary Expansion"

    if activity_positive and inflation_positive:
        if financial_supportive:
            return "Reflationary Expansion"

        if financial_restrictive:
            return "Restrictive Reflation"

        return "Reflationary Transition"

    if activity_negative and inflation_positive:
        if financial_restrictive:
            return "Stagflationary Slowdown"

        return "Stagflationary Transition"

    if activity_negative and inflation_negative:
        if financial_supportive:
            return "Policy-Response Slowdown"

        if financial_restrictive:
            return "Disinflationary Contraction"

        return "Disinflationary Slowdown"

    if activity_positive:
        return "Activity-Led Expansion"

    if activity_negative:
        return "Activity Slowdown"

    if inflation_positive:
        return "Inflationary Transition"

    if inflation_negative:
        return "Disinflationary Transition"

    if financial_supportive:
        return "Financial Easing Transition"

    if financial_restrictive:
        return "Financial Tightening Transition"

    return "Mixed / Transitional"


def build_environment_summary(
    activity_label: str,
    inflation_impulse_label: str,
    financial_impulse_label: str,
    environment_label: str,
) -> str:
    return (
        f"The macro environment is classified as {environment_label}. "
        f"Activity is {activity_label.lower()}, inflation pressure is "
        f"{inflation_impulse_label.lower()}, and the financial impulse is "
        f"{financial_impulse_label.lower()}."
    )
    
def calculate_dimension_margin(score: float) -> float:
    """
    Measure how far a score is from its nearest classification boundary.

    A margin of:
        0.0 = directly on a boundary
        1.0 = firmly inside the current classification range

    Neutral scores use +/-0.15 as their boundaries.
    Directional scores use 0.15 to 0.50 as the robustness range.
    """

    bounded_score = max(-1.0, min(1.0, score))

    if -0.15 < bounded_score < 0.15:
        distance = min(
            bounded_score - (-0.15),
            0.15 - bounded_score,
        )

        return round(
            max(0.0, min(1.0, distance / 0.15)),
            4,
        )

    if bounded_score >= 0.15:
        distance = bounded_score - 0.15

        return round(
            max(0.0, min(1.0, distance / 0.35)),
            4,
        )

    distance = -0.15 - bounded_score

    return round(
        max(0.0, min(1.0, distance / 0.35)),
        4,
    )


def calculate_dimension_margins(
    activity_score: float,
    inflation_impulse_score: float,
    financial_impulse_score: float,
) -> dict[str, float]:
    return {
        "activity": calculate_dimension_margin(activity_score),
        "inflation": calculate_dimension_margin(
            inflation_impulse_score
        ),
        "financial": calculate_dimension_margin(
            financial_impulse_score
        ),
    }


def calculate_environment_conviction(
    confidence_score: float,
    dimension_margins: dict[str, float],
) -> float:
    """
    Combine model confidence with classification robustness.

    Average margin captures broad robustness.

    Minimum margin ensures that one fragile dimension reduces conviction,
    without allowing it to completely dominate the result.
    """

    if not dimension_margins:
        return 0.0

    margins = tuple(dimension_margins.values())

    average_margin = sum(margins) / len(margins)
    minimum_margin = min(margins)

    robustness_score = (
        0.75 * average_margin
        + 0.25 * minimum_margin
    )

    conviction = confidence_score * robustness_score

    return round(
        max(0.0, min(1.0, conviction)),
        4,
    )


def classify_environment_conviction(score: float) -> str:
    if score >= 0.70:
        return "High"

    if score >= 0.35:
        return "Moderate"

    return "Low"


def detect_dimension_boundary_flags(
    dimension_margins: dict[str, float],
    warning_threshold: float = 0.20,
) -> tuple[str, ...]:
    """
    Flag dimensions that are close to a classification boundary.
    """

    flags: list[str] = []

    for dimension, margin in dimension_margins.items():
        if margin < warning_threshold:
            flags.append(f"{dimension}_near_boundary")

    return tuple(flags)

def build_environment_result(
    config: MacroEnvironmentConfig,
    pillar_results: Iterable[PillarResult],
    as_of_date: date | None = None,
) -> MacroEnvironmentResult:
    """Build a complete macro-environment result."""

    results = validate_environment_inputs(config, pillar_results)

    normalized_map = {
        _canonical_pillar_name(result, config.economy): result
        for result in results
    }

    public_map = {
        result.name: result for result in results
    }

    confidence_score = calculate_environment_confidence(results)
    confidence_label = classify_environment_confidence(confidence_score)
    overall_direction = calculate_overall_direction(results)

    activity_score = calculate_activity_impulse(normalized_map)
    activity_label = classify_activity_impulse(activity_score)

    inflation_impulse_score = calculate_inflation_impulse(normalized_map)
    inflation_impulse_label = classify_inflation_impulse(
        inflation_impulse_score
    )

    financial_impulse_score = calculate_financial_impulse(normalized_map)
    financial_impulse_label = classify_financial_impulse(
        financial_impulse_score
    )

    environment_label = classify_macro_environment(
        activity_score=activity_score,
        inflation_impulse_score=inflation_impulse_score,
        financial_impulse_score=financial_impulse_score,
    )

    environment_summary = build_environment_summary(
        activity_label=activity_label,
        inflation_impulse_label=inflation_impulse_label,
        financial_impulse_label=financial_impulse_label,
        environment_label=environment_label,
    )
    
    dimension_margins = calculate_dimension_margins(
        activity_score=activity_score,
        inflation_impulse_score=inflation_impulse_score,
        financial_impulse_score=financial_impulse_score,
    )

    environment_conviction_score = (
        calculate_environment_conviction(
            confidence_score=confidence_score,
            dimension_margins=dimension_margins,
        )
    )

    environment_conviction_label = (
        classify_environment_conviction(
            environment_conviction_score
        )
    )

    boundary_flags = detect_dimension_boundary_flags(
        dimension_margins
    )

    confirmations = detect_confirmations(normalized_map)
    tensions = detect_tensions(normalized_map)
    transition_signals = detect_transition_signals(results)

    flags: list[str] = []

    flags.extend(boundary_flags)

    if confidence_score < config.minimum_confidence:
        flags.append("low_environment_confidence")

    if overall_direction == "Mixed":
        flags.append("mixed_pillar_direction")

    diagnostics = {
        "pillar_count": len(results),
        "average_state_score": round(
            fmean(result.state_score for result in results),
            4,
        ),
        "average_trend_score": round(
            fmean(result.trend_score for result in results),
            4,
        ),
        "positive_trend_pillars": tuple(
            result.name
            for result in results
            if result.trend_score >= 0.20
        ),
        "negative_trend_pillars": tuple(
            result.name
            for result in results
            if result.trend_score <= -0.20
        ),
        "activity_margin": dimension_margins["activity"],
        "inflation_margin": dimension_margins["inflation"],
        "financial_margin": dimension_margins["financial"],
        "environment_conviction_score": (
            environment_conviction_score
        ),
    }

    return MacroEnvironmentResult(
        economy=config.economy,
        as_of_date=as_of_date,
        pillar_results=results,
        pillar_map=public_map,
        overall_direction=overall_direction,
        activity_score=activity_score,
        activity_label=activity_label,
        inflation_impulse_score=inflation_impulse_score,
        inflation_impulse_label=inflation_impulse_label,
        financial_impulse_score=financial_impulse_score,
        financial_impulse_label=financial_impulse_label,
        environment_label=environment_label,
        environment_summary=environment_summary,
        confirmations=confirmations,
        tensions=tensions,
        transition_signals=transition_signals,
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        key_drivers=identify_key_drivers(results),
        flags=tuple(flags),
        environment_conviction_score=environment_conviction_score,
        environment_conviction_label=environment_conviction_label,
        dimension_margins=dimension_margins,
        diagnostics=diagnostics,
    )