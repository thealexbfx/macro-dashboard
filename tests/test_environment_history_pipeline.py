"""Tests for historical environment pipeline runners."""

from datetime import date

import pytest

from macro_engine.models.environment import (
    MacroEnvironmentResult,
    MacroEnvironmentSnapshot,
)
from macro_engine.pipelines.history import (
    HistoricalEnvironmentRun,
    generate_history_dates,
    run_environment_history,
)


def make_result(
    as_of_date: date,
    economy: str = "USA",
) -> MacroEnvironmentResult:
    """
    Create a lightweight environment result without running live data APIs.

    The object is created without dataclass validation because these tests
    focus specifically on historical orchestration and snapshot conversion.
    """

    result = object.__new__(MacroEnvironmentResult)

    object.__setattr__(result, "economy", economy)
    object.__setattr__(result, "as_of_date", as_of_date)

    object.__setattr__(result, "activity_score", 0.25)
    object.__setattr__(result, "activity_label", "Expanding")

    object.__setattr__(
        result,
        "inflation_impulse_score",
        -0.20,
    )
    object.__setattr__(
        result,
        "inflation_impulse_label",
        "Easing",
    )

    object.__setattr__(
        result,
        "financial_impulse_score",
        0.30,
    )
    object.__setattr__(
        result,
        "financial_impulse_label",
        "Supportive",
    )

    object.__setattr__(
        result,
        "environment_label",
        "Goldilocks Expansion",
    )

    object.__setattr__(
        result,
        "confidence_score",
        0.80,
    )
    object.__setattr__(
        result,
        "environment_conviction_score",
        0.65,
    )
    object.__setattr__(
        result,
        "environment_conviction_label",
        "Moderate",
    )

    object.__setattr__(
        result,
        "flags",
        (),
    )

    return result


def test_generate_monthly_history_dates() -> None:
    dates = generate_history_dates(
        start_date=date(2026, 1, 10),
        end_date=date(2026, 3, 15),
        frequency="monthly",
    )

    assert dates == (
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 15),
    )


def test_generate_quarterly_history_dates() -> None:
    dates = generate_history_dates(
        start_date=date(2025, 1, 1),
        end_date=date(2025, 10, 15),
        frequency="quarterly",
    )

    assert dates == (
        date(2025, 3, 31),
        date(2025, 6, 30),
        date(2025, 9, 30),
        date(2025, 10, 15),
    )


def test_generate_history_dates_rejects_invalid_range() -> None:
    with pytest.raises(
        ValueError,
        match="end_date must not be before start_date",
    ):
        generate_history_dates(
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
        )


def test_run_environment_history_builds_ordered_history() -> None:
    requested_dates: list[date] = []

    def runner(
        as_of_date: date | None = None,
    ) -> MacroEnvironmentResult:
        assert as_of_date is not None

        requested_dates.append(as_of_date)

        return make_result(as_of_date)

    run = run_environment_history(
        economy="USA",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        environment_runner=runner,
        frequency="monthly",
    )

    assert isinstance(
        run,
        HistoricalEnvironmentRun,
    )

    assert run.history is not None
    assert run.success_count == 3
    assert run.failure_count == 0
    assert run.success_rate == 1.0
    assert run.is_complete is True

    assert requested_dates == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
    ]

    assert run.history.observation_count == 3
    assert run.history.earliest.as_of_date == date(
        2026,
        1,
        31,
    )
    assert run.history.latest.as_of_date == date(
        2026,
        3,
        31,
    )

    assert isinstance(
        run.history.latest,
        MacroEnvironmentSnapshot,
    )


def test_run_environment_history_records_failures() -> None:
    failing_date = date(2026, 2, 28)

    def runner(
        as_of_date: date | None = None,
    ) -> MacroEnvironmentResult:
        assert as_of_date is not None

        if as_of_date == failing_date:
            raise ValueError(
                "insufficient historical data"
            )

        return make_result(as_of_date)

    run = run_environment_history(
        economy="USA",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        environment_runner=runner,
        frequency="monthly",
        continue_on_error=True,
    )

    assert run.history is not None
    assert run.success_count == 2
    assert run.failure_count == 1
    assert run.success_rate == pytest.approx(
        2 / 3,
        abs=0.0001,
    )
    assert run.is_complete is False

    failure = run.failures[0]

    assert failure.as_of_date == failing_date
    assert failure.error_type == "ValueError"
    assert failure.message == (
        "insufficient historical data"
    )


def test_run_environment_history_can_raise_immediately() -> None:
    def runner(
        as_of_date: date | None = None,
    ) -> MacroEnvironmentResult:
        raise RuntimeError(
            "historical calculation failed"
        )

    with pytest.raises(
        RuntimeError,
        match="historical calculation failed",
    ):
        run_environment_history(
            economy="USA",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            environment_runner=runner,
            continue_on_error=False,
        )


def test_run_environment_history_rejects_wrong_result_date() -> None:
    def runner(
        as_of_date: date | None = None,
    ) -> MacroEnvironmentResult:
        return make_result(
            date(2020, 1, 1)
        )

    run = run_environment_history(
        economy="USA",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        environment_runner=runner,
        continue_on_error=True,
    )

    assert run.history is None
    assert run.success_count == 0
    assert run.failure_count == 1
    assert run.failures[0].error_type == "ValueError"
    assert "date does not match" in (
        run.failures[0].message
    )