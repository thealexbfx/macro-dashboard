from __future__ import annotations

from datetime import date

import pandas as pd

from data.yahoo import get_fx_data_yahoo
from macro_engine.pipelines.history import (
    run_uk_environment_history,
    run_usa_environment_history,
)


MONTHS_TO_ANALYZE = 60
END_DATE = date.today()

START_DATE = (
    pd.Timestamp(END_DATE)
    - pd.DateOffset(months=MONTHS_TO_ANALYZE + 6)
).date()

MINIMUM_REGIME_OBSERVATIONS = 3


def history_to_dataframe(
    history_run,
    prefix: str,
) -> pd.DataFrame:
    if history_run.history is None:
        raise RuntimeError(
            f"{prefix} history returned no successful observations."
        )

    rows = []

    for snapshot in history_run.history.snapshots:
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
                f"{prefix}_activity_label": snapshot.activity_label,
                f"{prefix}_inflation_label": (
                    snapshot.inflation_impulse_label
                ),
                f"{prefix}_financial_label": (
                    snapshot.financial_impulse_label
                ),
                f"{prefix}_flags": "|".join(snapshot.flags),
                f"{prefix}_flag_count": len(snapshot.flags),
            }
        )

    dataframe = pd.DataFrame(rows)

    if dataframe.empty:
        raise RuntimeError(
            f"{prefix} history DataFrame is empty."
        )

    dataframe["month"] = (
        dataframe["date"].dt.to_period("M")
    )

    return (
        dataframe
        .sort_values("date")
        .drop_duplicates("month", keep="last")
        .drop(columns="date")
    )


def add_forward_returns(
    data: pd.DataFrame,
) -> pd.DataFrame:
    result = data.copy()

    for horizon in [1, 3, 6]:
        result[f"gbpusd_forward_{horizon}m"] = (
            result["gbpusd_close"].shift(-horizon)
            / result["gbpusd_close"]
            - 1
        )

    return result


def summarize_environment(
    data: pd.DataFrame,
    group_columns: list[str],
    environment_type: str,
) -> pd.DataFrame:
    rows = []

    grouped = data.groupby(
        group_columns,
        observed=True,
        dropna=False,
    )

    for group_values, group in grouped:
        if not isinstance(group_values, tuple):
            group_values = (group_values,)

        row = {
            "environment_type": environment_type,
        }

        for column, value in zip(
            group_columns,
            group_values,
        ):
            row[column] = value

        for horizon in [1, 3, 6]:
            return_column = (
                f"gbpusd_forward_{horizon}m"
            )

            returns = group[
                return_column
            ].dropna()

            row[
                f"observations_{horizon}m"
            ] = len(returns)

            row[
                f"average_return_{horizon}m"
            ] = returns.mean()

            row[
                f"median_return_{horizon}m"
            ] = returns.median()

            row[
                f"gbpusd_up_rate_{horizon}m"
            ] = (
                (returns > 0).mean()
                if not returns.empty
                else float("nan")
            )

            row[
                f"best_return_{horizon}m"
            ] = returns.max()

            row[
                f"worst_return_{horizon}m"
            ] = returns.min()

        row["average_confidence"] = (
            group[
                [
                    column
                    for column in [
                        "us_confidence",
                        "uk_confidence",
                    ]
                    if column in group.columns
                ]
            ]
            .mean(axis=1)
            .mean()
        )

        row["average_conviction"] = (
            group[
                [
                    column
                    for column in [
                        "us_conviction",
                        "uk_conviction",
                    ]
                    if column in group.columns
                ]
            ]
            .mean(axis=1)
            .mean()
        )

        rows.append(row)

    report = pd.DataFrame(rows)

    if report.empty:
        return report

    return report.sort_values(
        [
            "observations_3m",
            "average_return_3m",
        ],
        ascending=[False, False],
    )


