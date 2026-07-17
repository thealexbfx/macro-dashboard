"""Reusable bucket aggregation logic for the MacroLens Engine."""

from collections.abc import Sequence
from macro_engine.models.bucket import BucketConfig, BucketResult
from macro_engine.models.indicator import IndicatorResult


def prepare_bucket_results(
    results: Sequence[IndicatorResult],
    config: BucketConfig,
) -> tuple[IndicatorResult, ...]:
    """
    Validate and filter indicator results for a bucket.
    """
    valid_results = tuple(
        result
        for result in results
        if result.is_valid
        and result.economy == config.economy
        and result.pillar == config.pillar
    )

    if len(valid_results) < config.minimum_indicators:
        raise ValueError(
            f"{config.bucket_id} requires at least "
            f"{config.minimum_indicators} valid indicators."
        )

    return valid_results


def calculate_bucket_state_score(
    results: Sequence[IndicatorResult],
    config: BucketConfig,
) -> float:
    """
    Calculate a normalized weighted average of indicator state scores.
    """
    prepared = prepare_bucket_results(results, config)

    weighted_total = 0.0
    weight_total = 0.0

    for result in prepared:
        weight = config.indicator_weights.get(result.indicator_id, 1.0)

        weighted_total += result.state_score * weight
        weight_total += weight

    if weight_total <= 0:
        raise ValueError(
            f"{config.bucket_id} has no usable indicator weights."
        )

    return float(weighted_total / weight_total)
    
def classify_bucket_state(score: float) -> str:
    """Convert a bucket state score into an economic label."""
    if score >= 0.60:
        return "Very Strong"

    if score >= 0.20:
        return "Strong"

    if score > -0.20:
        return "Normal"

    if score > -0.60:
        return "Weak"

    return "Very Weak"


def calculate_bucket_trend_score(
    results: Sequence[IndicatorResult],
    config: BucketConfig,
) -> float:
    """
    Calculate a normalized weighted average of indicator trend scores.
    """
    prepared = prepare_bucket_results(results, config)

    weighted_total = 0.0
    weight_total = 0.0

    for result in prepared:
        weight = config.indicator_weights.get(result.indicator_id, 1.0)

        weighted_total += result.trend_score * weight
        weight_total += weight

    if weight_total <= 0:
        raise ValueError(
            f"{config.bucket_id} has no usable indicator weights."
        )

    return float(weighted_total / weight_total)


def classify_bucket_trend(score: float) -> str:
    """Convert a bucket trend score into a directional label."""
    if score >= 0.20:
        return "Improving"

    if score <= -0.20:
        return "Deteriorating"

    return "Stable"
    
def calculate_bucket_breadth_score(
    results: Sequence[IndicatorResult],
    config: BucketConfig,
) -> float:
    """
    Measure how many indicators support a positive bucket signal.

    Returns a score from -1 to +1:
    +1 means all indicators are positive.
    -1 means all indicators are negative.
    """
    prepared = prepare_bucket_results(results, config)

    positive = sum(result.state_score > 0.10 for result in prepared)
    negative = sum(result.state_score < -0.10 for result in prepared)

    return float((positive - negative) / len(prepared))


def classify_bucket_breadth(score: float) -> str:
    """Convert bucket breadth into a descriptive label."""
    if score >= 0.75:
        return "Broadly Positive"

    if score >= 0.25:
        return "Mostly Positive"

    if score > -0.25:
        return "Mixed"

    if score > -0.75:
        return "Mostly Negative"

    return "Broadly Negative"
    
def calculate_bucket_confidence_score(
    results: Sequence[IndicatorResult],
    config: BucketConfig,
) -> float:
    """
    Calculate confidence using indicator weights and confidence scores.

    Indicators with larger bucket weights contribute more to the result.
    """
    prepared = prepare_bucket_results(results, config)

    weighted_total = 0.0
    weight_total = 0.0

    for result in prepared:
        weight = config.indicator_weights.get(result.indicator_id, 1.0)

        weighted_total += result.confidence_score * weight
        weight_total += weight

    if weight_total <= 0:
        raise ValueError(
            f"{config.bucket_id} has no usable indicator weights."
        )

    return float(weighted_total / weight_total)


