from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from data.yahoo import get_fx_data_yahoo
from macro_engine.pipelines.history import (
    run_usa_environment_history,
)
from macro_engine.research.environment_validation import (
    EnvironmentValidationResult,
    validate_environment_asset_relationship,
)


MONTHS_TO_ANALYZE = 240
HORIZONS = [1, 3, 6]
END_DATE = date.today()

START_DATE = (
    pd.Timestamp(END_DATE)
    - pd.DateOffset(months=MONTHS_TO_ANALYZE + 24)
).date()


@dataclass(frozen=True)
class AssetConfiguration:
    name: str
    ticker: str
    outcome_mode: str
    outcome_multiplier: float
    outcome_name: str
    outcome_unit: str


ASSETS = [
    AssetConfiguration(
        name="SP500",
        ticker="^GSPC",
        outcome_mode="percentage_return",
        outcome_multiplier=1.0,
        outcome_name="S&P 500 return",
        outcome_unit="decimal",
    ),
    AssetConfiguration(
        name="US10Y",
        ticker="^TNX",
        outcome_mode="absolute_change",
        outcome_multiplier=100.0,
        outcome_name="10-year Treasury yield change",
        outcome_unit="basis points",
    ),
    AssetConfiguration(
        name="Gold",
        ticker="GC=F",
        outcome_mode="percentage_return",
        outcome_multiplier=1.0,
        outcome_name="Gold return",
        outcome_unit="decimal",
    ),
    AssetConfiguration(
        name="WTI",
        ticker="CL=F",
        outcome_mode="percentage_return",
        outcome_multiplier=1.0,
        outcome_name="WTI crude return",
        outcome_unit="decimal",
    ),
    AssetConfiguration(
        name="DXY",
        ticker="DX-Y.NYB",
        outcome_mode="percentage_return",
        outcome_multiplier=1.0,
        outcome_name="US Dollar Index return",
        outcome_unit="decimal",
    ),
]


def download_asset(
    configuration: AssetConfiguration,
) -> pd.DataFrame:
    print(
        f"Downloading {configuration.name} "
        f"({configuration.ticker})..."
    )

    data = get_fx_data_yahoo(
        ticker=configuration.ticker,
        start_date=START_DATE,
        end_date=END_DATE,
    )

    if data.empty:
        raise RuntimeError(
            f"No data returned for {configuration.name}."
        )

    return data


def create_compact_environment_report(
    result: EnvironmentValidationResult,
) -> pd.DataFrame:
    report = result.primary_environment_report.copy()

    selected_columns = [
        "us_environment",
        "observations_1m",
        "average_outcome_1m",
        "median_outcome_1m",
        "positive_rate_1m",
        "observations_3m",
        "average_outcome_3m",
        "median_outcome_3m",
        "positive_rate_3m",
        "observations_6m",
        "average_outcome_6m",
        "median_outcome_6m",
        "positive_rate_6m",
        "average_confidence",
        "average_conviction",
    ]

    available_columns = [
        column
        for column in selected_columns
        if column in report.columns
    ]

    report = report[available_columns].copy()

    report.insert(0, "asset", result.asset_name)
    report.insert(1, "outcome_name", result.outcome_name)
    report.insert(2, "outcome_unit", result.outcome_unit)

    return report


def create_cross_asset_regime_matrix(
    results: list[EnvironmentValidationResult],
) -> pd.DataFrame:
    rows = []

    for result in results:
        report = result.primary_environment_report

        for _, regime in report.iterrows():
            row = {
                "us_environment": regime["us_environment"],
                "asset": result.asset_name,
                "outcome_name": result.outcome_name,
                "outcome_unit": result.outcome_unit,
            }

            for horizon in HORIZONS:
                row[f"observations_{horizon}m"] = regime.get(
                    f"observations_{horizon}m"
                )

                value = regime.get(
                    f"average_outcome_{horizon}m"
                )

                if (
                    result.outcome_mode
                    if hasattr(result, "outcome_mode")
                    else None
                ):
                    pass

                if result.outcome_unit == "decimal":
                    value = (
                        value * 100
                        if pd.notna(value)
                        else value
                    )

                row[f"average_outcome_{horizon}m"] = value

                positive_rate = regime.get(
                    f"positive_rate_{horizon}m"
                )

                row[f"positive_rate_{horizon}m"] = (
                    positive_rate * 100
                    if pd.notna(positive_rate)
                    else positive_rate
                )

            rows.append(row)

    return pd.DataFrame(rows)


print("\nRunning USA environment history...")

usa_history = run_usa_environment_history(
    start_date=START_DATE,
    end_date=END_DATE,
    frequency="monthly",
)

results: list[EnvironmentValidationResult] = []

for configuration in ASSETS:
    asset_data = download_asset(configuration)

    result = validate_environment_asset_relationship(
        asset_name=configuration.name,
        asset_data=asset_data,
        primary_history_run=usa_history,
        primary_prefix="us",
        horizons=HORIZONS,
        months_to_analyze=MONTHS_TO_ANALYZE,
        minimum_pair_observations=3,
        outcome_mode=configuration.outcome_mode,
        outcome_multiplier=configuration.outcome_multiplier,
        outcome_name=configuration.outcome_name,
        outcome_unit=configuration.outcome_unit,
    )

    results.append(result)

    saved_paths = result.save_csvs(
        output_directory=(
            f"research_outputs/cross_asset/"
            f"{configuration.name.lower()}"
        )
    )

    print(
        f"{configuration.name}: "
        f"{len(result.history)} matched months, "
        f"{len(saved_paths)} reports saved."
    )


compact_reports = [
    create_compact_environment_report(result)
    for result in results
]

combined_environment_report = pd.concat(
    compact_reports,
    ignore_index=True,
)

cross_asset_matrix = create_cross_asset_regime_matrix(
    results
)

combined_environment_report.to_csv(
    "research_outputs/cross_asset/"
    "combined_us_environment_report.csv",
    index=False,
)

cross_asset_matrix.to_csv(
    "research_outputs/cross_asset/"
    "cross_asset_regime_matrix.csv",
    index=False,
)


print("\n" + "=" * 140)
print("CROSS-ASSET US ENVIRONMENT VALIDATION")
print("=" * 140)

display_matrix = cross_asset_matrix.copy()

with pd.option_context(
    "display.max_rows",
    None,
    "display.max_columns",
    None,
    "display.width",
    300,
):
    print(
        display_matrix.to_string(
            index=False,
            float_format=lambda value: f"{value:.2f}",
        )
    )


print("\nSaved combined reports:")

print(
    "  research_outputs/cross_asset/"
    "combined_us_environment_report.csv"
)

print(
    "  research_outputs/cross_asset/"
    "cross_asset_regime_matrix.csv"
)