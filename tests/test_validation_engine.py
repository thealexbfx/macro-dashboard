"""Tests for historical macro-environment validation."""

from datetime import date

import pytest

from macro_engine.engine.validation_engine import (
    build_environment_validation_summary,
    calculate_regime_statistics,
    is_transitional_regime,
)
from macro_engine.models.environment import (
    MacroEnvironmentHistory,
    MacroEnvironmentSnapshot,
)


def make_snapshot(
    *,
    as_of_date: date,
    environment_label: str,
    activity_score: float = 0.20,
    inflation_score: float = -0.10,
    financial_score: float = 0.15,
    confidence_score: float = 0.80,
    conviction_score: float = 0.60,
) -> MacroEnvironmentSnapshot:
    return MacroEnvironmentSnapshot(
        economy="USA",
        as_of_date=as_of_date,
        activity_score=activity_score,
        activity_label="Expanding",
        inflation_impulse_score=inflation_score,
        inflation_impulse_label="Easing",
        financial_impulse_score=financial_score,
        financial_impulse_label="Supportive",
        environment_label=environment_label,
        confidence_score=confidence_score,
        environment_conviction_score=(
            conviction_score
        ),
        environment_conviction_label="Moderate",
    )


def make_history() -> MacroEnvironmentHistory:
    return MacroEnvironmentHistory(
        economy="USA",
        snapshots=(
            make_snapshot(
                as_of_date=date(2025, 1, 31),
                environment_label=(
                    "Goldilocks Expansion"
                ),
                activity_score=0.40,
                confidence_score=0.80,
                conviction_score=0.60,
            ),
            make_snapshot(
                as_of_date=date(2025, 2, 28),
                environment_label=(
                    "Goldilocks Expansion"
                ),
                activity_score=0.50,
                confidence_score=0.90,
                conviction_score=0.70,
            ),
            make_snapshot(
                as_of_date=date(2025, 3, 31),
                environment_label=(
                    "Mixed / Transitional"
                ),
                activity_score=0.00,
                confidence_score=0.60,
                conviction_score=0.20,
            ),
            make_snapshot(
                as_of_date=date(2025, 4, 30),
                environment_label=(
                    "Activity Slowdown"
                ),
                activity_score=-0.30,
                confidence_score=0.70,
                conviction_score=0.50,
            ),
            make_snapshot(
                as_of_date=date(2025, 5, 31),
                environment_label=(
                    "Activity Slowdown"
                ),
                activity_score=-0.40,
                confidence_score=0.80,
                conviction_score=0.60,
            ),
            make_snapshot(
                as_of_date=date(2025, 6, 30),
                environment_label=(
                    "Goldilocks Expansion"
                ),
                activity_score=0.30,
                confidence_score=0.85,
                conviction_score=0.55,
            ),
        ),
    )


@pytest.mark.parametrize(
    ("label", "expected"),
    (
        ("Mixed / Transitional", True),
        ("Inflationary Transition", True),
        ("Reflationary Transition", True),
        ("Goldilocks Expansion", False),
        ("Activity Slowdown", False),
    ),
)
def test_is_transitional_regime(
    label: str,
    expected: bool,
) -> None:
    assert is_transitional_regime(label) is expected


def test_calculate_regime_statistics() -> None:
    statistics = calculate_regime_statistics(
        make_history()
    )

    assert len(statistics) == 3

    goldilocks = next(
        result
        for result in statistics
        if result.environment_label
        == "Goldilocks Expansion"
    )

    assert goldilocks.occurrence_count == 2
    assert goldilocks.observation_count == 3
    assert goldilocks.coverage_ratio == 0.5

    assert (
        goldilocks.average_duration_observations
        == 1.5
    )
    assert (
        goldilocks.median_duration_observations
        == 1.5
    )
    assert (
        goldilocks.minimum_duration_observations
        == 1
    )
    assert (
        goldilocks.maximum_duration_observations
        == 2
    )

    assert (
        goldilocks.average_confidence_score
        == pytest.approx(
            0.85,
            abs=0.0001,
        )
    )

    assert (
        goldilocks.average_conviction_score
        == pytest.approx(
            0.6167,
            abs=0.0001,
        )
    )

    assert (
        goldilocks.average_activity_score
        == pytest.approx(
            0.40,
            abs=0.0001,
        )
    )

    assert goldilocks.current_regime is True


def test_statistics_are_ordered_by_coverage() -> None:
    statistics = calculate_regime_statistics(
        make_history()
    )

    assert statistics[0].environment_label == (
        "Goldilocks Expansion"
    )

    assert statistics[0].observation_count == 3


def test_build_environment_validation_summary() -> None:
    summary = build_environment_validation_summary(
        make_history()
    )

    assert summary.economy == "USA"

    assert summary.start_date == date(
        2025,
        1,
        31,
    )

    assert summary.end_date == date(
        2025,
        6,
        30,
    )

    assert summary.observation_count == 6
    assert summary.regime_period_count == 4
    assert summary.unique_regime_count == 3

    assert summary.most_common_regime == (
        "Goldilocks Expansion"
    )

    assert summary.most_persistent_regime in {
        "Activity Slowdown",
        "Goldilocks Expansion",
    }

    assert summary.current_regime == (
        "Goldilocks Expansion"
    )

    assert (
        summary.transitional_observation_count
        == 1
    )

    assert (
        summary.transitional_coverage_ratio
        == pytest.approx(
            1 / 6,
            abs=0.0001,
        )
    )

    assert (
        summary.average_confidence_score
        == pytest.approx(
            0.775,
            abs=0.0001,
        )
    )


def test_single_observation_regime_has_zero_deviation() -> None:
    history = MacroEnvironmentHistory(
        economy="USA",
        snapshots=(
            make_snapshot(
                as_of_date=date(2025, 1, 31),
                environment_label=(
                    "Mixed / Transitional"
                ),
            ),
        ),
    )

    statistics = calculate_regime_statistics(
        history
    )

    result = statistics[0]

    assert (
        result.confidence_standard_deviation
        == 0.0
    )

    assert (
        result.conviction_standard_deviation
        == 0.0
    )


def test_coverage_ratios_sum_to_one() -> None:
    statistics = calculate_regime_statistics(
        make_history()
    )

    total_coverage = sum(
        result.coverage_ratio
        for result in statistics
    )

    assert total_coverage == pytest.approx(
        1.0,
        abs=0.0001,
    )