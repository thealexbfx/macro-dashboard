"""Deterministic model contracts; real provider checks require --run-live."""

import ast
import importlib
import inspect

import numpy as np
import pandas as pd
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-live",
        action="store_true",
        help="Run real provider smoke tests (network and credentials required).",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-live"):
        for item in items:
            if "live" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(
                        reason="Real provider check: opt in with --run-live."
                    )
                )


@pytest.fixture(autouse=True)
def no_accidental_provider_network(request, monkeypatch):
    if "live" in request.keywords:
        return
    import urllib.request

    import requests

    def blocked(*args, **kwargs):
        raise AssertionError(
            "Offline test attempted provider HTTP. Supply a fixture or mark an explicit live test."
        )

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    monkeypatch.setattr(urllib.request, "urlopen", blocked)


@pytest.fixture
def synthetic_pipeline_data(monkeypatch):
    """Patch only the source boundary; execute real indicator/bucket/pillar engines.

    Read the loader-to-config pair at each run_indicator call so fixture cadence
    follows actual metadata. These data are deliberately synthetic, never evidence.
    Individual tests may still override a loader to test calls or edge cases.
    """
    modules = (
        "growth",
        "inflation",
        "labor",
        "uk_growth",
        "japan_growth",
        "euro_growth",
        "euro_inflation",
        "euro_labor",
        "euro_liquidity",
        "euro_policy",
    )
    aliases = {
        "daily": ("B", 3000),
        "weekly": ("W-FRI", 1000),
        "monthly": ("MS", 360),
        "quarterly": ("QS", 160),
        "annual": ("YS", 50),
    }
    for name in modules:
        module = importlib.import_module(f"macro_engine.pipelines.{name}")
        for node in ast.walk(ast.parse(inspect.getsource(module))):
            if (
                not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Name)
                or node.func.id != "run_indicator"
            ):
                continue
            if (
                len(node.args) < 2
                or not isinstance(node.args[0], ast.Call)
                or not isinstance(node.args[0].func, ast.Name)
                or not isinstance(node.args[1], ast.Name)
            ):
                continue
            loader = node.args[0].func.id
            config = getattr(module, node.args[1].id)
            alias, count = aliases[config.frequency]
            dates = pd.date_range(end="2025-12-31", periods=count, freq=alias)
            values = (
                3 + np.sin(np.arange(len(dates)) / 5) + np.arange(len(dates)) * 0.002
            )
            frame = pd.DataFrame({"date": dates, "value": values})
            monkeypatch.setattr(
                module, loader, lambda frame=frame: frame.copy(deep=True)
            )
