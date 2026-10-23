"""Tests for UK Growth production pipelines."""

from macro_engine.pipelines.uk_growth import (
    run_uk_economic_activity,
    run_uk_forward_looking,
    run_uk_household_demand,
    run_uk_industrial_activity,
)


def test_run_uk_economic_activity():
    result = run_uk_economic_activity()

    assert result.bucket_id == "uk_economic_activity"
    assert result.name == "Economic Activity"
    assert result.economy == "United Kingdom"
    assert result.pillar == "growth"
    assert result.indicators_used == 2
    assert len(result.indicator_results) == 2
    assert result.diagnostics["missing_indicator_ids"] == []


def test_run_uk_household_demand():
    result = run_uk_household_demand()

    assert result.bucket_id == "uk_household_demand"
    assert result.name == "Household Demand"
    assert result.economy == "United Kingdom"
    assert result.pillar == "growth"
    assert result.indicators_used == 1
    assert len(result.indicator_results) == 1
    assert result.diagnostics["missing_indicator_ids"] == []


def test_run_uk_industrial_activity():
    result = run_uk_industrial_activity()

    assert result.bucket_id == "uk_industrial_activity"
    assert result.name == "Industrial Activity"
    assert result.economy == "United Kingdom"
    assert result.pillar == "growth"
    assert result.indicators_used == 1
    assert len(result.indicator_results) == 1
    assert result.diagnostics["missing_indicator_ids"] == []


def test_run_uk_forward_looking():
    result = run_uk_forward_looking()

    assert result.bucket_id == "uk_forward_looking"
    assert result.name == "Forward Looking"
    assert result.economy == "United Kingdom"
    assert result.pillar == "growth"
    assert result.indicators_used == 1
    assert len(result.indicator_results) == 1
    assert result.diagnostics["missing_indicator_ids"] == []

# Model-contract tests use synthetic source observations; live providers are tested separately.
import pytest
pytestmark = pytest.mark.usefixtures("synthetic_pipeline_data")
