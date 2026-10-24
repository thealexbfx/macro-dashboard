from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_HORIZONS = (1, 3, 6)


@dataclass(frozen=True)
class EnvironmentValidationResult:
    """
    Complete output from an environment-versus-asset validation run.
    """

    asset_name: str
    outcome_name: str
    outcome_unit: str
    history: pd.DataFrame
    primary_environment_report: pd.DataFrame
    secondary_environment_report: pd.DataFrame | None
    environment_pair_report: pd.DataFrame | None
    confidence_report: pd.DataFrame
    conviction_report: pd.DataFrame
    primary_transition_report: pd.DataFrame
    secondary_transition_report: pd.DataFrame | None

    def save_csvs(
        self,
        output_directory: str | Path = ".",
    ) -> list[Path]:
        """
        Save every available report using consistent filenames.
        """
        directory = Path(output_directory)
        directory.mkdir(parents=True, exist_ok=True)

        slug = _slugify(self.asset_name)

        reports: dict[str, pd.DataFrame | None] = {
            "environment_history": self.history,
            "primary_environment_report": (
                self.primary_environment_report
            ),
            "secondary_environment_report": (
                self.secondary_environment_report
            ),
            "environment_pair_report": (
                self.environment_pair_report
            ),
            "confidence_report": self.confidence_report,
            "conviction_report": self.conviction_report,
            "primary_transition_report": (
                self.primary_transition_report
            ),
            "secondary_transition_report": (
                self.secondary_transition_report
            ),
        }

        saved_paths: list[Path] = []

        for report_name, report in reports.items():
            if report is None:
                continue

            path = directory / f"{slug}_{report_name}.csv"
            report.to_csv(path, index=False)
            saved_paths.append(path)

        return saved_paths


def _slugify(value: str) -> str:
    return (
        value.strip()
        .lower()
        .replace("/", "")
        .replace(" ", "_")
        .replace("-", "_")
    )


def history_to_environment_dataframe(
    history_run,
    prefix: str,
) -> pd.DataFrame:
    """
    Convert a MacroLens HistoricalEnvironmentRun into one row per month.
    """
    if history_run.history is None:
        raise RuntimeError(
            f"{prefix} history returned no successful observations."
        )

    rows = []

    for snapshot in history_run.history.snapshots:
        flags = snapshot.flags or []

        rows.append(
            {
                "date": pd.Timestamp(snapshot.as_of_date),
                f"{prefix}_environment": snapshot.environment_label,
                f"{prefix}_confidence": snapshot.confidence_score,
                f"{prefix}_conviction": (
                    snapshot.environment_conviction_score
                ),
                f"{prefix}_conviction_label": (
                    snapshot.environment_conviction_label
                ),
                f"{prefix}_activity_score": snapshot.activity_score,
                f"{prefix}_activity_label": snapshot.activity_label,
                f"{prefix}_inflation_score": (
                    snapshot.inflation_impulse_score
                ),
                f"{prefix}_inflation_label": (
                    snapshot.inflation_impulse_label
                ),
                f"{prefix}_financial_score": (
                    snapshot.financial_impulse_score
                ),
                f"{prefix}_financial_label": (
                    snapshot.financial_impulse_label
                ),
                f"{prefix}_flags": "|".join(flags),
                f"{prefix}_flag_count": len(flags),
            }
        )

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        raise RuntimeError(
            f"{prefix} history DataFrame is empty."
        )

    dataframe["month"] = dataframe["date"].dt.to_period("M")

    return (
        dataframe
        .sort_values("date")
        .drop_duplicates("month", keep="last")
        .drop(columns="date")
        .reset_index(drop=True)
    )


