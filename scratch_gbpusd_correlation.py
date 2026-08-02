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

# Request a small buffer so monthly returns and forward returns calculate cleanly.
START_DATE = (
    pd.Timestamp(END_DATE) - pd.DateOffset(months=MONTHS_TO_ANALYZE + 3)
).date()


def history_to_dataframe(history_run, prefix: str) -> pd.DataFrame:
    if history_run.history is None:
        raise RuntimeError(f"{prefix} history returned no successful observations.")

    rows = [
        {
            "date": pd.Timestamp(snapshot.as_of_date),
            f"{prefix}_activity": snapshot.activity_score,
            f"{prefix}_inflation": snapshot.inflation_impulse_score,
            f"{prefix}_financial": snapshot.financial_impulse_score,
        }
        for snapshot in history_run.history.snapshots
    ]

    df = pd.DataFrame(rows)

    if df.empty:
        raise RuntimeError(f"{prefix} history DataFrame is empty.")

    # Align every observation to its calendar month.
    df["month"] = df["date"].dt.to_period("M")

    return (
        df.sort_values("date")
        .drop_duplicates("month", keep="last")
        .drop(columns="date")
    )


print("\nRunning USA model history...")
usa_run = run_usa_environment_history(
    start_date=START_DATE,
    end_date=END_DATE,
    frequency="monthly",
)

print("Running UK model history...")
uk_run = run_uk_environment_history(
    start_date=START_DATE,
    end_date=END_DATE,
    frequency="monthly",
)

print("Downloading GBP/USD from Yahoo Finance...")
fx_daily = get_fx_data_yahoo(
    ticker="GBPUSD=X",
    start_date=START_DATE,
    end_date=END_DATE,
)

if fx_daily.empty:
    raise RuntimeError("Yahoo Finance returned no GBP/USD data.")

usa_df = history_to_dataframe(usa_run, "us")
uk_df = history_to_dataframe(uk_run, "uk")

fx_daily["date"] = pd.to_datetime(fx_daily["date"])
fx_daily["month"] = fx_daily["date"].dt.to_period("M")

# Last available daily GBP/USD close in each calendar month.
fx_monthly = (
    fx_daily.sort_values("date")
    .groupby("month", as_index=False)
    .agg(
        gbpusd_close=("value", "last"),
        gbpusd_trading_days=("value", "size"),
    )
)

research = (
    usa_df.merge(uk_df, on="month", how="inner")
    .merge(fx_monthly, on="month", how="inner")
    .sort_values("month")
    .tail(MONTHS_TO_ANALYZE)
    .reset_index(drop=True)
)

research["activity_difference"] = (
    research["us_activity"] - research["uk_activity"]
)

research["inflation_difference"] = (
    research["us_inflation"] - research["uk_inflation"]
)

research["financial_difference"] = (
    research["us_financial"] - research["uk_financial"]
)

# GBP/USD rises when GBP strengthens against USD.
research["gbpusd_monthly_return"] = research["gbpusd_close"].pct_change()

# Forward returns measure what happened after each model observation.
research["gbpusd_forward_1m"] = (
    research["gbpusd_close"].shift(-1) / research["gbpusd_close"] - 1
)

research["gbpusd_forward_3m"] = (
    research["gbpusd_close"].shift(-3) / research["gbpusd_close"] - 1
)

score_columns = [
    "us_activity",
    "uk_activity",
    "activity_difference",
    "us_inflation",
    "uk_inflation",
    "inflation_difference",
    "us_financial",
    "uk_financial",
    "financial_difference",
]

return_columns = [
    "gbpusd_monthly_return",
    "gbpusd_forward_1m",
    "gbpusd_forward_3m",
]

correlations = research[score_columns + return_columns].corr().loc[
    score_columns,
    return_columns,
]

display_columns = [
    "month",
    "gbpusd_close",
    "us_activity",
    "uk_activity",
    "activity_difference",
    "us_inflation",
    "uk_inflation",
    "inflation_difference",
    "us_financial",
    "uk_financial",
    "financial_difference",
    "gbpusd_monthly_return",
    "gbpusd_forward_1m",
    "gbpusd_forward_3m",
]

output = research[display_columns].copy()
output["month"] = output["month"].astype(str)

print("\n" + "=" * 100)
print("GBP/USD RELATIVE MACRO CORRELATION TEST")
print("=" * 100)