def classify_bucket_confidence(score: float) -> str:
    """Convert a bucket confidence score into a display label."""
    if score >= 0.90:
        return "Very High"

    if score >= 0.75:
        return "High"

    if score >= 0.60:
        return "Moderate"

    if score >= 0.40:
        return "Low"

    return "Very Low"


def identify_key_drivers(
    results: Sequence[IndicatorResult],
    config: BucketConfig,
    limit: int = 3,
) -> tuple[str, ...]:
    """
    Identify the indicators making the largest contributions to bucket state.

    Contribution equals indicator state score multiplied by bucket weight.
    """
    prepared = prepare_bucket_results(results, config)

    contributions = []

    for result in prepared:
        weight = config.indicator_weights.get(result.indicator_id, 1.0)
        contribution = result.state_score * weight

        contributions.append(
            (
                abs(contribution),
                contribution,
                result.name,
            )
        )

    contributions.sort(reverse=True)

    drivers = []

    for _, contribution, name in contributions[:limit]:
        if contribution > 0:
            direction = "positive"
        elif contribution < 0:
            direction = "negative"
        else:
            direction = "neutral"

        drivers.append(
            f"{name}: {direction} contribution ({contribution:+.3f})"
        )

    return tuple(drivers)
    
def run_bucket(
    results: Sequence[IndicatorResult],
    config: BucketConfig,
) -> BucketResult:
    """
    Run the full MacroLens bucket aggregation pipeline.
    """
    prepared = prepare_bucket_results(results, config)

    state_score = calculate_bucket_state_score(prepared, config)
    trend_score = calculate_bucket_trend_score(prepared, config)
    breadth_score = calculate_bucket_breadth_score(prepared, config)
    confidence_score = calculate_bucket_confidence_score(prepared, config)

    key_drivers = identify_key_drivers(
        prepared,
        config,
        limit=min(3, len(prepared)),
    )

    flags: list[str] = []

    expected_indicator_ids = set(config.indicator_weights)
    used_indicator_ids = {
        result.indicator_id
        for result in prepared
    }

    missing_indicator_ids = expected_indicator_ids - used_indicator_ids

    if missing_indicator_ids:
        flags.append(
            "missing_indicators: "
            + ", ".join(sorted(missing_indicator_ids))
        )

    if breadth_score == 0:
        flags.append("mixed_breadth")

    if state_score > 0.20 and trend_score < -0.20:
        flags.append("positive_but_deteriorating")

    if state_score < -0.20 and trend_score > 0.20:
        flags.append("weak_but_improving")

    diagnostics = {
        "configured_indicators": len(config.indicator_weights),
        "indicators_used": len(prepared),
        "weights_used": {
            result.indicator_id: config.indicator_weights.get(
                result.indicator_id,
                1.0,
            )
            for result in prepared
        },
        "indicator_state_scores": {
            result.indicator_id: result.state_score
            for result in prepared
        },
        "indicator_trend_scores": {
            result.indicator_id: result.trend_score
            for result in prepared
        },
        "missing_indicator_ids": sorted(missing_indicator_ids),
    }

    return BucketResult(
        bucket_id=config.bucket_id,
        name=config.name,
        economy=config.economy,
        pillar=config.pillar,
        state_score=state_score,
        state_label=classify_bucket_state(state_score),
        trend_score=trend_score,
        trend_label=classify_bucket_trend(trend_score),
        breadth_score=breadth_score,
        breadth_label=classify_bucket_breadth(breadth_score),
        confidence_score=confidence_score,
        confidence_label=classify_bucket_confidence(confidence_score),
        indicators_used=len(prepared),
        indicator_results=prepared,
        key_drivers=key_drivers,
        flags=tuple(flags),
        diagnostics=diagnostics,
    )