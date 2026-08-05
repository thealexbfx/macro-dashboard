from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from macro_engine.decision.fx_config import (
    get_fx_configs,
)
from macro_engine.decision.workspace import (
    DecisionWorkspaceResult,
    build_fx_workspace,
)

from macro_engine.decision.cross_asset.config import (
    get_cross_asset_config,
)
from macro_engine.decision.workspace import (
    DecisionWorkspaceResult,
    build_cross_asset_workspace,
    build_fx_workspace,
)

WorkspaceBuilder = Callable[
    [int],
    DecisionWorkspaceResult,
]


@dataclass(frozen=True)
class DecisionAsset:
    key: str
    display_name: str
    asset_class: str
    default_horizon_months: int
    builder: WorkspaceBuilder


ASSET_REGISTRY: dict[str, DecisionAsset] = {
    config.key: DecisionAsset(
        key=config.key,
        display_name=config.display_name,
        asset_class="FX",
        default_horizon_months=(
            config.default_horizon_months
        ),
        builder=(
            lambda horizon_months,
            asset_key=config.key: build_fx_workspace(
                asset_key=asset_key,
                horizon_months=horizon_months,
            )
        ),
    )
    for config in get_fx_configs()
}

gold_config = get_cross_asset_config(
    "gold"
)

ASSET_REGISTRY["gold"] = DecisionAsset(
    key=gold_config.key,
    display_name=gold_config.display_name,
    asset_class=gold_config.asset_class,
    default_horizon_months=(
        gold_config.default_horizon_months
    ),
    builder=(
        lambda horizon_months: build_cross_asset_workspace(
            asset_key="gold",
            horizon_months=horizon_months,
        )
    ),
)

sp500_config = get_cross_asset_config(
    "sp500"
)

ASSET_REGISTRY["sp500"] = DecisionAsset(
    key=sp500_config.key,
    display_name=sp500_config.display_name,
    asset_class=sp500_config.asset_class,
    default_horizon_months=(
        sp500_config.default_horizon_months
    ),
    builder=(
        lambda horizon_months: build_cross_asset_workspace(
            asset_key="sp500",
            horizon_months=horizon_months,
        )
    ),
)

us10y_config = get_cross_asset_config(
    "us10y"
)

ASSET_REGISTRY["us10y"] = DecisionAsset(
    key=us10y_config.key,
    display_name=us10y_config.display_name,
    asset_class=us10y_config.asset_class,
    default_horizon_months=(
        us10y_config.default_horizon_months
    ),
    builder=(
        lambda horizon_months: build_cross_asset_workspace(
            asset_key="us10y",
            horizon_months=horizon_months,
        )
    ),
)

wti_config = get_cross_asset_config(
    "wti"
)

ASSET_REGISTRY["wti"] = DecisionAsset(
    key=wti_config.key,
    display_name=wti_config.display_name,
    asset_class=wti_config.asset_class,
    default_horizon_months=(
        wti_config.default_horizon_months
    ),
    builder=(
        lambda horizon_months: build_cross_asset_workspace(
            asset_key="wti",
            horizon_months=horizon_months,
        )
    ),
)

dxy_config = get_cross_asset_config(
    "dxy"
)

ASSET_REGISTRY["dxy"] = DecisionAsset(
    key=dxy_config.key,
    display_name=dxy_config.display_name,
    asset_class=dxy_config.asset_class,
    default_horizon_months=(
        dxy_config.default_horizon_months
    ),
    builder=(
        lambda horizon_months: build_cross_asset_workspace(
            asset_key="dxy",
            horizon_months=horizon_months,
        )
    ),
)

def get_available_assets() -> tuple[
    DecisionAsset,
    ...,
]:
    return tuple(
        ASSET_REGISTRY.values()
    )


def get_asset(
    asset_key: str,
) -> DecisionAsset:
    try:
        return ASSET_REGISTRY[asset_key]

    except KeyError as exc:
        available = ", ".join(
            ASSET_REGISTRY
        )

        raise ValueError(
            f"Unknown decision asset: {asset_key}. "
            f"Available assets: {available}"
        ) from exc


def build_workspace(
    asset_key: str,
    horizon_months: int | None = None,
) -> DecisionWorkspaceResult:
    asset = get_asset(asset_key)

    resolved_horizon = (
        horizon_months
        if horizon_months is not None
        else asset.default_horizon_months
    )

    return asset.builder(
        resolved_horizon
    )