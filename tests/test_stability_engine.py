"""Tests for historical regime stability and churn validation."""

from datetime import date

import pytest

from macro_engine.engine.validation_engine import (
    build_stability_validation_summary,
    calculate_regime_stability_statistics,
    count_regime_oscillations,
)
from macro_engine.models.environment import (
    MacroEnvironmentHistory,
    MacroEnvironmentSnapshot,
)


def make_snapshot(
    *,
    as_of_date: date,
    environment_label: str,
    confidence_score: float = 0.80,
    conviction_score: float = 0.60,
) -> MacroEnvironmentSnapshot:
    return MacroEnvironmentSnapshot(
        economy="USA",
        as_of_date=as_of_date,
        activity_score=0.20,
        activity_label="Stable",
        inflation_impulse_score=0.00,
        inflation_impulse_label="Stable",
        financial_impulse_score=0.10,
        financial_impulse_label="Neutral",
        environment_label=environment_label,
        confidence_score=confidence_score,
        environment_conviction_score=(
            conviction_score
        ),
        environment_conviction_label="Moderate",
    )


def make_stability_history() -> MacroEnvironmentHistory:
    """
    Regime periods:

    Expansion: Jan-Feb
    Slowdown: Mar
    Expansion: Apr-May
    Reflation: Jun
    Expansion: Jul-Aug

    Oscillations:

    Expansion -> Slowdown -> Expansion
    Expansion -> Reflation -> Expansion
    """

    return MacroEnvironmentHistory(
        economy="USA",
        snapshots=(
            make_snapshot(
                as_of_date=date(2025, 1, 31),
                environment_label="Expansion",
                confidence_score=0.90,
                conviction_score=0.80,
            ),
            make_snapshot(
                as_of_date=date(2025, 2, 28),
                environment_label="Expansion",
                confidence_score=0.70,
                conviction_score=0.50,
            ),
            make_snapshot(
                as_of_date=date(2025, 3, 31),
                environment_label="Slowdown",
                confidence_score=0.60,
                conviction_score=0.30,
            ),
            make_snapshot(
                as_of_date=date(2025, 4, 30),
                environment_label="Expansion",
                confidence_score=0.80,
                conviction_score=0.60,
            ),
            make_snapshot(
                as_of_date=date(2025, 5, 31),
                environment_label="Expansion",
                confidence_score=0.75,
                conviction_score=0.55,
            ),
            make_snapshot(
                as_of_date=date(2025, 6, 30),
                environment_label="Reflation",
                confidence_score=0.65,
                conviction_score=0.40,
            ),
            make_snapshot(
                as_of_date=date(2025, 7, 31),
                environment_label="Expansion",
                confidence_score=0.85,
                conviction_score=0.70,
            ),
            make_snapshot(
                as_of_date=date(2025, 8, 31),
                environment_label="Expansion",
                confidence_score=0.80,
                conviction_score=0.65,
            ),
        ),
    )


def test_count_regime_oscillations() -> None:
    assert (
        count_regime_oscillations(
            make_stability_history()
        )
        == 2
    )


def test_calculate_regime_stability_statistics() -> None:
    statistics = calculate_regime_stability_statistics(
        make_stability_history()
    )

    expansion = next(
        result
        for result in statistics
        if result.environment_label == "Expansion"
    )

    assert expansion.occurrence_count == 3
    assert expansion.completed_occurrence_count == 2
    assert expansion.observation_count == 6

    assert (
        expansion.average_duration_observations
        == 2.0
    )
    assert (
        expansion.median_duration_observations
        == 2.0
    )
    assert expansion.minimum_duration_observations == 2
    assert expansion.maximum_duration_observations == 2

    assert expansion.short_lived_occurrence_count == 0
    assert expansion.short_lived_occurrence_ratio == 0.0
    assert expansion.current_regime is True


def test_short_lived_regime_statistics() -> None:
    statistics = calculate_regime_stability_statistics(
        make_stability_history()
    )

    slowdown = next(
        result
        for result in statistics
        if result.environment_label == "Slowdown"
    )

    assert slowdown.occurrence_count == 1
    assert slowdown.completed_occurrence_count == 1
    assert slowdown.short_lived_occurrence_count == 1
    assert slowdown.short_lived_occurrence_ratio == 1.0


def test_confidence_and_conviction_change() -> None:
    statistics = calculate_regime_stability_statistics(
        make_stability_history()
    )

    expansion = next(
        result
        for result in statistics
        if result.environment_label == "Expansion"
    )

    assert (
        expansion.average_starting_confidence_score
        == pytest.approx(
            0.85,
            abs=0.0001,
        )
    )

    assert (
        expansion.average_ending_confidence_score
        == pytest.approx(
            0.75,
            abs=0.0001,
        )
    )

    assert (
        expansion.average_confidence_change
        == pytest.approx(
            -0.10,
            abs=0.0001,
        )
    )


def test_build_stability_validation_summary() -> None:
    summary = build_stability_validation_summary(
        make_stability_history()
    )

    assert summary.economy == "USA"
    assert summary.observation_count == 8
    assert summary.regime_period_count == 5
    assert summary.completed_regime_period_count == 4
    assert summary.completed_transition_count == 4

    assert (
        summary.average_regime_duration_observations
        == 1.6
    )

    assert (
        summary.median_regime_duration_observations
        == 2.0
    )

    assert summary.short_lived_period_count == 2
    assert summary.short_lived_period_ratio == 0.4

    assert summary.short_lived_observation_count == 2
    assert summary.short_lived_observation_ratio == 0.25

    assert summary.oscillation_count == 2

    assert summary.oscillation_ratio == pytest.approx(
        2 / 3,
        abs=0.0001,
    )

    assert summary.churn_label == "High Churn"


def test_single_regime_history_has_zero_churn() -> None:
    history = MacroEnvironmentHistory(
        economy="USA",
        snapshots=(
            make_snapshot(
                as_of_date=date(2025, 1, 31),
                environment_label="Expansion",
            ),
            make_snapshot(
                as_of_date=date(2025, 2, 28),
                environment_label="Expansion",
            ),
        ),
    )

    summary = build_stability_validation_summary(
        history
    )

    assert summary.regime_period_count == 1
    assert summary.completed_regime_period_count == 0
    assert summary.completed_transition_count == 0
    assert summary.annualized_transition_rate == 0.0
    assert summary.oscillation_count == 0
    assert summary.oscillation_ratio == 0.0
    assert summary.churn_label == "Low Churn"


def test_invalid_short_lived_threshold_raises() -> None:
    history = make_stability_history()

    with pytest.raises(
        ValueError,
        match="must be at least 1",
    ):
        calculate_regime_stability_statistics(
            history,
            short_lived_max_observations=0,
        )

    with pytest.raises(
        ValueError,
        match="must be at least 1",
    ):
        build_stability_validation_summary(
            history,
            short_lived_max_observations=0,
        )