def asset_prices_to_monthly(
    asset_data: pd.DataFrame,
    value_column: str = "value",
    date_column: str = "date",
) -> pd.DataFrame:
    """
    Convert daily or irregular asset data into month-end observations.
    """
    required_columns = {date_column, value_column}

    missing = required_columns.difference(asset_data.columns)

    if missing:
        raise ValueError(
            "Asset data is missing required columns: "
            + ", ".join(sorted(missing))
        )

    monthly = asset_data[
        [date_column, value_column]
    ].copy()

    monthly[date_column] = pd.to_datetime(
        monthly[date_column]
    )

    monthly = monthly.dropna(
        subset=[date_column, value_column]
    )

    monthly["month"] = (
        monthly[date_column].dt.to_period("M")
    )

    return (
        monthly
        .sort_values(date_column)
        .groupby("month", as_index=False)
        .agg(asset_close=(value_column, "last"))
    )


def add_forward_outcomes(
    data: pd.DataFrame,
    horizons: Iterable[int],
    *,
    outcome_mode: str = "percentage_return",
    outcome_multiplier: float = 1.0,
) -> pd.DataFrame:
    """
    Calculate future asset outcomes.

    percentage_return:
        Future price divided by current price minus one.

    absolute_change:
        Future value minus current value, multiplied by
        outcome_multiplier.

    Examples:
        Equity return:
            outcome_mode="percentage_return"

        Treasury yield change in basis points:
            outcome_mode="absolute_change"
            outcome_multiplier=100
    """
    valid_modes = {
        "percentage_return",
        "absolute_change",
    }

    if outcome_mode not in valid_modes:
        raise ValueError(
            f"outcome_mode must be one of {sorted(valid_modes)}."
        )

    result = data.copy()

    if "month" not in result:
        raise ValueError("Monthly outcomes require an explicit month column.")
    months = pd.PeriodIndex(result["month"], freq="M")
    if months.has_duplicates:
        raise ValueError("Monthly outcomes require unique months.")
    prices = pd.Series(result["asset_close"].to_numpy(), index=months)

    for horizon in horizons:
        if not isinstance(horizon, int) or horizon <= 0:
            raise ValueError(
                "Forward horizons must be positive."
            )

        # Calendar-month lookup prevents a missing month from lengthening the horizon.
        future_value = pd.Series(prices.reindex(months + horizon).to_numpy(), index=result.index)

        if outcome_mode == "percentage_return":
            outcome = (
                future_value
                / result["asset_close"]
                - 1
            )
        else:
            outcome = (
                future_value
                - result["asset_close"]
            ) * outcome_multiplier

        result[f"forward_outcome_{horizon}m"] = outcome.replace([float("inf"), -float("inf")], float("nan"))

    return result


def add_transition_fields(
    data: pd.DataFrame,
    prefix: str,
) -> pd.DataFrame:
    result = data.copy()

    environment_column = f"{prefix}_environment"
    previous_column = f"{prefix}_previous_environment"
    changed_column = f"{prefix}_environment_changed"
    transition_column = f"{prefix}_transition"

    result[previous_column] = (
        result[environment_column].shift(1)
    )

    result[changed_column] = (
        result[environment_column]
        != result[previous_column]
    )

    result[transition_column] = (
        result[previous_column].fillna("Unknown")
        + " → "
        + result[environment_column]
    )

    return result


