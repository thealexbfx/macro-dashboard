from __future__ import annotations

from macro_engine.research.analytics import metadata

from economy_data.usa import USA_ECONOMY_MAP
from economy_data.euro import EURO_ECONOMY_MAP
from economy_data.uk import UK_ECONOMY_MAP
from economy_data.japan import JAPAN_ECONOMY_MAP

from market_data.commodities import COMMODITY_MAP
from market_data.fx import FX_MAP
from market_data.equities import EQUITIES_MAP
from market_data.crypto import CRYPTO_MAP
from market_data.rates_bonds import RATES_BONDS_MAP


def _add_market_map(
    registry: dict,
    market_map: dict,
    group: str,
) -> None:
    for name, config in market_map.items():
        label = f"{group} · {name}"

        if "ticker" in config:
            registry[label] = {
                "name": name,
                "group": group,
                "kind": "ticker",
                "loader": config["ticker"],
                "unit_type": config.get("unit_type", "market_price"),
            }

        elif "data_func" in config:
            registry[label] = {
                "name": name,
                "group": group,
                "kind": "function",
                "loader": config["data_func"],
                "unit_type": config.get(
                    "unit_type",
                    config.get("unit", "market_value"),
                ),
            }


def _add_economy_map(
    registry: dict,
    economy_map: dict,
    country: str,
) -> None:
    for name, config in economy_map.items():
        label = f"{country} · {name}"

        registry[label] = {
            "name": name,
            "group": country,
            "kind": "function",
            "loader": config["data_func"],
            "frequency": config.get("frequency"),
            "unit_type": config.get("unit_type"),
            "unit_label": config.get("unit_label", ""),
            "change_type": config.get("change_type"),
            "compatible_group": config.get("compatible_group"),
        }


def build_comparison_registry() -> dict:
    registry = {}

    # Markets
    _add_market_map(
        registry,
        COMMODITY_MAP,
        "Commodities",
    )

    _add_market_map(
        registry,
        FX_MAP,
        "FX",
    )

    _add_market_map(
        registry,
        EQUITIES_MAP,
        "Equities",
    )

    _add_market_map(
        registry,
        CRYPTO_MAP,
        "Crypto",
    )

    _add_market_map(
        registry,
        RATES_BONDS_MAP,
        "Rates & Bonds",
    )

    # Economies
    _add_economy_map(
        registry,
        USA_ECONOMY_MAP,
        "United States",
    )

    _add_economy_map(
        registry,
        EURO_ECONOMY_MAP,
        "Euro Area",
    )

    _add_economy_map(
        registry,
        UK_ECONOMY_MAP,
        "United Kingdom",
    )

    _add_economy_map(
        registry,
        JAPAN_ECONOMY_MAP,
        "Japan",
    )

    for entry in registry.values():
        source_map = {"Commodities": COMMODITY_MAP, "FX": FX_MAP,
                      "Equities": EQUITIES_MAP, "Crypto": CRYPTO_MAP,
                      "Rates & Bonds": RATES_BONDS_MAP,
                      "United States": USA_ECONOMY_MAP, "Euro Area": EURO_ECONOMY_MAP,
                      "United Kingdom": UK_ECONOMY_MAP, "Japan": JAPAN_ECONOMY_MAP}[entry["group"]]
        config = source_map[entry["name"]]
        for field in ("frequency", "unit_label", "source", "representation", "can_be_nonpositive", "ratio_group", "date_convention", "is_policy_rate", "carry_forward_days"):
            if field in config:
                entry[field] = config[field]
        entry["metadata"] = metadata(entry, entry["name"], entry["group"])
    return registry


COMPARISON_REGISTRY = build_comparison_registry()


def comparison_options() -> list[str]:
    return sorted(COMPARISON_REGISTRY.keys())


def get_comparison_series(label: str) -> dict:
    return COMPARISON_REGISTRY[label]
