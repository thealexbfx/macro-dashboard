from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from macro_engine.models.historical import EnvironmentEpisode


@dataclass(frozen=True)
class HorizonStatistics:
    horizon_months: int
    observation_count: int

    average: float | None
    median: float | None
    positive_rate: float | None

    best: float | None
    worst: float | None


@dataclass(frozen=True)
class EnvironmentExplorerResult:
    environment: str
    episode_count: int

    average_duration_months: float | None
    median_duration_months: float | None
    longest_duration_months: int | None
    shortest_duration_months: int | None

    horizon_statistics: dict[int, HorizonStatistics]

    episodes: tuple[EnvironmentEpisode, ...]


def _build_horizon_statistics(
    episodes: Iterable[EnvironmentEpisode],
    horizon_months: int,
) -> HorizonStatistics:
    values = [
        episode.get_forward_outcome(horizon_months)
        for episode in episodes
    ]

    valid_values = pd.Series(
        [value for value in values if value is not None],
        dtype="float64",
    ).dropna()

    if valid_values.empty:
        return HorizonStatistics(
            horizon_months=horizon_months,
            observation_count=0,
            average=None,
            median=None,
            positive_rate=None,
            best=None,
            worst=None,
        )

    return HorizonStatistics(
        horizon_months=horizon_months,
        observation_count=len(valid_values),
        average=float(valid_values.mean()),
        median=float(valid_values.median()),
        positive_rate=float((valid_values > 0).mean()),
        best=float(valid_values.max()),
        worst=float(valid_values.min()),
    )


def build_environment_explorer_result(
    episodes: Iterable[EnvironmentEpisode],
    environment: str,
) -> EnvironmentExplorerResult:
    normalized_environment = environment.strip().casefold()

    selected = tuple(
        episode
        for episode in episodes
        if episode.environment.strip().casefold()
        == normalized_environment
    )

    if not selected:
        raise ValueError(
            f"No episodes found for environment: {environment}"
        )

    durations = pd.Series(
        [episode.duration_months for episode in selected],
        dtype="float64",
    )

    horizons = sorted(
        {
            horizon
            for episode in selected
            for horizon in episode.forward_outcomes
        }
    )

    horizon_statistics = {
        horizon: _build_horizon_statistics(selected, horizon)
        for horizon in horizons
    }

    return EnvironmentExplorerResult(
        environment=selected[0].environment,
        episode_count=len(selected),
        average_duration_months=float(durations.mean()),
        median_duration_months=float(durations.median()),
        longest_duration_months=int(durations.max()),
        shortest_duration_months=int(durations.min()),
        horizon_statistics=horizon_statistics,
        episodes=selected,
    )


def explorer_episodes_to_frame(
    result: EnvironmentExplorerResult,
) -> pd.DataFrame:
    records = [
        episode.to_record()
        for episode in result.episodes
    ]

    return pd.DataFrame(records)