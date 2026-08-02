from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from macro_engine.historical.episodes import build_environment_episodes
from macro_engine.historical.explorer import (
    EnvironmentExplorerResult,
    build_environment_explorer_result,
)


@dataclass(frozen=True)
class AssetExplorerConfig:
    file_path: str
    outcome_name: str
    outcome_unit: str


@dataclass(frozen=True)
class CrossAssetExplorerResult:
    environment: str
    results_by_asset: dict[str, EnvironmentExplorerResult]
    asset_configs: dict[str, AssetExplorerConfig]


DEFAULT_ASSET_CONFIGS: dict[str, AssetExplorerConfig] = {
    "S&P 500": AssetExplorerConfig(
        file_path="sp500/sp500_environment_history.csv",
        outcome_name="Forward return",
        outcome_unit="percent",
    ),
    "US 10Y": AssetExplorerConfig(
        file_path="us10y/us10y_environment_history.csv",
        outcome_name="Yield change",
        outcome_unit="basis_points",
    ),
    "Gold": AssetExplorerConfig(
        file_path="gold/gold_environment_history.csv",
        outcome_name="Forward return",
        outcome_unit="percent",
    ),
    "WTI": AssetExplorerConfig(
        file_path="wti/wti_environment_history.csv",
        outcome_name="Forward return",
        outcome_unit="percent",
    ),
    "DXY": AssetExplorerConfig(
        file_path="dxy/dxy_environment_history.csv",
        outcome_name="Forward return",
        outcome_unit="percent",
    ),
}


def build_cross_asset_explorer(
    environment: str,
    base_directory: str | Path = "research_outputs/cross_asset",
    asset_configs: dict[str, AssetExplorerConfig] | None = None,
) -> CrossAssetExplorerResult:
    """
    Build episode-level explorer results for one environment across assets.
    """
    base_path = Path(base_directory)
    configs = asset_configs or DEFAULT_ASSET_CONFIGS

    results: dict[str, EnvironmentExplorerResult] = {}

    for asset_name, config in configs.items():
        file_path = base_path / config.file_path

        if not file_path.exists():
            raise FileNotFoundError(
                f"Environment history file not found for "
                f"{asset_name}: {file_path}"
            )

        history = pd.read_csv(file_path)
        episodes = build_environment_episodes(history)

        results[asset_name] = build_environment_explorer_result(
            episodes=episodes,
            environment=environment,
        )

    return CrossAssetExplorerResult(
        environment=environment,
        results_by_asset=results,
        asset_configs=configs,
    )


def cross_asset_summary_to_frame(
    result: CrossAssetExplorerResult,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []

    for asset_name, explorer_result in result.results_by_asset.items():
        config = result.asset_configs[asset_name]

        for horizon, statistics in explorer_result.horizon_statistics.items():
            records.append(
                {
                    "environment": result.environment,
                    "asset": asset_name,
                    "outcome_name": config.outcome_name,
                    "outcome_unit": config.outcome_unit,
                    "horizon_months": horizon,
                    "episode_count": explorer_result.episode_count,
                    "average_duration_months": (
                        explorer_result.average_duration_months
                    ),
                    "observation_count": statistics.observation_count,
                    "average": statistics.average,
                    "median": statistics.median,
                    "positive_rate": statistics.positive_rate,
                    "best": statistics.best,
                    "worst": statistics.worst,
                }
            )

    return pd.DataFrame(records)


def format_outcome(
    value: float | None,
    outcome_unit: str,
) -> str:
    """Format an outcome according to its asset-specific unit."""
    if value is None or pd.isna(value):
        return "N/A"

    if outcome_unit == "percent":
        return f"{value:+.2%}"

    if outcome_unit == "basis_points":
        return f"{value:+.1f} bp"

    return f"{value:+.2f}"
    
def cross_asset_episodes_to_frame(
    result: CrossAssetExplorerResult,
) -> pd.DataFrame:
    """
    Combine matching environment episodes across all assets.

    Each row represents one distinct macro-environment episode. Asset outcomes
    are joined using the episode start and end months.
    """
    if not result.results_by_asset:
        return pd.DataFrame()

    asset_items = list(result.results_by_asset.items())
    first_asset_name, first_asset_result = asset_items[0]

    records: dict[tuple[str, str], dict[str, object]] = {}

    for episode in first_asset_result.episodes:
        episode_key = (
            episode.start_month,
            episode.end_month,
        )

        records[episode_key] = {
            "environment": episode.environment,
            "start_month": episode.start_month,
            "end_month": episode.end_month,
            "duration_months": episode.duration_months,
            "previous_environment": episode.previous_environment,
            "next_environment": episode.next_environment,
            "entry_confidence": episode.entry_confidence,
            "entry_conviction": episode.entry_conviction,
            "entry_activity_score": episode.entry_activity_score,
            "entry_inflation_score": episode.entry_inflation_score,
            "entry_financial_score": episode.entry_financial_score,
        }

    for asset_name, explorer_result in asset_items:
        config = result.asset_configs[asset_name]

        asset_episode_keys = {
            (episode.start_month, episode.end_month)
            for episode in explorer_result.episodes
        }

        expected_keys = set(records)

        if asset_episode_keys != expected_keys:
            missing = expected_keys.difference(asset_episode_keys)
            extra = asset_episode_keys.difference(expected_keys)

            raise ValueError(
                f"Episode mismatch for {asset_name}. "
                f"Missing episodes: {sorted(missing)}. "
                f"Unexpected episodes: {sorted(extra)}."
            )

        normalized_asset_name = (
            asset_name.lower()
            .replace("&", "and")
            .replace(" ", "_")
            .replace("/", "_")
        )

        for episode in explorer_result.episodes:
            episode_key = (
                episode.start_month,
                episode.end_month,
            )

            record = records[episode_key]

            for horizon, outcome in episode.forward_outcomes.items():
                record[
                    f"{normalized_asset_name}_{horizon}m"
                ] = outcome

            record[
                f"{normalized_asset_name}_outcome_unit"
            ] = config.outcome_unit

    episode_frame = pd.DataFrame(records.values())

    return episode_frame.sort_values(
        "start_month"
    ).reset_index(drop=True)
    
def format_cross_asset_episode_frame(
    frame: pd.DataFrame,
    result: CrossAssetExplorerResult,
    horizons: tuple[int, ...] = (1, 3, 6),
) -> pd.DataFrame:
    """
    Create a human-readable cross-asset episode table.
    """
    display = frame[
        [
            "start_month",
            "end_month",
            "duration_months",
            "previous_environment",
            "next_environment",
        ]
    ].copy()

    display = display.rename(
        columns={
            "start_month": "Entry",
            "end_month": "End",
            "duration_months": "Duration",
            "previous_environment": "Previous",
            "next_environment": "Next",
        }
    )

    for asset_name, config in result.asset_configs.items():
        normalized_asset_name = (
            asset_name.lower()
            .replace("&", "and")
            .replace(" ", "_")
            .replace("/", "_")
        )

        for horizon in horizons:
            source_column = (
                f"{normalized_asset_name}_{horizon}m"
            )

            if source_column not in frame.columns:
                continue

            display_column = f"{asset_name} {horizon}M"

            display[display_column] = frame[source_column].map(
                lambda value, unit=config.outcome_unit: format_outcome(
                    value,
                    unit,
                )
            )

    return display