def summarize_environment_groups(
    data: pd.DataFrame,
    group_columns: list[str],
    horizons: Iterable[int],
    report_type: str,
) -> pd.DataFrame:
    """
    Summarize the forward-return distribution for each environment group.
    """
    rows: list[dict] = []

    grouped = data.groupby(
        group_columns,
        observed=True,
        dropna=False,
    )

    for group_values, group in grouped:
        if not isinstance(group_values, tuple):
            group_values = (group_values,)

        row: dict = {
            "report_type": report_type,
        }

        for column, value in zip(
            group_columns,
            group_values,
        ):
            row[column] = value

        for horizon in horizons:
            outcome_column = (
                f"forward_outcome_{horizon}m"
            )

            outcomes = group[outcome_column].dropna()

            row[f"observations_{horizon}m"] = len(outcomes)

            row[f"average_outcome_{horizon}m"] = outcomes.mean()
            row[f"median_outcome_{horizon}m"] = outcomes.median()

            row[f"positive_rate_{horizon}m"] = (
                (outcomes > 0).mean()
                if not outcomes.empty
                else float("nan")
            )

            row[f"negative_rate_{horizon}m"] = (
                (outcomes < 0).mean()
                if not outcomes.empty
                else float("nan")
            )

            row[f"outcome_std_{horizon}m"] = outcomes.std()

            row[f"outcome_25th_{horizon}m"] = (
                outcomes.quantile(0.25)
            )

            row[f"outcome_75th_{horizon}m"] = (
                outcomes.quantile(0.75)
            )

            row[f"best_outcome_{horizon}m"] = outcomes.max()
            row[f"worst_outcome_{horizon}m"] = outcomes.min()

        confidence_columns = [
            column
            for column in data.columns
            if column.endswith("_confidence")
        ]

        conviction_columns = [
            column
            for column in data.columns
            if column.endswith("_conviction")
        ]

        if confidence_columns:
            row["average_confidence"] = (
                group[confidence_columns]
                .mean(axis=1)
                .mean()
            )

        if conviction_columns:
            row["average_conviction"] = (
                group[conviction_columns]
                .mean(axis=1)
                .mean()
            )

        rows.append(row)

    report = pd.DataFrame(rows)

    if report.empty:
        return report

    first_horizon = list(horizons)[0]

    return report.sort_values(
        [
            f"observations_{first_horizon}m",
            f"average_outcome_{first_horizon}m",
        ],
        ascending=[False, False],
    ).reset_index(drop=True)


def summarize_transitions(
    data: pd.DataFrame,
    prefix: str,
    horizons: Iterable[int],
    minimum_observations: int,
) -> pd.DataFrame:
    changed_column = f"{prefix}_environment_changed"
    previous_column = f"{prefix}_previous_environment"
    transition_column = f"{prefix}_transition"

    sample = data.loc[
        data[changed_column]
        & data[previous_column].notna()
    ].copy()

    report = summarize_environment_groups(
        sample,
        group_columns=[transition_column],
        horizons=horizons,
        report_type=f"{prefix} environment transition",
    )

    if report.empty:
        return report

    first_horizon = list(horizons)[0]

    return report.loc[
        report[f"observations_{first_horizon}m"]
        >= minimum_observations
    ].reset_index(drop=True)