def add_transition_fields(
    data: pd.DataFrame,
) -> pd.DataFrame:
    result = data.copy()

    result["us_previous_environment"] = (
        result["us_environment"].shift(1)
    )

    result["uk_previous_environment"] = (
        result["uk_environment"].shift(1)
    )

    result["us_environment_changed"] = (
        result["us_environment"]
        != result["us_previous_environment"]
    )

    result["uk_environment_changed"] = (
        result["uk_environment"]
        != result["uk_previous_environment"]
    )

    result["either_environment_changed"] = (
        result["us_environment_changed"]
        | result["uk_environment_changed"]
    )

    result["us_transition"] = (
        result["us_previous_environment"].fillna("Unknown")
        + " → "
        + result["us_environment"]
    )

    result["uk_transition"] = (
        result["uk_previous_environment"].fillna("Unknown")
        + " → "
        + result["uk_environment"]
    )

    return result


def summarize_transitions(
    data: pd.DataFrame,
    transition_column: str,
    economy: str,
) -> pd.DataFrame:
    transition_sample = data.loc[
        data[
            f"{economy}_environment_changed"
        ]
        & data[
            f"{economy}_previous_environment"
        ].notna()
    ].copy()

    report = summarize_environment(
        transition_sample,
        group_columns=[transition_column],
        environment_type=f"{economy.upper()} transition",
    )

    if report.empty:
        return report

    return report.loc[
        report["observations_1m"]
        >= MINIMUM_REGIME_OBSERVATIONS
    ].copy()


def print_report(
    title: str,
    report: pd.DataFrame,
    label_columns: list[str],
) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)

    if report.empty:
        print("No qualifying observations.")
        return

    display = report.copy()

    percentage_columns = [
        column
        for column in display.columns
        if (
            "return_" in column
            or "up_rate_" in column
            or column
            in {
                "average_confidence",
                "average_conviction",
            }
        )
    ]

    for column in percentage_columns:
        display[column] = (
            display[column] * 100
        )

    columns_to_show = (
        label_columns
        + [
            "observations_1m",
            "average_return_1m",
            "median_return_1m",
            "gbpusd_up_rate_1m",
            "observations_3m",
            "average_return_3m",
            "median_return_3m",
            "gbpusd_up_rate_3m",
            "observations_6m",
            "average_return_6m",
            "gbpusd_up_rate_6m",
            "average_confidence",
            "average_conviction",
        ]
    )

    available_columns = [
        column
        for column in columns_to_show
        if column in display.columns
    ]

    with pd.option_context(
        "display.max_rows",
        None,
        "display.max_columns",
        None,
        "display.width",
        250,
    ):
        print(
            display[
                available_columns
            ].to_string(
                index=False,
                float_format=lambda value: f"{value:.2f}",
            )
        )


print("\nRunning USA environment history...")

usa_run = run_usa_environment_history(
    start_date=START_DATE,
    end_date=END_DATE,
    frequency="monthly",
)

print("Running UK environment history...")

uk_run = run_uk_environment_history(
    start_date=START_DATE,
    end_date=END_DATE,
    frequency="monthly",
)

print("Downloading GBP/USD...")

fx_daily = get_fx_data_yahoo(
    ticker="GBPUSD=X",
    start_date=START_DATE,
    end_date=END_DATE,
)

if fx_daily.empty:
    raise RuntimeError(
        "Yahoo Finance returned no GBP/USD data."
    )

usa = history_to_dataframe(
    usa_run,
    prefix="us",
)

uk = history_to_dataframe(
    uk_run,
    prefix="uk",
)

fx_daily["date"] = pd.to_datetime(
    fx_daily["date"]
)

fx_daily["month"] = (
    fx_daily["date"].dt.to_period("M")
)

fx_monthly = (
    fx_daily
    .sort_values("date")
    .groupby("month", as_index=False)
    .agg(
        gbpusd_close=("value", "last"),
    )
)

research = (
    usa
    .merge(
        uk,
        on="month",
        how="inner",
    )
    .merge(
        fx_monthly,
        on="month",
        how="inner",
    )
    .sort_values("month")
    .tail(MONTHS_TO_ANALYZE)
    .reset_index(drop=True)
)

research = add_forward_returns(
    research
)

research = add_transition_fields(
    research
)

research["environment_pair"] = (
    research["us_environment"]
    + " | "
    + research["uk_environment"]
)

