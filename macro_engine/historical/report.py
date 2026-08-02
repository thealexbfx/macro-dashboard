from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from macro_engine.historical.cross_asset import (
    CrossAssetExplorerResult,
    build_cross_asset_explorer,
    cross_asset_episodes_to_frame,
    cross_asset_summary_to_frame,
    format_cross_asset_episode_frame,
    format_outcome,
)


@dataclass(frozen=True)
class HistoricalRegimeReport:
    environment: str
    episode_count: int
    average_duration_months: float
    median_duration_months: float

    summary: pd.DataFrame
    raw_episodes: pd.DataFrame
    episode_display: pd.DataFrame


def build_historical_regime_report(
    environment: str,
    horizons: tuple[int, ...] = (1, 3, 6),
) -> HistoricalRegimeReport:
    result = build_cross_asset_explorer(environment)

    first_result = next(iter(result.results_by_asset.values()))

    summary = _build_summary_display(result)
    raw_episodes = cross_asset_episodes_to_frame(result)
    episode_display = format_cross_asset_episode_frame(
        raw_episodes,
        result,
        horizons=horizons,
    )

    return HistoricalRegimeReport(
        environment=environment,
        episode_count=first_result.episode_count,
        average_duration_months=first_result.average_duration_months,
        median_duration_months=first_result.median_duration_months,
        summary=summary,
        raw_episodes=raw_episodes,
        episode_display=episode_display,
    )


def _build_summary_display(
    result: CrossAssetExplorerResult,
) -> pd.DataFrame:
    summary = cross_asset_summary_to_frame(result)

    summary["average_display"] = summary.apply(
        lambda row: format_outcome(
            row["average"],
            row["outcome_unit"],
        ),
        axis=1,
    )

    summary["median_display"] = summary.apply(
        lambda row: format_outcome(
            row["median"],
            row["outcome_unit"],
        ),
        axis=1,
    )

    summary["best_display"] = summary.apply(
        lambda row: format_outcome(
            row["best"],
            row["outcome_unit"],
        ),
        axis=1,
    )

    summary["worst_display"] = summary.apply(
        lambda row: format_outcome(
            row["worst"],
            row["outcome_unit"],
        ),
        axis=1,
    )

    summary["frequency_display"] = summary["positive_rate"].map(
        lambda value: f"{value:.1%}"
    )

    return summary[
        [
            "asset",
            "horizon_months",
            "observation_count",
            "average_display",
            "median_display",
            "frequency_display",
            "best_display",
            "worst_display",
        ]
    ].rename(
        columns={
            "asset": "Asset",
            "horizon_months": "Horizon",
            "observation_count": "Episodes",
            "average_display": "Average",
            "median_display": "Median",
            "frequency_display": "Positive frequency",
            "best_display": "Best",
            "worst_display": "Worst",
        }
    )