print(f"\nRequested model period: {START_DATE} to {END_DATE}")
print(f"Matched monthly observations: {len(research)}")
print(f"First matched month: {output['month'].iloc[0]}")
print(f"Last matched month:  {output['month'].iloc[-1]}")

print("\nLAST 60 MONTHS OF MATCHED DATA")
print("-" * 100)

with pd.option_context(
    "display.max_rows",
    100,
    "display.max_columns",
    None,
    "display.width",
    220,
    "display.float_format",
    "{:.4f}".format,
):
    print(output.to_string(index=False))

print("\nCORRELATIONS")
print("-" * 100)
print(
    correlations.rename(
        columns={
            "gbpusd_monthly_return": "Same-month return",
            "gbpusd_forward_1m": "Next 1-month return",
            "gbpusd_forward_3m": "Next 3-month return",
        }
    ).round(4).to_string()
)

ranked = (
    correlations["gbpusd_forward_1m"]
    .dropna()
    .sort_values(key=lambda values: values.abs(), ascending=False)
)

print("\nNEXT-MONTH CORRELATIONS, RANKED BY ABSOLUTE STRENGTH")
print("-" * 100)

for score_name, correlation in ranked.items():
    print(f"{score_name:<25} {correlation:>8.4f}")

def summarize_condition(
    data: pd.DataFrame,
    condition: pd.Series,
    signal_name: str,
    expected_direction: str | None = None,
) -> dict:
    """
    Summarize GBP/USD returns after a specified macro condition.

    expected_direction:
        "down" means the macro signal is expected to strengthen USD
        and therefore lower GBP/USD.

        "up" means the macro signal is expected to strengthen GBP
        and therefore raise GBP/USD.
    """
    sample = data.loc[condition].copy()

    one_month = sample["gbpusd_forward_1m"].dropna()
    three_month = sample["gbpusd_forward_3m"].dropna()

    if expected_direction == "down":
        hit_rate_1m = (one_month < 0).mean()
        hit_rate_3m = (three_month < 0).mean()
    elif expected_direction == "up":
        hit_rate_1m = (one_month > 0).mean()
        hit_rate_3m = (three_month > 0).mean()
    else:
        hit_rate_1m = float("nan")
        hit_rate_3m = float("nan")

    return {
        "signal": signal_name,
        "observations_1m": len(one_month),
        "average_1m": one_month.mean(),
        "median_1m": one_month.median(),
        "hit_rate_1m": hit_rate_1m,
        "best_1m": one_month.max(),
        "worst_1m": one_month.min(),
        "observations_3m": len(three_month),
        "average_3m": three_month.mean(),
        "median_3m": three_month.median(),
        "hit_rate_3m": hit_rate_3m,
        "best_3m": three_month.max(),
        "worst_3m": three_month.min(),
    }


signal_tests = [
    summarize_condition(
        research,
        research["activity_difference"] >= 0.30,
        "US activity leads UK by at least 0.30",
        expected_direction="down",
    ),
    summarize_condition(
        research,
        research["activity_difference"] <= -0.30,
        "UK activity leads US by at least 0.30",
        expected_direction="up",
    ),
    summarize_condition(
        research,
        research["inflation_difference"] >= 0.30,
        "US inflation impulse leads UK by at least 0.30",
        expected_direction="down",
    ),
    summarize_condition(
        research,
        research["inflation_difference"] <= -0.30,
        "UK inflation impulse leads US by at least 0.30",
        expected_direction="up",
    ),
    summarize_condition(
        research,
        (
            (research["activity_difference"] > 0)
            & (research["inflation_difference"] > 0)
        ),
        "US leads UK in both activity and inflation",
        expected_direction="down",
    ),
    summarize_condition(
        research,
        (
            (research["activity_difference"] < 0)
            & (research["inflation_difference"] < 0)
        ),
        "UK leads US in both activity and inflation",
        expected_direction="up",
    ),
    summarize_condition(
        research,
        (
            (research["us_activity"] > 0)
            & (research["uk_activity"] < 0)
        ),
        "US activity positive while UK activity negative",
        expected_direction="down",
    ),
    summarize_condition(
        research,
        (
            (research["uk_activity"] > 0)
            & (research["us_activity"] < 0)
        ),
        "UK activity positive while US activity negative",
        expected_direction="up",
    ),
    summarize_condition(
        research,
        (
            (research["us_inflation"] > 0)
            & (research["uk_inflation"] < 0)
        ),
        "US inflation accelerating while UK inflation easing",
        expected_direction="down",
    ),
    summarize_condition(
        research,
        (
            (research["uk_inflation"] > 0)
            & (research["us_inflation"] < 0)
        ),
        "UK inflation accelerating while US inflation easing",
        expected_direction="up",
    ),
]

