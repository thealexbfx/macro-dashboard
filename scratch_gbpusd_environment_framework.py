from __future__ import annotations

from datetime import date

import pandas as pd

from data.yahoo import get_fx_data_yahoo
from macro_engine.pipelines.history import (
    run_uk_environment_history,
    run_usa_environment_history,
)
from macro_engine.research.environment_validation import (
    validate_environment_asset_relationship,
)


MONTHS_TO_ANALYZE = 60
END_DATE = date.today()

START_DATE = (
    pd.Timestamp(END_DATE)
    - pd.DateOffset(months=MONTHS_TO_ANALYZE + 12)
).date()


def print_report(
    title: str,
    report: pd.DataFrame | None,
) -> None:
    print("\n" + "=" * 120)
    print(title)
    print("=" * 120)

    if report is None or report.empty:
        print("No qualifying observations.")
        return

    display = report.copy()

    percentage_columns = [
        column
        for column in display.columns
        if any(
            phrase in column
            for phrase in [
                "return_",
                "up_rate_",
                "down_rate_",
                "average_confidence",
                "average_conviction",
            ]
        )
    ]

    for column in percentage_columns:
        display[column] = display[column] * 100

    with pd.option_context(
        "display.max_rows",
        None,
        "display.max_columns",
        None,
        "display.width",
        280,
    ):
        print(
            display.to_string(
                index=False,
                float_format=lambda value: f"{value:.2f}",
            )
        )


print("\nRunning USA environment history...")

usa_history = run_usa_environment_history(
    start_date=START_DATE,
    end_date=END_DATE,
    frequency="monthly",
)

print("Running UK environment history...")

uk_history = run_uk_environment_history(
    start_date=START_DATE,
    end_date=END_DATE,
    frequency="monthly",
)

print("Downloading GBP/USD...")

gbpusd = get_fx_data_yahoo(
    ticker="GBPUSD=X",
    start_date=START_DATE,
    end_date=END_DATE,
)

result = validate_environment_asset_relationship(
    asset_name="GBPUSD",
    asset_data=gbpusd,
    primary_history_run=usa_history,
    primary_prefix="us",
    secondary_history_run=uk_history,
    secondary_prefix="uk",
    horizons=[1, 3, 6],
    months_to_analyze=MONTHS_TO_ANALYZE,
    minimum_pair_observations=3,
)

print("\n" + "=" * 120)
print("GBP/USD ENVIRONMENT VALIDATION FRAMEWORK")
print("=" * 120)

print(
    f"Matched monthly observations: "
    f"{len(result.history)}"
)

print(
    f"First month: {result.history['month'].iloc[0]}"
)

print(
    f"Last month:  {result.history['month'].iloc[-1]}"
)

print_report(
    "GBP/USD BY US ENVIRONMENT",
    result.primary_environment_report,
)

print_report(
    "GBP/USD BY UK ENVIRONMENT",
    result.secondary_environment_report,
)

print_report(
    "GBP/USD BY US–UK ENVIRONMENT PAIR",
    result.environment_pair_report,
)

print_report(
    "GBP/USD BY CONFIDENCE BUCKET",
    result.confidence_report,
)

print_report(
    "GBP/USD BY CONVICTION BUCKET",
    result.conviction_report,
)

print_report(
    "GBP/USD AFTER US ENVIRONMENT TRANSITIONS",
    result.primary_transition_report,
)

print_report(
    "GBP/USD AFTER UK ENVIRONMENT TRANSITIONS",
    result.secondary_transition_report,
)

saved_paths = result.save_csvs(
    output_directory="research_outputs",
)

print("\nSaved:")

for path in saved_paths:
    print(f"  {path}")