from __future__ import annotations

from macro_engine.decision.historical_engine import (
    load_historical_evidence,
)
from macro_engine.decision.historical_models import (
    HistoricalEvidence,
)


def load_gbpusd_historical_evidence(
    *,
    us_environment: str,
    uk_environment: str,
    horizon_months: int = 3,
) -> tuple[HistoricalEvidence, ...]:
    return load_historical_evidence(
        asset_key="gbpusd",
        primary_environment=us_environment,
        secondary_environment=uk_environment,
        horizon_months=horizon_months,
    )


def load_eurusd_historical_evidence(
    *,
    us_environment: str,
    euro_environment: str,
    horizon_months: int = 3,
) -> tuple[HistoricalEvidence, ...]:
    return load_historical_evidence(
        asset_key="eurusd",
        primary_environment=us_environment,
        secondary_environment=euro_environment,
        horizon_months=horizon_months,
    )