signal_report = pd.DataFrame(signal_tests)

percentage_columns = [
    "average_1m",
    "median_1m",
    "hit_rate_1m",
    "best_1m",
    "worst_1m",
    "average_3m",
    "median_3m",
    "hit_rate_3m",
    "best_3m",
    "worst_3m",
]

signal_report_display = signal_report.copy()

for column in percentage_columns:
    signal_report_display[column] = (
        signal_report_display[column] * 100
    )

print("\nCONDITIONAL SIGNAL VALIDATION")
print("-" * 100)
print(
    "Hit rate measures whether GBP/USD moved in the direction implied "
    "by the relative macro condition."
)

for _, row in signal_report_display.iterrows():
    print("\n" + row["signal"])
    print("-" * len(row["signal"]))

    print(
        f"1-month observations: {int(row['observations_1m'])}\n"
        f"Average 1M return:    {row['average_1m']:+.2f}%\n"
        f"Median 1M return:     {row['median_1m']:+.2f}%\n"
        f"Directional hit rate:{row['hit_rate_1m']:>7.1f}%\n"
        f"Best 1M return:       {row['best_1m']:+.2f}%\n"
        f"Worst 1M return:      {row['worst_1m']:+.2f}%"
    )

    print(
        f"\n3-month observations: {int(row['observations_3m'])}\n"
        f"Average 3M return:    {row['average_3m']:+.2f}%\n"
        f"Median 3M return:     {row['median_3m']:+.2f}%\n"
        f"Directional hit rate:{row['hit_rate_3m']:>7.1f}%\n"
        f"Best 3M return:       {row['best_3m']:+.2f}%\n"
        f"Worst 3M return:      {row['worst_3m']:+.2f}%"
    )


# Divide relative scores into three broad regimes.
research["activity_regime"] = pd.cut(
    research["activity_difference"],
    bins=[float("-inf"), -0.30, 0.30, float("inf")],
    labels=[
        "UK activity advantage",
        "Balanced activity",
        "US activity advantage",
    ],
)

research["inflation_regime"] = pd.cut(
    research["inflation_difference"],
    bins=[float("-inf"), -0.30, 0.30, float("inf")],
    labels=[
        "UK inflation advantage",
        "Balanced inflation",
        "US inflation advantage",
    ],
)

regime_table = (
    research.groupby(
        ["activity_regime", "inflation_regime"],
        observed=True,
    )
    .agg(
        observations=("gbpusd_forward_1m", "count"),
        average_forward_1m=("gbpusd_forward_1m", "mean"),
        median_forward_1m=("gbpusd_forward_1m", "median"),
        gbpusd_up_rate_1m=(
            "gbpusd_forward_1m",
            lambda values: (values.dropna() > 0).mean(),
        ),
        average_forward_3m=("gbpusd_forward_3m", "mean"),
    )
    .reset_index()
    .sort_values(
        ["observations", "average_forward_1m"],
        ascending=[False, False],
    )
)

regime_table_display = regime_table.copy()

for column in [
    "average_forward_1m",
    "median_forward_1m",
    "gbpusd_up_rate_1m",
    "average_forward_3m",
]:
    regime_table_display[column] = (
        regime_table_display[column] * 100
    )

print("\n" + "=" * 100)
print("ACTIVITY AND INFLATION REGIME MATRIX")
print("=" * 100)

with pd.option_context(
    "display.max_rows",
    None,
    "display.max_columns",
    None,
    "display.width",
    180,
    "display.float_format",
    "{:.2f}".format,
):
    print(regime_table_display.to_string(index=False))


signal_report_path = "gbpusd_conditional_signal_report.csv"
regime_report_path = "gbpusd_macro_regime_report.csv"

signal_report.to_csv(signal_report_path, index=False)
regime_table.to_csv(regime_report_path, index=False)

