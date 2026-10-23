"""Tests for japan Growth production pipelines."""

from macro_engine.pipelines.japan_growth import (
    run_japan_economic_activity,
    run_japan_forward_looking,
    run_japan_household_demand,
    run_japan_industrial_activity,
)


def test_run_japan_economic_activity():
    result = run_japan_economic_activity()

    assert result.bucket_id == "japan_economic_activity"
    assert result.name == "Economic Activity"
    assert result.economy == "Japan"
    assert result.pillar == "growth"
    assert result.indicators_used == 1
    assert len(result.indicator_results) == 1
    assert result.diagnostics["missing_indicator_ids"] == []


def test_run_japan_household_demand():
    result = run_japan_household_demand()

    assert result.bucket_id == "japan_household_demand"
    assert result.name == "Household Demand"
    assert result.economy == "Japan"
    assert result.pillar == "growth"
    assert result.indicators_used == 1
    assert len(result.indicator_results) == 1
    assert result.diagnostics["missing_indicator_ids"] == []


def test_run_japan_industrial_activity():
    result = run_japan_industrial_activity()

    assert result.bucket_id == "japan_industrial_activity"
    assert result.name == "Industrial Activity"
    assert result.economy == "Japan"
    assert result.pillar == "growth"
    assert result.indicators_used == 1
    assert len(result.indicator_results) == 1
    assert result.diagnostics["missing_indicator_ids"] == []


def test_run_japan_forward_looking():
    result = run_japan_forward_looking()

    assert result.bucket_id == "japan_forward_looking"
    assert result.name == "Forward Looking"
    assert result.economy == "Japan"
    assert result.pillar == "growth"
    assert result.indicators_used == 1
    assert len(result.indicator_results) == 1
    assert result.diagnostics["missing_indicator_ids"] == []

# Model-contract tests use synthetic source observations; live providers are tested separately.
import pytest
pytestmark = pytest.mark.usefixtures("synthetic_pipeline_data")
