from __future__ import annotations

from dataclasses import dataclass

from macro_engine.models.environment import (
    MacroEnvironmentResult,
    MacroEnvironmentSnapshot,
)
from macro_engine.models.pillar import PillarResult


ECONOMY_DISPLAY_NAMES = {
    "USA": "United States",
    "US": "United States",
    "EURO": "Euro Area",
    "EURO AREA": "Euro Area",
    "UK": "United Kingdom",
    "UNITED KINGDOM": "United Kingdom",
    "JAPAN": "Japan",
}


def economy_display_name(value: str) -> str:
    return ECONOMY_DISPLAY_NAMES.get(value.strip().upper(), value)


@dataclass(frozen=True)
class ComparisonObservation:
    category: str
    economy: str
    message: str
    score: float


@dataclass(frozen=True)
class RecentEnvironmentChange:
    economy: str
    current_environment: str
    previous_environment: str
    changed: bool
    overall_direction: str
    confidence_score: float
    confidence_label: str
    conviction_score: float
    conviction_label: str


def pillar_for(
    result: MacroEnvironmentResult,
    pillar_name: str,
) -> PillarResult | None:
    target = pillar_name.casefold()

    for pillar in result.pillar_results:
        identifiers = (
            pillar.pillar_id.casefold(),
            pillar.name.casefold(),
        )
        if any(target == value or value.endswith(f"_{target}") for value in identifiers):
            return pillar
        if any(target in value.split() for value in identifiers):
            return pillar

    return None


def build_comparison_observations(
    results: tuple[MacroEnvironmentResult, ...],
    limit: int = 4,
) -> tuple[ComparisonObservation, ...]:
    if limit < 1 or not results:
        return ()

    candidates: list[ComparisonObservation] = []
    specifications = (
        ("Growth", "growth", max, "strongest growth"),
        ("Liquidity", "liquidity", min, "weakest liquidity"),
        ("Inflation", "inflation", max, "highest inflation"),
        ("Policy", "policy", max, "strongest policy"),
    )

    for category, pillar_name, selector, description in specifications:
        available = [
            (result, pillar_for(result, pillar_name))
            for result in results
        ]
        available = [
            (result, pillar)
            for result, pillar in available
            if pillar is not None
        ]
        if not available:
            continue

        selected_result, selected_pillar = selector(
            available,
            key=lambda item: item[1].state_score,
        )
        candidates.append(
            ComparisonObservation(
                category=category,
                economy=economy_display_name(selected_result.economy),
                message=(
                    f"{economy_display_name(selected_result.economy)} currently has the {description} "
                    f"state among the available economies ({selected_pillar.state_label}, "
                    f"{selected_pillar.state_score:+.2f})."
                ),
                score=selected_pillar.state_score,
            )
        )

    if len(candidates) < limit:
        highest_confidence = max(results, key=lambda item: item.confidence_score)
        candidates.append(
            ComparisonObservation(
                category="Confidence",
                economy=economy_display_name(highest_confidence.economy),
                message=(
                    f"{economy_display_name(highest_confidence.economy)} currently has the highest model "
                    f"confidence at {highest_confidence.confidence_score:.0%}."
                ),
                score=highest_confidence.confidence_score,
            )
        )

    if len(candidates) < limit:
        lowest_conviction = min(
            results,
            key=lambda item: item.environment_conviction_score,
        )
        candidates.append(
            ComparisonObservation(
                category="Conviction",
                economy=economy_display_name(lowest_conviction.economy),
                message=(
                    f"{economy_display_name(lowest_conviction.economy)} currently has the lowest environment "
                    f"conviction at {lowest_conviction.environment_conviction_score:.0%}."
                ),
                score=lowest_conviction.environment_conviction_score,
            )
        )

    return tuple(candidates[:limit])


def build_recent_environment_change(
    result: MacroEnvironmentResult,
    snapshots: tuple[MacroEnvironmentSnapshot, ...],
) -> RecentEnvironmentChange | None:
    if len(snapshots) < 2:
        return None

    ordered = sorted(snapshots, key=lambda item: item.as_of_date)
    current, previous = ordered[-1], ordered[-2]

    return RecentEnvironmentChange(
        economy=economy_display_name(result.economy),
        current_environment=current.environment_label,
        previous_environment=previous.environment_label,
        changed=current.environment_label != previous.environment_label,
        overall_direction=result.overall_direction,
        confidence_score=result.confidence_score,
        confidence_label=result.confidence_label,
        conviction_score=result.environment_conviction_score,
        conviction_label=result.environment_conviction_label,
    )