print(f"\nConditional report saved to: {signal_report_path}")
print(f"Regime report saved to:      {regime_report_path}")

def build_quantile_report(
    data: pd.DataFrame,
    signal_column: str,
    forward_return_column: str,
    quantiles: int = 5,
) -> pd.DataFrame:
    """
    Split a macro signal into equal-sized quantile buckets and summarize
    subsequent GBP/USD returns.
    """
    sample = data[[signal_column, forward_return_column]].dropna().copy()

    if len(sample) < quantiles:
        raise ValueError(
            f"Not enough observations to create {quantiles} quantiles "
            f"for {signal_column}."
        )

    sample["quantile"] = pd.qcut(
        sample[signal_column],
        q=quantiles,
        labels=[f"Q{i}" for i in range(1, quantiles + 1)],
        duplicates="drop",
    )

    report = (
        sample.groupby("quantile", observed=True)
        .agg(
            observations=(forward_return_column, "count"),
            signal_min=(signal_column, "min"),
            signal_max=(signal_column, "max"),
            signal_average=(signal_column, "mean"),
            average_return=(forward_return_column, "mean"),
            median_return=(forward_return_column, "median"),
            gbpusd_up_rate=(
                forward_return_column,
                lambda values: (values > 0).mean(),
            ),
            best_return=(forward_return_column, "max"),
            worst_return=(forward_return_column, "min"),
        )
        .reset_index()
    )

    report.insert(0, "signal", signal_column)
    report.insert(1, "forward_horizon", forward_return_column)

    return report


quantile_reports = []

signals_to_test = [
    "us_activity",
    "uk_activity",
    "activity_difference",
    "us_inflation",
    "uk_inflation",
    "inflation_difference",
]

forward_horizons = [
    "gbpusd_forward_1m",
    "gbpusd_forward_3m",
]

for signal_column in signals_to_test:
    for forward_return_column in forward_horizons:
        quantile_reports.append(
            build_quantile_report(
                research,
                signal_column=signal_column,
                forward_return_column=forward_return_column,
                quantiles=5,
            )
        )

quantile_report = pd.concat(
    quantile_reports,
    ignore_index=True,
)

quantile_report_display = quantile_report.copy()

for column in [
    "average_return",
    "median_return",
    "gbpusd_up_rate",
    "best_return",
    "worst_return",
]:
    quantile_report_display[column] = (
        quantile_report_display[column] * 100
    )


print("\n" + "=" * 100)
print("QUINTILE SIGNAL VALIDATION")
print("=" * 100)
print(
    "Q1 contains the lowest 20% of signal observations. "
    "Q5 contains the highest 20%."
)

for signal_column in signals_to_test:
    for forward_return_column in forward_horizons:
        subset = quantile_report_display.loc[
            (
                quantile_report_display["signal"]
                == signal_column
            )
            & (
                quantile_report_display["forward_horizon"]
                == forward_return_column
            )
        ]

        print(
            f"\n{signal_column.upper()} — "
            f"{forward_return_column.upper()}"
        )
        print("-" * 100)

        print(
            subset[
                [
                    "quantile",
                    "observations",
                    "signal_min",
                    "signal_max",
                    "signal_average",
                    "average_return",
                    "median_return",
                    "gbpusd_up_rate",
                    "best_return",
                    "worst_return",
                ]
            ].to_string(
                index=False,
                float_format=lambda value: f"{value:.2f}",
            )
        )


