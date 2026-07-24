"""Tests for US inflation bucket pipelines."""

from unittest.mock import patch

import pandas as pd

from macro_engine.pipelines.inflation import (
    run_usa_core_inflation_persistence,
    run_usa_headline_price_pressure,
    run_usa_labor_cost_pressure,
    run_usa_producer_pipeline_pressure,
)


def make_test_data() -> pd.DataFrame:
    """Create sufficient monthly history for indicator-engine tests."""
    dates = pd.date_range(
        start="2015-01-31",
        periods=120,
        freq="ME",
    )

    values = [
        2.0 + (index * 0.01)
        for index in range(len(dates))
    ]

    return pd.DataFrame(
        {
            "date": dates,
            "value": values,
        }
    )


def test_run_usa_core_inflation_persistence_returns_valid_bucket() -> None:
    result = run_usa_core_inflation_persistence()

    assert result.bucket_id == "usa_core_inflation_persistence"
    assert result.pillar == "inflation"
    assert result.economy == "USA"
    assert result.indicators_used == 2
    assert result.is_valid


def test_run_usa_headline_price_pressure_returns_valid_bucket() -> None:
    result = run_usa_headline_price_pressure()

    assert result.bucket_id == "usa_headline_price_pressure"
    assert result.pillar == "inflation"
    assert result.economy == "USA"
    assert result.indicators_used == 4
    assert result.is_valid

def test_run_usa_producer_pipeline_pressure_returns_valid_bucket() -> None:
    result = run_usa_producer_pipeline_pressure()

    assert result.bucket_id == "usa_producer_pipeline_pressure"
    assert result.pillar == "inflation"
    assert result.economy == "USA"
    assert result.indicators_used == 4
    assert result.is_valid
    
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_export_prices_yoy_data"
)
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_import_prices_yoy_data"
)
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_core_ppi_yoy_data"
)
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_ppi_yoy_data"
)
def test_producer_pipeline_calls_each_loader_once(
    mock_headline_ppi,
    mock_core_ppi,
    mock_import_prices,
    mock_export_prices,
) -> None:
    test_data = make_test_data()

    mock_headline_ppi.return_value = test_data
    mock_core_ppi.return_value = test_data
    mock_import_prices.return_value = test_data
    mock_export_prices.return_value = test_data

    result = run_usa_producer_pipeline_pressure()

    mock_headline_ppi.assert_called_once_with()
    mock_core_ppi.assert_called_once_with()
    mock_import_prices.assert_called_once_with()
    mock_export_prices.assert_called_once_with()

    assert result.indicators_used == 4
    assert result.is_valid


@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_headline_cpi_3m_annualized_data"
)
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_energy_cpi_yoy_data"
)
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_food_cpi_yoy_data"
)
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_cpi_yoy_data"
)
def test_headline_pipeline_calls_each_loader_once(
    mock_headline_cpi,
    mock_food_cpi,
    mock_energy_cpi,
    mock_headline_momentum,
) -> None:
    test_data = make_test_data()

    mock_headline_cpi.return_value = test_data
    mock_food_cpi.return_value = test_data
    mock_energy_cpi.return_value = test_data
    mock_headline_momentum.return_value = test_data

    result = run_usa_headline_price_pressure()

    mock_headline_cpi.assert_called_once_with()
    mock_headline_momentum.assert_called_once_with()
    mock_food_cpi.assert_called_once_with()
    mock_energy_cpi.assert_called_once_with()

    assert result.indicators_used == 4
    assert result.is_valid
    
def test_run_usa_labor_cost_pressure_returns_valid_bucket() -> None:
    result = run_usa_labor_cost_pressure()

    assert result.bucket_id == "usa_labor_cost_pressure"
    assert result.pillar == "inflation"
    assert result.economy == "USA"
    assert result.indicators_used == 5
    assert result.is_valid
    
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_labor_productivity_data"
)
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_unit_labor_costs_data"
)
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_eci_wages_salaries_yoy_data"
)
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_eci_total_compensation_yoy_data"
)
@patch(
    "macro_engine.pipelines.inflation."
    "get_usa_average_hourly_earnings_yoy_data"
)
def test_labor_cost_pipeline_calls_each_loader_once(
    mock_ahe,
    mock_eci_total,
    mock_eci_wages,
    mock_unit_labor_costs,
    mock_productivity,
) -> None:
    test_data = make_test_data()

    mock_ahe.return_value = test_data
    mock_eci_total.return_value = test_data
    mock_eci_wages.return_value = test_data
    mock_unit_labor_costs.return_value = test_data
    mock_productivity.return_value = test_data

    result = run_usa_labor_cost_pressure()

    mock_ahe.assert_called_once_with()
    mock_eci_total.assert_called_once_with()
    mock_eci_wages.assert_called_once_with()
    mock_unit_labor_costs.assert_called_once_with()
    mock_productivity.assert_called_once_with()

    assert result.indicators_used == 5
    assert result.is_valid