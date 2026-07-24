"""Tests for historical regime-transition validation."""

from datetime import date

import pytest

from macro_engine.engine.validation_engine import (
    build_regime_transition_summary,
    calculate_regime_exit_statistics,
    calculate_transition_statistics,
)
from macro_engine.models.environment import (
    MacroEnvironmentHistory,
    MacroEnvironmentSnapshot,
)


def make_snapshot(
    *,
    as_of_date: date,
    environment_label: str,
    activity_score: float,
    inflation_score: float = 0.0,
    financial_score: float = 0.0,
    confidence_score: float = 0.80,
    conviction_score: float = 0.60,
) -> MacroEnvironmentSnapshot:
    return MacroEnvironmentSnapshot(
        economy="USA",
        as_of_date=as_of_date,
        activity_score=activity_score,
        activity_label="Stable",
        inflation_impulse_score=inflation_score,
        inflation_impulse_label="Stable",
        financial_impulse_score=financial_score,
        financial_impulse_label="Neutral",
        environment_label=environment_label,
        confidence_score=confidence_score,
        environment_conviction_score=(
            conviction_score
        ),
        environment_conviction_label="Moderate",
    )


def make_transition_history() -> MacroEnvironmentHistory:
    """
    Regime periods:

    Goldilocks: Jan-Feb
    Slowdown: Mar-Apr
    Goldilocks: May
    Reflation: Jun-Jul
    Slowdown: Aug

    Completed transitions:

    Goldilocks -> Slowdown
    Slowdown -> Goldilocks
    Goldilocks -> Reflation
    Reflation -> Slowdown
    """

    return MacroEnvironmentHistory(
        economy="USA",
        snapshots=(
            make_snapshot(
                as_of_date=date(2025, 1, 31),
                environment_label="Goldilocks",
                activity_score=0.40,
            ),
            make_snapshot(
                as_of_date=date(2025, 2, 28),
                environment_label="Goldilocks",
                activity_score=0.30,
                confidence_score=0.90,
                conviction_score=0.70,
            ),
            make_snapshot(
                as_of_date=date(2025, 3, 31),
                environment_label="Slowdown",
                activity_score=-0.20,
            ),
            make_snapshot(
                as_of_date=date(2025, 4, 30),
                environment_label="Slowdown",
                activity_score=-0.30,
                confidence_score=0.70,
                conviction_score=0.40,
            ),
            make_snapshot(
                as_of_date=date(2025, 5, 31),
                environment_label="Goldilocks",
                activity_score=0.20,
                confidence_score=0.80,
                conviction_score=0.50,
            ),
            make_snapshot(
                as_of_date=date(2025, 6, 30),
                environment_label="Reflation",
                activity_score=0.40,
            ),
            make_snapshot(
                as_of_date=date(2025, 7, 31),
                environment_label="Reflation",
                activity_score=0.50,
                confidence_score=0.85,
                conviction_score=0.65,
            ),
            make_snapshot(
                as_of_date=date(2025, 8, 31),
                environment_label="Slowdown",
                activity_score=-0.40,
            ),
        ),
    )


def test_calculate_transition_statistics() -> None:
    statistics = calculate_transition_statistics(
        make_transition_history()
    )

    assert len(statistics) == 4

    goldilocks_to_slowdown = next(
        result
        for result in statistics
        if (
            result.from_environment_label
            == "Goldilocks"
            and result.to_environment_label
            == "Slowdown"
        )
    )

    assert goldilocks_to_slowdown.transition_count == 1
    assert goldilocks_to_slowdown.source_exit_count == 2

    assert (
        goldilocks_to_slowdown.transition_probability
        == 0.5
    )

    assert (
        goldilocks_to_slowdown.first_transition_date
        == date(2025, 3, 31)
    )

    assert (
        goldilocks_to_slowdown
        .average_source_duration_observations
        == 2.0
    )

    assert (
        goldilocks_to_slowdown
        .average_source_confidence_score
        == 0.9
    )

    assert (
        goldilocks_to_slowdown
        .average_source_conviction_score
        == 0.7
    )

    assert (
        goldilocks_to_slowdown
        .average_pre_transition_activity_score
        == 0.3
    )


def test_source_transition_probabilities_sum_to_one() -> None:
    statistics = calculate_transition_statistics(
        make_transition_history()
    )

    goldilocks_probability = sum(
        result.transition_probability
        for result in statistics
        if result.from_environment_label
        == "Goldilocks"
    )

    assert goldilocks_probability == pytest.approx(
        1.0,
        abs=0.0001,
    )


def test_current_period_has_no_imagined_exit() -> None:
    statistics = calculate_transition_statistics(
        make_transition_history()
    )

    slowdown_exits = [
        result
        for result in statistics
        if result.from_environment_label
        == "Slowdown"
    ]

    assert len(slowdown_exits) == 1

    assert (
        slowdown_exits[0].to_environment_label
        == "Goldilocks"
    )

    assert slowdown_exits[0].source_exit_count == 1


def test_calculate_regime_exit_statistics() -> None:
    statistics = calculate_regime_exit_statistics(
        make_transition_history()
    )

    goldilocks = next(
        result
        for result in statistics
        if result.environment_label == "Goldilocks"
    )

    assert goldilocks.completed_exit_count == 2
    assert goldilocks.destination_count == 2

    assert goldilocks.most_common_next_regime in {
        "Reflation",
        "Slowdown",
    }

    assert (
        goldilocks
        .most_common_transition_probability
        == 0.5
    )

    assert (
        goldilocks
        .average_duration_before_exit_observations
        == 1.5
    )

    assert goldilocks.current_regime is False


def test_current_regime_can_have_historical_exits() -> None:
    statistics = calculate_regime_exit_statistics(
        make_transition_history()
    )

    slowdown = next(
        result
        for result in statistics
        if result.environment_label == "Slowdown"
    )

    assert slowdown.current_regime is True
    assert slowdown.completed_exit_count == 1
    assert slowdown.most_common_next_regime == (
        "Goldilocks"
    )


def test_build_regime_transition_summary() -> None:
    summary = build_regime_transition_summary(
        make_transition_history()
    )

    assert summary.economy == "USA"
    assert summary.regime_period_count == 5
    assert summary.completed_transition_count == 4
    assert summary.unique_transition_count == 4
    assert summary.source_regime_count == 3
    assert summary.most_common_transition_count == 1

    assert " -> " in summary.most_common_transition


def test_single_regime_history_has_no_statistics() -> None:
    history = MacroEnvironmentHistory(
        economy="USA",
        snapshots=(
            make_snapshot(
                as_of_date=date(2025, 1, 31),
                environment_label="Goldilocks",
                activity_score=0.40,
            ),
            make_snapshot(
                as_of_date=date(2025, 2, 28),
                environment_label="Goldilocks",
                activity_score=0.30,
            ),
        ),
    )

    assert calculate_transition_statistics(history) == ()
    assert calculate_regime_exit_statistics(history) == ()

    with pytest.raises(
        ValueError,
        match="at least two regime periods",
    ):
        build_regime_transition_summary(history)