research["confidence_bucket"] = pd.cut(
    (
        research["us_confidence"]
        + research["uk_confidence"]
    )
    / 2,
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

research["conviction_bucket"] = pd.cut(
    (
        research["us_conviction"]
        + research["uk_conviction"]
    )
    / 2,
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


us_environment_report = summarize_environment(
    research,
    group_columns=["us_environment"],
    environment_type="US environment",
)

uk_environment_report = summarize_environment(
    research,
    group_columns=["uk_environment"],
    environment_type="UK environment",
)

environment_pair_report = summarize_environment(
    research,
    group_columns=[
        "us_environment",
        "uk_environment",
    ],
    environment_type="US–UK environment pair",
)

confidence_report = summarize_environment(
    research,
    group_columns=["confidence_bucket"],
    environment_type="Confidence bucket",
)

conviction_report = summarize_environment(
    research,
    group_columns=["conviction_bucket"],
    environment_type="Conviction bucket",
)

us_transition_report = summarize_transitions(
    research,
    transition_column="us_transition",
    economy="us",
)

uk_transition_report = summarize_transitions(
    research,
    transition_column="uk_transition",
    economy="uk",
)


print("\n" + "=" * 120)
print("GBP/USD HISTORICAL ENVIRONMENT VALIDATION")
print("=" * 120)

print(
    f"Requested period: {START_DATE} to {END_DATE}"
)

print(
    f"Matched monthly observations: {len(research)}"
)

print(
    f"First matched month: {research['month'].iloc[0]}"
)

print(
    f"Last matched month:  {research['month'].iloc[-1]}"
)


print_report(
    "GBP/USD RETURNS BY US ENVIRONMENT",
    us_environment_report,
    ["us_environment"],
)

print_report(
    "GBP/USD RETURNS BY UK ENVIRONMENT",
    uk_environment_report,
    ["uk_environment"],
)

qualifying_pairs = environment_pair_report.loc[
    environment_pair_report[
        "observations_1m"
    ]
    >= MINIMUM_REGIME_OBSERVATIONS
].copy()

print_report(
    (
        "GBP/USD RETURNS BY US–UK ENVIRONMENT PAIR "
        f"(MINIMUM {MINIMUM_REGIME_OBSERVATIONS} OBSERVATIONS)"
    ),
    qualifying_pairs,
    [
        "us_environment",
        "uk_environment",
    ],
)

print_report(
    "GBP/USD RETURNS BY AVERAGE ENVIRONMENT CONFIDENCE",
    confidence_report,
    ["confidence_bucket"],
)

print_report(
    "GBP/USD RETURNS BY AVERAGE ENVIRONMENT CONVICTION",
    conviction_report,
    ["conviction_bucket"],
)

print_report(
    "GBP/USD RETURNS AFTER US ENVIRONMENT TRANSITIONS",
    us_transition_report,
    ["us_transition"],
)

print_report(
    "GBP/USD RETURNS AFTER UK ENVIRONMENT TRANSITIONS",
    uk_transition_report,
    ["uk_transition"],
)


research_output = research.copy()

research_output["month"] = (
    research_output["month"].astype(str)
)

research_output.to_csv(
    "gbpusd_environment_history.csv",
    index=False,
)

us_environment_report.to_csv(
    "gbpusd_us_environment_report.csv",
    index=False,
)

uk_environment_report.to_csv(
    "gbpusd_uk_environment_report.csv",
    index=False,
)

environment_pair_report.to_csv(
    "gbpusd_environment_pair_report.csv",
    index=False,
)

confidence_report.to_csv(
    "gbpusd_environment_confidence_report.csv",
    index=False,
)

conviction_report.to_csv(
    "gbpusd_environment_conviction_report.csv",
    index=False,
)

us_transition_report.to_csv(
    "gbpusd_us_transition_report.csv",
    index=False,
)

uk_transition_report.to_csv(
    "gbpusd_uk_transition_report.csv",
    index=False,
)


print("\nSaved:")

print(
    "  gbpusd_environment_history.csv\n"
    "  gbpusd_us_environment_report.csv\n"
    "  gbpusd_uk_environment_report.csv\n"
    "  gbpusd_environment_pair_report.csv\n"
    "  gbpusd_environment_confidence_report.csv\n"
    "  gbpusd_environment_conviction_report.csv\n"
    "  gbpusd_us_transition_report.csv\n"
    "  gbpusd_uk_transition_report.csv"
)