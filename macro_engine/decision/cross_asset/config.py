from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CrossAssetDecisionConfig:
    key: str
    display_name: str
    asset_class: str
    ticker: str

    environment_cache: str
    historical_asset_name: str

    default_horizon_months: int = 3


CROSS_ASSET_CONFIGS: dict[
    str,
    CrossAssetDecisionConfig,
] = {
    "gold": CrossAssetDecisionConfig(
        key="gold",
        display_name="Gold",
        asset_class="Commodities",
        ticker="GC=F",
        environment_cache="usa_environment",
        historical_asset_name="Gold",
    ),

    "sp500": CrossAssetDecisionConfig(
        key="sp500",
        display_name="S&P 500",
        asset_class="Equities",
        ticker="^GSPC",
        environment_cache="usa_environment",
        historical_asset_name="S&P 500",
    ),

    "us10y": CrossAssetDecisionConfig(
        key="us10y",
        display_name="US 10Y",
        asset_class="Rates",
        ticker="^TNX",
        environment_cache="usa_environment",
        historical_asset_name="US 10Y",
    ),

    "wti": CrossAssetDecisionConfig(
        key="wti",
        display_name="WTI",
        asset_class="Commodities",
        ticker="CL=F",
        environment_cache="usa_environment",
        historical_asset_name="WTI",
    ),

    "dxy": CrossAssetDecisionConfig(
        key="dxy",
        display_name="DXY",
        asset_class="FX",
        ticker="DX-Y.NYB",
        environment_cache="usa_environment",
        historical_asset_name="DXY",
    ),
}


def get_cross_asset_config(
    asset_key: str,
) -> CrossAssetDecisionConfig:
    try:
        return CROSS_ASSET_CONFIGS[asset_key]

    except KeyError as exc:
        available = ", ".join(
            sorted(CROSS_ASSET_CONFIGS)
        )

        raise ValueError(
            f"Unknown cross-asset decision asset: {asset_key}. "
            f"Available assets: {available}"
        ) from exc


def get_cross_asset_configs() -> tuple[
    CrossAssetDecisionConfig,
    ...,
]:
    return tuple(
        CROSS_ASSET_CONFIGS.values()
    )