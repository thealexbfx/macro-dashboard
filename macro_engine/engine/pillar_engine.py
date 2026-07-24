"""Reusable pillar aggregation logic for the MacroLens Engine."""

from collections.abc import Sequence

from macro_engine.models.bucket import BucketResult
from macro_engine.models.pillar import PillarConfig, PillarResult


def prepare_pillar_results(
    results: Sequence[BucketResult],
    config: PillarConfig,
) -> tuple[BucketResult, ...]:
    """
    Validate and filter bucket results for a pillar.
    """
    valid_results = tuple(
        result
        for result in results
        if result.is_valid
        and result.economy == config.economy
        and result.pillar == config.pillar
    )

    if len(valid_results) < config.minimum_buckets:
        raise ValueError(
            f"{config.pillar_id} requires at least "
            f"{config.minimum_buckets} valid buckets."
        )

    return valid_results


def calculate_pillar_state_score(
    results: Sequence[BucketResult],
    config: PillarConfig,
) -> float:
    """
    Calculate a normalized weighted average of bucket state scores.
    """
    prepared = prepare_pillar_results(results, config)

    weighted_total = 0.0
    weight_total = 0.0

    for result in prepared:
        weight = config.bucket_weights.get(result.bucket_id, 1.0)

        weighted_total += result.state_score * weight
        weight_total += weight

    if weight_total <= 0:
        raise ValueError(
            f"{config.pillar_id} has no usable bucket weights."
        )

    return float(weighted_total / weight_total)


def classify_pillar_state(score: float) -> str:
    """Convert a pillar state score into an economic label."""
    if score >= 0.60:
        return "Very Strong"

    if score >= 0.20:
        return "Strong"

    if score > -0.20:
        return "Normal"

    if score > -0.60:
        return "Weak"

    return "Very Weak"


def calculate_pillar_trend_score(
    results: Sequence[BucketResult],
    config: PillarConfig,
) -> float:
    """
    Calculate a normalized weighted average of bucket trend scores.
    """
    prepared = prepare_pillar_results(results, config)

    weighted_total = 0.0
    weight_total = 0.0

    for result in prepared:
        weight = config.bucket_weights.get(result.bucket_id, 1.0)

        weighted_total += result.trend_score * weight
        weight_total += weight

    if weight_total <= 0:
        raise ValueError(
            f"{config.pillar_id} has no usable bucket weights."
        )

    return float(weighted_total / weight_total)


def classify_pillar_trend(score: float) -> str:
    """Convert a pillar trend score into a directional label."""
    if score >= 0.20:
        return "Improving"

    if score <= -0.20:
        return "Deteriorating"

    return "Stable"


def calculate_pillar_breadth_score(
    results: Sequence[BucketResult],
    config: PillarConfig,
) -> float:
    """
    Measure how many buckets support a positive pillar signal.

    Returns a score from -1 to +1:
    +1 means all buckets are positive.
    -1 means all buckets are negative.
    """
    prepared = prepare_pillar_results(results, config)

    positive = sum(result.state_score > 0.10 for result in prepared)
    negative = sum(result.state_score < -0.10 for result in prepared)

    return float((positive - negative) / len(prepared))


def classify_pillar_breadth(score: float) -> str:
    """Convert pillar breadth into a descriptive label."""
    if score >= 0.75:
        return "Broadly Positive"

    if score >= 0.25:
        return "Mostly Positive"

    if score > -0.25:
        return "Mixed"

    if score > -0.75:
        return "Mostly Negative"

    return "Broadly Negative"


def calculate_pillar_confidence_score(
    results: Sequence[BucketResult],
    config: PillarConfig,
) -> float:
    """
    Calculate confidence using bucket weights and confidence scores.
    """
    prepared = prepare_pillar_results(results, config)

    weighted_total = 0.0
    weight_total = 0.0

    for result in prepared:
        weight = config.bucket_weights.get(result.bucket_id, 1.0)

        weighted_total += result.confidence_score * weight
        weight_total += weight

    if weight_total <= 0:
        raise ValueError(
            f"{config.pillar_id} has no usable bucket weights."
        )

    return float(weighted_total / weight_total)


def classify_pillar_confidence(score: float) -> str:
    """Convert a pillar confidence score into a display label."""
    if score >= 0.90:
        return "Very High"

    if score >= 0.75:
        return "High"

    if score >= 0.60:
        return "Moderate"

    if score >= 0.40:
        return "Low"

    return "Very Low"


def identify_pillar_key_drivers(
    results: Sequence[BucketResult],
    config: PillarConfig,
    limit: int = 3,
) -> tuple[str, ...]:
    """
    Identify the buckets making the largest contributions to pillar state.

    Contribution equals bucket state score multiplied by pillar weight.
    """
    prepared = prepare_pillar_results(results, config)

    contributions = []

    for result in prepared:
        weight = config.bucket_weights.get(result.bucket_id, 1.0)
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


def run_pillar(
    results: Sequence[BucketResult],
    config: PillarConfig,
) -> PillarResult:
    """
    Run the full MacroLens pillar aggregation pipeline.
    """
    prepared = prepare_pillar_results(results, config)

    state_score = calculate_pillar_state_score(prepared, config)
    trend_score = calculate_pillar_trend_score(prepared, config)
    breadth_score = calculate_pillar_breadth_score(prepared, config)
    confidence_score = calculate_pillar_confidence_score(
        prepared,
        config,
    )

    key_drivers = identify_pillar_key_drivers(
        prepared,
        config,
        limit=min(3, len(prepared)),
    )

    flags: list[str] = []

    expected_bucket_ids = set(config.bucket_weights)
    used_bucket_ids = {
        result.bucket_id
        for result in prepared
    }

    missing_bucket_ids = expected_bucket_ids - used_bucket_ids

    if missing_bucket_ids:
        flags.append(
            "missing_buckets: "
            + ", ".join(sorted(missing_bucket_ids))
        )

    if breadth_score == 0:
        flags.append("mixed_breadth")

    if state_score > 0.20 and trend_score < -0.20:
        flags.append("positive_but_deteriorating")

    if state_score < -0.20 and trend_score > 0.20:
        flags.append("weak_but_improving")

    diagnostics = {
        "configured_buckets": len(config.bucket_weights),
        "buckets_used": len(prepared),
        "weights_used": {
            result.bucket_id: config.bucket_weights.get(
                result.bucket_id,
                1.0,
            )
            for result in prepared
        },
        "bucket_state_scores": {
            result.bucket_id: result.state_score
            for result in prepared
        },
        "bucket_trend_scores": {
            result.bucket_id: result.trend_score
            for result in prepared
        },
        "missing_bucket_ids": sorted(missing_bucket_ids),
    }

    return PillarResult(
        pillar_id=config.pillar_id,
        name=config.name,
        economy=config.economy,
        state_score=state_score,
        state_label=classify_pillar_state(state_score),
        trend_score=trend_score,
        trend_label=classify_pillar_trend(trend_score),
        breadth_score=breadth_score,
        breadth_label=classify_pillar_breadth(breadth_score),
        confidence_score=confidence_score,
        confidence_label=classify_pillar_confidence(
            confidence_score,
        ),
        buckets_used=len(prepared),
        bucket_results=prepared,
        key_drivers=key_drivers,
        flags=tuple(flags),
        diagnostics=diagnostics,
    )