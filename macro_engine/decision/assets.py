from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from macro_engine.decision.workspace import (
    DecisionWorkspaceResult,
    build_eurusd_workspace,
    build_gbpusd_workspace,
)

WorkspaceBuilder = Callable[[int], DecisionWorkspaceResult]


@dataclass(frozen=True)
class DecisionAsset:
    key: str
    display_name: str
    asset_class: str
    default_horizon_months: int
    builder: WorkspaceBuilder


ASSET_REGISTRY: dict[str, DecisionAsset] = {
    "gbpusd": DecisionAsset(
        key="gbpusd",
        display_name="GBP/USD",
        asset_class="FX",
        default_horizon_months=3,
        builder=build_gbpusd_workspace,
    ),
    
    "eurusd": DecisionAsset(
        key="eurusd",
        display_name="EUR/USD",
        asset_class="FX",
        default_horizon_months=3,
        builder=build_eurusd_workspace,
    ),
}


def get_available_assets() -> tuple[DecisionAsset, ...]:
    return tuple(ASSET_REGISTRY.values())


def get_asset(asset_key: str) -> DecisionAsset:
    try:
        return ASSET_REGISTRY[asset_key]
    except KeyError as exc:
        available = ", ".join(ASSET_REGISTRY)
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

    return asset.builder(resolved_horizon)