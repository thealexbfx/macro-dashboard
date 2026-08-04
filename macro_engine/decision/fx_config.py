from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FXDecisionConfig:
    key: str
    display_name: str
    ticker: str

    base_name: str
    quote_name: str

    base_environment_cache: str
    quote_environment_cache: str

    historical_primary_name: str
    historical_secondary_name: str

    default_horizon_months: int = 3


FX_CONFIGS: dict[str, FXDecisionConfig] = {
    "gbpusd": FXDecisionConfig(
        key="gbpusd",
        display_name="GBP/USD",
        ticker="GBPUSD=X",
        base_name="United Kingdom",
        quote_name="United States",
        base_environment_cache="uk_environment",
        quote_environment_cache="usa_environment",
        historical_primary_name="US",
        historical_secondary_name="UK",
    ),

    "eurusd": FXDecisionConfig(
        key="eurusd",
        display_name="EUR/USD",
        ticker="EURUSD=X",
        base_name="Euro Area",
        quote_name="United States",
        base_environment_cache="euro_environment",
        quote_environment_cache="usa_environment",
        historical_primary_name="US",
        historical_secondary_name="Euro Area",
    ),
    
    "usdjpy": FXDecisionConfig(
        key="usdjpy",
        display_name="USD/JPY",
        ticker="USDJPY=X",
        base_name="United States",
        quote_name="Japan",
        base_environment_cache="usa_environment",
        quote_environment_cache="japan_environment",
        historical_primary_name="US",
        historical_secondary_name="Japan",
    ),
}


def get_fx_config(
    asset_key: str,
) -> FXDecisionConfig:
    try:
        return FX_CONFIGS[asset_key]

    except KeyError as exc:
        available = ", ".join(
            sorted(FX_CONFIGS)
        )

        raise ValueError(
            f"Unknown FX decision asset: {asset_key}. "
            f"Available FX assets: {available}"
        ) from exc


def get_fx_configs() -> tuple[FXDecisionConfig, ...]:
    return tuple(
        FX_CONFIGS.values()
    )