def validate_environment_asset_relationship(
    *,
    asset_name: str,
    asset_data: pd.DataFrame,
    primary_history_run,
    primary_prefix: str,
    secondary_history_run=None,
    secondary_prefix: str | None = None,
    horizons: Iterable[int] = DEFAULT_HORIZONS,
    months_to_analyze: int | None = None,
    minimum_pair_observations: int = 3,
    value_column: str = "value",
    date_column: str = "date",
    outcome_mode: str = "percentage_return",
    outcome_multiplier: float = 1.0,
    outcome_name: str = "Return",
    outcome_unit: str = "decimal",
) -> EnvironmentValidationResult:
    """
    Validate how an asset behaved after MacroLens environments.

    The primary economy is required. A secondary economy is optional and
    enables relative environment-pair analysis.
    """
    horizons = tuple(sorted(set(horizons)))

    if not horizons:
        raise ValueError(
            "At least one forward-return horizon is required."
        )

    if secondary_history_run is not None and not secondary_prefix:
        raise ValueError(
            "secondary_prefix is required when a secondary history "
            "run is supplied."
        )

    primary = history_to_environment_dataframe(
        primary_history_run,
        prefix=primary_prefix,
    )

    asset_monthly = asset_prices_to_monthly(
        asset_data,
        value_column=value_column,
        date_column=date_column,
    )

    history = primary.merge(
        asset_monthly,
        on="month",
        how="inner",
    )

    secondary_environment_report = None
    environment_pair_report = None
    secondary_transition_report = None

    if secondary_history_run is not None:
        secondary = history_to_environment_dataframe(
            secondary_history_run,
            prefix=secondary_prefix,
        )

        history = history.merge(
            secondary,
            on="month",
            how="inner",
        )

    history = history.sort_values(
        "month"
    ).reset_index(drop=True)

    if months_to_analyze is not None:
        history = (
            history
            .tail(months_to_analyze)
            .reset_index(drop=True)
        )

    if history.empty:
        raise RuntimeError(
            "No matched monthly environment and asset observations."
        )

    history = add_forward_outcomes(
        history,
        horizons=horizons,
        outcome_mode=outcome_mode,
        outcome_multiplier=outcome_multiplier,
    )

    history = add_transition_fields(
        history,
        prefix=primary_prefix,
    )

    if secondary_history_run is not None:
        history = add_transition_fields(
            history,
            prefix=secondary_prefix,
        )

    confidence_columns = [
        f"{primary_prefix}_confidence"
    ]

    conviction_columns = [
        f"{primary_prefix}_conviction"
    ]

    if secondary_history_run is not None:
        confidence_columns.append(
            f"{secondary_prefix}_confidence"
        )
        conviction_columns.append(
            f"{secondary_prefix}_conviction"
        )

    history["average_environment_confidence"] = (
        history[confidence_columns].mean(axis=1)
    )

    history["average_environment_conviction"] = (
        history[conviction_columns].mean(axis=1)
    )

    history["confidence_bucket"] = pd.cut(
        history["average_environment_confidence"],
        bins=[
            float("-inf"),
            0.60,
            0.75,
            float("inf"),
        ],
        labels=[
            "Low confidence",
            "Moderate confidence",
            "High confidence",
        ],
    )

    history["conviction_bucket"] = pd.cut(
        history["average_environment_conviction"],
        bins=[
            float("-inf"),
            0.25,
            0.50,
            float("inf"),
        ],
        labels=[
            "Low conviction",
            "Moderate conviction",
            "High conviction",
        ],
    )

    primary_environment_report = (
        summarize_environment_groups(
            history,
            group_columns=[
                f"{primary_prefix}_environment"
            ],
            horizons=horizons,
            report_type="Primary environment",
        )
    )

    primary_transition_report = summarize_transitions(
        history,
        prefix=primary_prefix,
        horizons=horizons,
        minimum_observations=minimum_pair_observations,
    )

    if secondary_history_run is not None:
        secondary_environment_report = (
            summarize_environment_groups(
                history,
                group_columns=[
                    f"{secondary_prefix}_environment"
                ],
                horizons=horizons,
                report_type="Secondary environment",
            )
        )

        environment_pair_report = (
            summarize_environment_groups(
                history,
                group_columns=[
                    f"{primary_prefix}_environment",
                    f"{secondary_prefix}_environment",
                ],
                horizons=horizons,
                report_type="Environment pair",
            )
        )

        first_horizon = horizons[0]

        environment_pair_report = (
            environment_pair_report.loc[
                environment_pair_report[
                    f"observations_{first_horizon}m"
                ]
                >= minimum_pair_observations
            ]
            .reset_index(drop=True)
        )

        secondary_transition_report = summarize_transitions(
            history,
            prefix=secondary_prefix,
            horizons=horizons,
            minimum_observations=minimum_pair_observations,
        )

    confidence_report = summarize_environment_groups(
        history,
        group_columns=["confidence_bucket"],
        horizons=horizons,
        report_type="Confidence bucket",
    )

    conviction_report = summarize_environment_groups(
        history,
        group_columns=["conviction_bucket"],
        horizons=horizons,
        report_type="Conviction bucket",
    )

    history_output = history.copy()
    history_output["month"] = (
        history_output["month"].astype(str)
    )

    return EnvironmentValidationResult(
        asset_name=asset_name,
        outcome_name=outcome_name,
        outcome_unit=outcome_unit,
        history=history_output,
        primary_environment_report=(
            primary_environment_report
        ),
        secondary_environment_report=(
            secondary_environment_report
        ),
        environment_pair_report=environment_pair_report,
        confidence_report=confidence_report,
        conviction_report=conviction_report,
        primary_transition_report=(
            primary_transition_report
        ),
        secondary_transition_report=(
            secondary_transition_report
        ),
    )