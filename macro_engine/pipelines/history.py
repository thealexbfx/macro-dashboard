"""Historical macro-environment pipeline runners."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Literal

import pandas as pd

from macro_engine.engine.environment_engine import (
    create_environment_snapshot,
)
from macro_engine.models.environment import (
    MacroEnvironmentHistory,
    MacroEnvironmentResult,
    MacroEnvironmentSnapshot,
)
from macro_engine.pipelines.environment import (
    run_usa_macro_environment,
)


HistoryFrequency = Literal[
    "monthly",
    "quarterly",
    "annual",
]


@dataclass(frozen=True)
class HistoricalRunFailure:
    """A historical observation that could not be calculated."""

    as_of_date: date
    error_type: str
    message: str

    def __post_init__(self) -> None:
        if not self.error_type.strip():
            raise ValueError(
                "error_type must not be empty"
            )

        if not self.message.strip():
            raise ValueError(
                "message must not be empty"
            )


@dataclass(frozen=True)
class HistoricalEnvironmentRun:
    """
    Complete output from a historical environment calculation.

    History contains all successful snapshots.
    Failures preserve dates that could not be calculated.
    """

    requested_start_date: date
    requested_end_date: date
    frequency: HistoryFrequency

    history: MacroEnvironmentHistory | None

    attempted_dates: tuple[date, ...]
    failures: tuple[HistoricalRunFailure, ...] = field(
        default_factory=tuple
    )

    def __post_init__(self) -> None:
        if self.requested_end_date < self.requested_start_date:
            raise ValueError(
                "requested_end_date must not be before "
                "requested_start_date"
            )

        if not self.attempted_dates:
            raise ValueError(
                "attempted_dates must not be empty"
            )

        if len(set(self.attempted_dates)) != len(
            self.attempted_dates
        ):
            raise ValueError(
                "attempted_dates must be unique"
            )

        if self.attempted_dates != tuple(
            sorted(self.attempted_dates)
        ):
            raise ValueError(
                "attempted_dates must be ordered"
            )

        failure_dates = tuple(
            failure.as_of_date
            for failure in self.failures
        )

        if len(set(failure_dates)) != len(failure_dates):
            raise ValueError(
                "failure dates must be unique"
            )

        if not set(failure_dates).issubset(
            set(self.attempted_dates)
        ):
            raise ValueError(
                "failure dates must be attempted dates"
            )

    @property
    def success_count(self) -> int:
        if self.history is None:
            return 0

        return self.history.observation_count

    @property
    def failure_count(self) -> int:
        return len(self.failures)

    @property
    def attempted_count(self) -> int:
        return len(self.attempted_dates)

    @property
    def success_rate(self) -> float:
        return round(
            self.success_count / self.attempted_count,
            4,
        )

    @property
    def is_complete(self) -> bool:
        return self.failure_count == 0


def generate_history_dates(
    start_date: date,
    end_date: date,
    frequency: HistoryFrequency = "monthly",
) -> tuple[date, ...]:
    """
    Generate ordered historical observation dates.

    Monthly observations use calendar month-end dates.
    Quarterly observations use calendar quarter-end dates.
    Annual observations use calendar year-end dates.

    The final requested end date is included when it does not already
    appear in the generated schedule.
    """

    if end_date < start_date:
        raise ValueError(
            "end_date must not be before start_date"
        )

    frequency_map = {
        "monthly": "ME",
        "quarterly": "QE",
        "annual": "YE",
    }

    if frequency not in frequency_map:
        raise ValueError(
            "frequency must be monthly, quarterly, or annual"
        )

    timestamps = pd.date_range(
        start=pd.Timestamp(start_date),
        end=pd.Timestamp(end_date),
        freq=frequency_map[frequency],
    )

    generated_dates = [
        timestamp.date()
        for timestamp in timestamps
        if start_date <= timestamp.date() <= end_date
    ]

    if end_date not in generated_dates:
        generated_dates.append(end_date)

    return tuple(
        sorted(set(generated_dates))
    )


def run_environment_history(
    *,
    economy: str,
    start_date: date,
    end_date: date,
    environment_runner: Callable[
        [date | None],
        MacroEnvironmentResult,
    ],
    frequency: HistoryFrequency = "monthly",
    continue_on_error: bool = True,
) -> HistoricalEnvironmentRun:
    """
    Run an environment pipeline across historical dates.

    Successful results are converted into immutable environment snapshots.
    Failures are retained as structured diagnostics.

    When continue_on_error is False, the original exception is raised.
    """

    if not economy.strip():
        raise ValueError(
            "economy must not be empty"
        )

    attempted_dates = generate_history_dates(
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
    )

    snapshots: list[MacroEnvironmentSnapshot] = []
    failures: list[HistoricalRunFailure] = []

    for observation_date in attempted_dates:
        try:
            result = environment_runner(
                as_of_date=observation_date,
            )

            snapshot = create_environment_snapshot(
                result
            )

            if snapshot.as_of_date != observation_date:
                raise ValueError(
                    "environment result date does not match "
                    "the requested historical date"
                )

            if (
                snapshot.economy.strip().upper()
                != economy.strip().upper()
            ):
                raise ValueError(
                    "environment result economy does not match "
                    "the requested economy"
                )

            snapshots.append(snapshot)

        except Exception as exc:
            if not continue_on_error:
                raise

            failures.append(
                HistoricalRunFailure(
                    as_of_date=observation_date,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
            )

    history = None

    if snapshots:
        history = MacroEnvironmentHistory(
            economy=economy,
            snapshots=tuple(snapshots),
        )

    return HistoricalEnvironmentRun(
        requested_start_date=start_date,
        requested_end_date=end_date,
        frequency=frequency,
        history=history,
        attempted_dates=attempted_dates,
        failures=tuple(failures),
    )


def run_usa_environment_history(
    start_date: date,
    end_date: date,
    frequency: HistoryFrequency = "monthly",
    continue_on_error: bool = True,
) -> HistoricalEnvironmentRun:
    """Run the complete USA environment across historical dates."""

    return run_environment_history(
        economy="USA",
        start_date=start_date,
        end_date=end_date,
        environment_runner=run_usa_macro_environment,
        frequency=frequency,
        continue_on_error=continue_on_error,
    )