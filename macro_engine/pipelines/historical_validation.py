from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable

import pandas as pd

from data.yahoo import get_fx_data_yahoo
from macro_engine.pipelines.history import (
    HistoricalEnvironmentRun,
    run_euro_environment_history,
    run_japan_environment_history,
    run_uk_environment_history,
    run_usa_environment_history,
)


HistoryRunner = Callable[..., HistoricalEnvironmentRun]

RESEARCH_OUTPUTS_DIR = Path("research_outputs")
DEFAULT_MONTHS_TO_ANALYZE = 60
FORWARD_HORIZONS = (1, 3, 6)


@dataclass(frozen=True)
class FXHistoricalValidationConfig:
    asset_key: str
    display_name: str
    ticker: str

    primary_prefix: str
    primary_display_name: str
    primary_history_runner: HistoryRunner

    secondary_prefix: str
    secondary_display_name: str
    secondary_history_runner: HistoryRunner


@dataclass(frozen=True)
class HistoricalValidationOutputs:
    history_path: Path
    primary_report_path: Path
    secondary_report_path: Path
    pair_report_path: Path


FX_VALIDATION_CONFIGS: dict[
    str,
    FXHistoricalValidationConfig,
] = {
    "gbpusd": FXHistoricalValidationConfig(
        asset_key="gbpusd",
        display_name="GBP/USD",
        ticker="GBPUSD=X",
        primary_prefix="us",
        primary_display_name="US",
        primary_history_runner=run_usa_environment_history,
        secondary_prefix="uk",
        secondary_display_name="UK",
        secondary_history_runner=run_uk_environment_history,
    ),
    "eurusd": FXHistoricalValidationConfig(
        asset_key="eurusd",
        display_name="EUR/USD",
        ticker="EURUSD=X",
        primary_prefix="us",
        primary_display_name="US",
        primary_history_runner=run_usa_environment_history,
        secondary_prefix="euro",
        secondary_display_name="Euro Area",
        secondary_history_runner=run_euro_environment_history,
    ),
    
    "usdjpy": FXHistoricalValidationConfig(
        asset_key="usdjpy",
        display_name="USD/JPY",
        ticker="USDJPY=X",
        primary_prefix="us",
        primary_display_name="US",
        primary_history_runner=run_usa_environment_history,
        secondary_prefix="japan",
        secondary_display_name="Japan",
        secondary_history_runner=run_japan_environment_history,
    ),
}


def get_validation_config(
    asset_key: str,
) -> FXHistoricalValidationConfig:
    try:
        return FX_VALIDATION_CONFIGS[asset_key]
    except KeyError as exc:
        available = ", ".join(FX_VALIDATION_CONFIGS)

        raise ValueError(
            f"No FX historical-validation configuration exists for "
            f"{asset_key}. Available assets: {available}"
        ) from exc


def _history_to_dataframe(
    history_run: HistoricalEnvironmentRun,
    prefix: str,
) -> pd.DataFrame:
    if history_run.history is None:
        raise RuntimeError(
            f"{prefix} history returned no successful observations."
        )

    rows: list[dict[str, object]] = []

    for snapshot in history_run.history.snapshots:
        rows.append(
            {
                "date": pd.Timestamp(snapshot.as_of_date),
                f"{prefix}_environment": snapshot.environment_label,
                f"{prefix}_confidence": snapshot.confidence_score,
                f"{prefix}_conviction": (
                    snapshot.environment_conviction_score
                ),
            }
        )

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        raise RuntimeError(
            f"{prefix} environment history is empty."
        )

    dataframe["month"] = dataframe["date"].dt.to_period("M")

    return (
        dataframe
        .sort_values("date")
        .drop_duplicates("month", keep="last")
        .drop(columns="date")
        .reset_index(drop=True)
    )


