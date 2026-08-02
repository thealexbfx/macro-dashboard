from __future__ import annotations

import re
from collections.abc import Iterable

import pandas as pd

from macro_engine.models.historical import EnvironmentEpisode


_REQUIRED_COLUMNS = {
    "month",
    "us_environment",
}


def _optional_float(value: object) -> float | None:
    if pd.isna(value):
        return None
    return float(value)


def _optional_string(value: object) -> str | None:
    if pd.isna(value):
        return None

    text = str(value).strip()
    return text or None


def _parse_flags(value: object) -> tuple[str, ...]:
    if pd.isna(value):
        return ()

    return tuple(
        flag.strip()
        for flag in str(value).split("|")
        if flag.strip()
    )


def _find_forward_outcome_columns(
    columns: Iterable[str],
) -> dict[int, str]:
    pattern = re.compile(r"^forward_outcome_(\d+)m$")
    outcome_columns: dict[int, str] = {}

    for column in columns:
        match = pattern.match(column)
        if match:
            outcome_columns[int(match.group(1))] = column

    return outcome_columns


def _validate_history(history: pd.DataFrame) -> None:
    missing = _REQUIRED_COLUMNS.difference(history.columns)

    if missing:
        raise ValueError(
            "History is missing required columns: "
            + ", ".join(sorted(missing))
        )

    if history.empty:
        raise ValueError("History cannot be empty.")


def build_environment_episodes(
    history: pd.DataFrame,
) -> list[EnvironmentEpisode]:
    """
    Convert monthly environment history into consecutive regime episodes.

    Each episode uses the first month as its entry observation. Forward asset
    outcomes, confidence, conviction, scores and flags therefore represent the
    environment at entry rather than averages across the whole episode.
    """
    _validate_history(history)

    data = history.copy()
    data["month"] = pd.to_datetime(data["month"], format="%Y-%m")
    data = data.sort_values("month").reset_index(drop=True)

    outcome_columns = _find_forward_outcome_columns(data.columns)

    environment_changed = (
        data["us_environment"]
        .ne(data["us_environment"].shift(1))
    )

    data["_episode_id"] = environment_changed.cumsum()

    grouped = list(data.groupby("_episode_id", sort=True))
    episodes: list[EnvironmentEpisode] = []

    for group_position, (_, episode_rows) in enumerate(grouped):
        episode_rows = episode_rows.sort_values("month")

        entry = episode_rows.iloc[0]
        final = episode_rows.iloc[-1]

        previous_environment = (
            _optional_string(data.loc[episode_rows.index[0] - 1, "us_environment"])
            if episode_rows.index[0] > 0
            else _optional_string(entry.get("us_previous_environment"))
        )

        next_environment: str | None = None

        if group_position + 1 < len(grouped):
            next_episode_rows = grouped[group_position + 1][1]
            next_environment = _optional_string(
                next_episode_rows.iloc[0]["us_environment"]
            )

        forward_outcomes = {
            horizon: _optional_float(entry[column])
            for horizon, column in outcome_columns.items()
        }

        episodes.append(
            EnvironmentEpisode(
                environment=str(entry["us_environment"]),
                start_month=entry["month"].strftime("%Y-%m"),
                end_month=final["month"].strftime("%Y-%m"),
                duration_months=len(episode_rows),
                previous_environment=previous_environment,
                next_environment=next_environment,
                entry_confidence=_optional_float(
                    entry.get("us_confidence")
                ),
                entry_conviction=_optional_float(
                    entry.get("us_conviction")
                ),
                entry_conviction_label=_optional_string(
                    entry.get("us_conviction_label")
                ),
                entry_activity_score=_optional_float(
                    entry.get("us_activity_score")
                ),
                entry_activity_label=_optional_string(
                    entry.get("us_activity_label")
                ),
                entry_inflation_score=_optional_float(
                    entry.get("us_inflation_score")
                ),
                entry_inflation_label=_optional_string(
                    entry.get("us_inflation_label")
                ),
                entry_financial_score=_optional_float(
                    entry.get("us_financial_score")
                ),
                entry_financial_label=_optional_string(
                    entry.get("us_financial_label")
                ),
                entry_asset_close=_optional_float(
                    entry.get("asset_close")
                ),
                forward_outcomes=forward_outcomes,
                entry_flags=_parse_flags(entry.get("us_flags")),
            )
        )

    return episodes


def episodes_to_frame(
    episodes: Iterable[EnvironmentEpisode],
) -> pd.DataFrame:
    """Convert environment episodes into a flat DataFrame."""
    return pd.DataFrame(
        episode.to_record()
        for episode in episodes
    )


def filter_environment_episodes(
    episodes: Iterable[EnvironmentEpisode],
    environment: str,
) -> list[EnvironmentEpisode]:
    """Return episodes matching one environment name."""
    normalized_environment = environment.strip().casefold()

    return [
        episode
        for episode in episodes
        if episode.environment.strip().casefold()
        == normalized_environment
    ]