def calculate_quantile_spread(
    report: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compare Q5 against Q1 to test whether increasingly high macro scores
    are associated with meaningfully different forward returns.
    """
    rows = []

    grouped = report.groupby(
        ["signal", "forward_horizon"],
        observed=True,
    )

    for (signal, horizon), group in grouped:
        q1 = group.loc[group["quantile"] == "Q1"]
        q5 = group.loc[group["quantile"] == "Q5"]

        if q1.empty or q5.empty:
            continue

        q1_row = q1.iloc[0]
        q5_row = q5.iloc[0]

        rows.append(
            {
                "signal": signal,
                "forward_horizon": horizon,
                "q1_average_return": q1_row["average_return"],
                "q5_average_return": q5_row["average_return"],
                "q5_minus_q1_spread": (
                    q5_row["average_return"]
                    - q1_row["average_return"]
                ),
                "q1_median_return": q1_row["median_return"],
                "q5_median_return": q5_row["median_return"],
                "q1_up_rate": q1_row["gbpusd_up_rate"],
                "q5_up_rate": q5_row["gbpusd_up_rate"],
                "q1_observations": q1_row["observations"],
                "q5_observations": q5_row["observations"],
            }
        )

    return pd.DataFrame(rows)


quantile_spread_report = calculate_quantile_spread(
    quantile_report
)

quantile_spread_display = quantile_spread_report.copy()

for column in [
    "q1_average_return",
    "q5_average_return",
    "q5_minus_q1_spread",
    "q1_median_return",
    "q5_median_return",
    "q1_up_rate",
    "q5_up_rate",
]:
    quantile_spread_display[column] = (
        quantile_spread_display[column] * 100
    )

quantile_spread_display = quantile_spread_display.sort_values(
    "q5_minus_q1_spread",
    key=lambda values: values.abs(),
    ascending=False,
)

print("\n" + "=" * 100)
print("Q5 MINUS Q1 RETURN SPREADS")
print("=" * 100)
print(
    "A large absolute spread suggests materially different market outcomes "
    "between low and high signal regimes."
)

print(
    quantile_spread_display[
        [
            "signal",
            "forward_horizon",
            "q1_average_return",
            "q5_average_return",
            "q5_minus_q1_spread",
            "q1_median_return",
            "q5_median_return",
            "q1_up_rate",
            "q5_up_rate",
            "q1_observations",
            "q5_observations",
        ]
    ].to_string(
        index=False,
        float_format=lambda value: f"{value:.2f}",
    )
)


def calculate_monotonicity(
    report: pd.DataFrame,
) -> pd.DataFrame:
    """
    Measure whether average returns generally rise or fall consistently
    from Q1 through Q5.
    """
    rows = []

    grouped = report.groupby(
        ["signal", "forward_horizon"],
        observed=True,
    )

    quantile_order = {
        "Q1": 1,
        "Q2": 2,
        "Q3": 3,
        "Q4": 4,
        "Q5": 5,
    }

    for (signal, horizon), group in grouped:
        ordered = group.copy()
        ordered["quantile_number"] = (
            ordered["quantile"]
            .astype(str)
            .map(quantile_order)
        )

        ordered = ordered.sort_values("quantile_number")

        if len(ordered) < 3:
            continue

        rank_correlation = ordered[
            ["quantile_number", "average_return"]
        ].corr(method="spearman").iloc[0, 1]

        rows.append(
            {
                "signal": signal,
                "forward_horizon": horizon,
                "spearman_monotonicity": rank_correlation,
            }
        )

    return pd.DataFrame(rows)


monotonicity_report = calculate_monotonicity(
    quantile_report
).sort_values(
    "spearman_monotonicity",
    key=lambda values: values.abs(),
    ascending=False,
)

print("\n" + "=" * 100)
print("QUANTILE MONOTONICITY")
print("=" * 100)
print(
    "Values near +1 mean returns generally rise from Q1 to Q5. "
    "Values near -1 mean they generally fall."
)

print(
    monotonicity_report.to_string(
        index=False,
        float_format=lambda value: f"{value:.3f}",
    )
)


quantile_report_path = "gbpusd_quantile_report.csv"
quantile_spread_path = "gbpusd_quantile_spread_report.csv"
monotonicity_path = "gbpusd_quantile_monotonicity_report.csv"

quantile_report.to_csv(
    quantile_report_path,
    index=False,
)

quantile_spread_report.to_csv(
    quantile_spread_path,
    index=False,
)

monotonicity_report.to_csv(
    monotonicity_path,
    index=False,
)

print(f"\nQuantile report saved to:     {quantile_report_path}")
print(f"Quantile spread saved to:     {quantile_spread_path}")
print(f"Monotonicity report saved to: {monotonicity_path}")

csv_path = "gbpusd_relative_macro_last_60_months.csv"
output.to_csv(csv_path, index=False)

print(f"\nCSV saved to: {csv_path}")
print("\nInterpretation reminder:")
print("Positive correlation = a higher score tends to precede a higher GBP/USD return.")
print("Negative correlation = a higher score tends to precede a lower GBP/USD return.")
print("US minus UK differences should generally be interpreted from the USD side.")
print("=" * 100)