def _build_monthly_price_data(
    *,
    ticker: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    daily = get_fx_data_yahoo(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
    )

    if daily.empty:
        raise RuntimeError(
            f"Yahoo Finance returned no data for {ticker}."
        )

    daily = daily.copy()
    daily["date"] = pd.to_datetime(daily["date"])
    daily["month"] = daily["date"].dt.to_period("M")

    return (
        daily
        .sort_values("date")
        .groupby("month", as_index=False)
        .agg(asset_close=("value", "last"))
    )


def _add_forward_returns(
    data: pd.DataFrame,
) -> pd.DataFrame:
    result = data.copy()

    for horizon in FORWARD_HORIZONS:
        result[f"forward_return_{horizon}m"] = (
            result["asset_close"].shift(-horizon)
            / result["asset_close"]
            - 1.0
        )

    return result


def _summarize_environment(
    *,
    data: pd.DataFrame,
    group_columns: list[str],
    environment_type: str,
    confidence_columns: list[str],
    conviction_columns: list[str],
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    grouped = data.groupby(
        group_columns,
        observed=True,
        dropna=False,
    )

    for group_values, group in grouped:
        if not isinstance(group_values, tuple):
            group_values = (group_values,)

        row: dict[str, object] = {
            "environment_type": environment_type,
        }

        for column, value in zip(
            group_columns,
            group_values,
        ):
            row[column] = value

        for horizon in FORWARD_HORIZONS:
            returns = group[
                f"forward_return_{horizon}m"
            ].dropna()

            observations = len(returns)

            row[f"observations_{horizon}m"] = observations
            row[f"average_return_{horizon}m"] = (
                returns.mean()
                if observations
                else float("nan")
            )
            row[f"median_return_{horizon}m"] = (
                returns.median()
                if observations
                else float("nan")
            )
            row[f"up_rate_{horizon}m"] = (
                (returns > 0).mean()
                if observations
                else float("nan")
            )
            row[f"down_rate_{horizon}m"] = (
                (returns < 0).mean()
                if observations
                else float("nan")
            )
            row[f"best_return_{horizon}m"] = (
                returns.max()
                if observations
                else float("nan")
            )
            row[f"worst_return_{horizon}m"] = (
                returns.min()
                if observations
                else float("nan")
            )

        available_confidence = [
            column
            for column in confidence_columns
            if column in group.columns
        ]

        available_conviction = [
            column
            for column in conviction_columns
            if column in group.columns
        ]

        row["average_confidence"] = (
            group[available_confidence]
            .mean(axis=1)
            .mean()
            if available_confidence
            else float("nan")
        )

        row["average_conviction"] = (
            group[available_conviction]
            .mean(axis=1)
            .mean()
            if available_conviction
            else float("nan")
        )

        rows.append(row)

    report = pd.DataFrame(rows)

    if report.empty:
        return report

    return (
        report
        .sort_values(
            [
                "observations_3m",
                "average_return_3m",
            ],
            ascending=[False, False],
        )
        .reset_index(drop=True)
    )


def run_fx_historical_validation(
    asset_key: str,
    *,
    months_to_analyze: int = DEFAULT_MONTHS_TO_ANALYZE,
    end_date: date | None = None,
) -> HistoricalValidationOutputs:
    config = get_validation_config(asset_key)

    resolved_end_date = end_date or date.today()

    start_date = (
        pd.Timestamp(resolved_end_date)
        - pd.DateOffset(months=months_to_analyze + 6)
    ).date()

    print(
        f"Running {config.primary_display_name} "
        "environment history..."
    )

    primary_run = config.primary_history_runner(
        start_date=start_date,
        end_date=resolved_end_date,
        frequency="monthly",
        continue_on_error=True,
    )

    print(
        f"Running {config.secondary_display_name} "
        "environment history..."
    )

    secondary_run = config.secondary_history_runner(
        start_date=start_date,
        end_date=resolved_end_date,
        frequency="monthly",
        continue_on_error=True,
    )

    print(f"Downloading {config.display_name}...")

    primary = _history_to_dataframe(
        primary_run,
        prefix=config.primary_prefix,
    )

    secondary = _history_to_dataframe(
        secondary_run,
        prefix=config.secondary_prefix,
    )

    monthly_price = _build_monthly_price_data(
        ticker=config.ticker,
        start_date=start_date,
        end_date=resolved_end_date,
    )

    primary_environment_column = (
        f"{config.primary_prefix}_environment"
    )
    secondary_environment_column = (
        f"{config.secondary_prefix}_environment"
    )

    primary_confidence_column = (
        f"{config.primary_prefix}_confidence"
    )
    secondary_confidence_column = (
        f"{config.secondary_prefix}_confidence"
    )

    primary_conviction_column = (
        f"{config.primary_prefix}_conviction"
    )
    secondary_conviction_column = (
        f"{config.secondary_prefix}_conviction"
    )

    research = (
        primary
        .merge(
            secondary,
            on="month",
            how="inner",
        )
        .merge(
            monthly_price,
            on="month",
            how="inner",
        )
        .sort_values("month")
        .tail(months_to_analyze)
        .reset_index(drop=True)
    )

    if research.empty:
        raise RuntimeError(
            f"No matched historical observations were available for "
            f"{config.display_name}."
        )

    research = _add_forward_returns(research)

    research["environment_pair"] = (
        research[primary_environment_column]
        + " | "
        + research[secondary_environment_column]
    )

    confidence_columns = [
        primary_confidence_column,
        secondary_confidence_column,
    ]

    conviction_columns = [
        primary_conviction_column,
        secondary_conviction_column,
    ]

    primary_report = _summarize_environment(
        data=research,
        group_columns=[primary_environment_column],
        environment_type=(
            f"{config.primary_display_name} environment"
        ),
        confidence_columns=confidence_columns,
        conviction_columns=conviction_columns,
    )

    secondary_report = _summarize_environment(
        data=research,
        group_columns=[secondary_environment_column],
        environment_type=(
            f"{config.secondary_display_name} environment"
        ),
        confidence_columns=confidence_columns,
        conviction_columns=conviction_columns,
    )

    pair_report = _summarize_environment(
        data=research,
        group_columns=[
            primary_environment_column,
            secondary_environment_column,
        ],
        environment_type=(
            f"{config.primary_display_name}–"
            f"{config.secondary_display_name} environment pair"
        ),
        confidence_columns=confidence_columns,
        conviction_columns=conviction_columns,
    )

    RESEARCH_OUTPUTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    history_path = (
        RESEARCH_OUTPUTS_DIR
        / f"{asset_key}_environment_history.csv"
    )

    primary_report_path = (
        RESEARCH_OUTPUTS_DIR
        / f"{asset_key}_primary_environment_report.csv"
    )

    secondary_report_path = (
        RESEARCH_OUTPUTS_DIR
        / f"{asset_key}_secondary_environment_report.csv"
    )

    pair_report_path = (
        RESEARCH_OUTPUTS_DIR
        / f"{asset_key}_environment_pair_report.csv"
    )

    research_output = research.copy()
    research_output["month"] = (
        research_output["month"].astype(str)
    )

    research_output.to_csv(
        history_path,
        index=False,
    )

    primary_report.to_csv(
        primary_report_path,
        index=False,
    )

    secondary_report.to_csv(
        secondary_report_path,
        index=False,
    )

    pair_report.to_csv(
        pair_report_path,
        index=False,
    )

    print()
    print(f"{config.display_name} validation complete.")
    print(f"Matched observations: {len(research)}")
    print(f"First month: {research['month'].iloc[0]}")
    print(f"Last month: {research['month'].iloc[-1]}")
    print()
    print("Saved:")
    print(f"  {history_path}")
    print(f"  {primary_report_path}")
    print(f"  {secondary_report_path}")
    print(f"  {pair_report_path}")

    return HistoricalValidationOutputs(
        history_path=history_path,
        primary_report_path=primary_report_path,
        secondary_report_path=secondary_report_path,
        pair_report_path=pair_report_path,
    )