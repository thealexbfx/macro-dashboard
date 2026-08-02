from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from macro_engine.decision.historical_models import (
    HistoricalEvidence,
)


RESEARCH_OUTPUTS_DIR = Path("research_outputs")


@dataclass(frozen=True)
class HistoricalDataset:
    asset_key: str
    display_name: str

    primary_file: str
    primary_column: str
    primary_source: str

    secondary_file: str
    secondary_column: str
    secondary_source: str

    pair_file: str
    pair_primary_column: str
    pair_secondary_column: str


HISTORICAL_DATASETS: dict[str, HistoricalDataset] = {
    "gbpusd": HistoricalDataset(
        asset_key="gbpusd",
        display_name="GBP/USD",
        primary_file="gbpusd_primary_environment_report.csv",
        primary_column="us_environment",
        primary_source="US environment history",
        secondary_file="gbpusd_secondary_environment_report.csv",
        secondary_column="uk_environment",
        secondary_source="UK environment history",
        pair_file="gbpusd_environment_pair_report.csv",
        pair_primary_column="us_environment",
        pair_secondary_column="uk_environment",
    ),

    "eurusd": HistoricalDataset(
        asset_key="eurusd",
        display_name="EUR/USD",
        primary_file="eurusd_primary_environment_report.csv",
        primary_column="us_environment",
        primary_source="US environment history",
        secondary_file="eurusd_secondary_environment_report.csv",
        secondary_column="euro_environment",
        secondary_source="Euro Area environment history",
        pair_file="eurusd_environment_pair_report.csv",
        pair_primary_column="us_environment",
        pair_secondary_column="euro_environment",
    ),
}


def get_historical_dataset(
    asset_key: str,
) -> HistoricalDataset:
    try:
        return HISTORICAL_DATASETS[asset_key]
    except KeyError as exc:
        available = ", ".join(HISTORICAL_DATASETS)

        raise ValueError(
            f"No historical dataset is registered for {asset_key}. "
            f"Available datasets: {available}"
        ) from exc


def _optional_float(
    value: object,
) -> float | None:
    if pd.isna(value):
        return None

    return float(value)


def _load_report(
    file_name: str,
) -> pd.DataFrame | None:
    path = RESEARCH_OUTPUTS_DIR / file_name

    if not path.exists():
        return None

    return pd.read_csv(path)


def _build_evidence(
    *,
    row: pd.Series,
    source: str,
    label: str,
    horizon_months: int,
) -> HistoricalEvidence:
    suffix = f"_{horizon_months}m"

    required_columns = {
        f"observations{suffix}",
        f"average_return{suffix}",
        f"median_return{suffix}",
        f"up_rate{suffix}",
        f"down_rate{suffix}",
    }

    missing_columns = required_columns.difference(row.index)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))

        raise ValueError(
            f"Historical report is missing required columns: {missing}"
        )

    return HistoricalEvidence(
        source=source,
        label=label,
        observations=int(row[f"observations{suffix}"]),
        average_return=_optional_float(
            row[f"average_return{suffix}"]
        ),
        median_return=_optional_float(
            row[f"median_return{suffix}"]
        ),
        up_rate=_optional_float(
            row[f"up_rate{suffix}"]
        ),
        down_rate=_optional_float(
            row[f"down_rate{suffix}"]
        ),
    )


def _load_single_environment_evidence(
    *,
    file_name: str,
    label_column: str,
    environment: str,
    source: str,
    horizon_months: int,
) -> HistoricalEvidence | None:
    dataframe = _load_report(file_name)

    if dataframe is None or label_column not in dataframe.columns:
        return None

    matches = dataframe.loc[
        dataframe[label_column] == environment
    ]

    if matches.empty:
        return None

    return _build_evidence(
        row=matches.iloc[0],
        source=source,
        label=environment,
        horizon_months=horizon_months,
    )


def load_historical_evidence(
    *,
    asset_key: str,
    primary_environment: str,
    secondary_environment: str,
    horizon_months: int = 3,
) -> tuple[HistoricalEvidence, ...]:
    dataset = get_historical_dataset(asset_key)

    evidence: list[HistoricalEvidence] = []

    primary = _load_single_environment_evidence(
        file_name=dataset.primary_file,
        label_column=dataset.primary_column,
        environment=primary_environment,
        source=dataset.primary_source,
        horizon_months=horizon_months,
    )

    if primary is not None:
        evidence.append(primary)

    secondary = _load_single_environment_evidence(
        file_name=dataset.secondary_file,
        label_column=dataset.secondary_column,
        environment=secondary_environment,
        source=dataset.secondary_source,
        horizon_months=horizon_months,
    )

    if secondary is not None:
        evidence.append(secondary)

    pair_dataframe = _load_report(dataset.pair_file)

    if (
        pair_dataframe is not None
        and dataset.pair_primary_column in pair_dataframe.columns
        and dataset.pair_secondary_column in pair_dataframe.columns
    ):
        pair_matches = pair_dataframe.loc[
            (
                pair_dataframe[dataset.pair_primary_column]
                == primary_environment
            )
            & (
                pair_dataframe[dataset.pair_secondary_column]
                == secondary_environment
            )
        ]

        if not pair_matches.empty:
            pair_label = (
                f"{primary_environment} / "
                f"{secondary_environment}"
            )

            pair_evidence = _build_evidence(
                row=pair_matches.iloc[0],
                source="Exact environment pair history",
                label=pair_label,
                horizon_months=horizon_months,
            )

            if pair_evidence.observations > 0:
                evidence.append(pair_evidence)

    return tuple(evidence)