from __future__ import annotations

from pathlib import Path

import pandas as pd

from macro_engine.decision.historical_models import (
    HistoricalEvidence,
)


CROSS_ASSET_OUTPUT_DIR = Path(
    "research_outputs/cross_asset"
)


def _optional_float(
    value: object,
) -> float | None:
    if pd.isna(value):
        return None

    return float(value)


def load_cross_asset_historical_evidence(
    *,
    asset_key: str,
    environment: str,
    horizon_months: int = 3,
) -> tuple[HistoricalEvidence, ...]:
    file_path = (
        CROSS_ASSET_OUTPUT_DIR
        / asset_key
        / f"{asset_key}_environment_history.csv"
    )

    if not file_path.exists():
        return ()

    data = pd.read_csv(file_path)

    environment_column = "us_environment"
    outcome_column = (
        f"forward_outcome_{horizon_months}m"
    )

    required_columns = {
        environment_column,
        outcome_column,
    }

    missing_columns = (
        required_columns.difference(data.columns)
    )

    if missing_columns:
        missing = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            f"{asset_key} historical data is missing "
            f"required columns: {missing}"
        )

    matches = data.loc[
        data[environment_column] == environment
    ].copy()

    if matches.empty:
        return ()

    returns = pd.to_numeric(
        matches[outcome_column],
        errors="coerce",
    ).dropna()

    if returns.empty:
        return ()

    observations = len(returns)

    evidence = HistoricalEvidence(
        source="US environment history",
        label=environment,
        observations=observations,
        average_return=_optional_float(
            returns.mean()
        ),
        median_return=_optional_float(
            returns.median()
        ),
        up_rate=_optional_float(
            (returns > 0).mean()
        ),
        down_rate=_optional_float(
            (returns < 0).mean()
        ),
    )

    return (evidence,)