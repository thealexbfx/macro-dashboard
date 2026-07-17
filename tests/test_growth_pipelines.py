"""Tests for US growth production pipelines."""

from datetime import date
from unittest.mock import patch

import pandas as pd

from macro_engine.pipelines.growth import (
    run_usa_household_demand,
    run_usa_housing,
    run_usa_industrial_activity,
)


def make_monthly_data(
    values: list[float],
    start: str = "2000-01-01",
) -> pd.DataFrame:
    """Create deterministic monthly indicator data."""

    dates = pd.date_range(
        start=start,
        periods=len(values),
        freq="MS",
    )

    return pd.DataFrame(
        {
            "date": dates,
            "value": values,
        }
    )


def make_stable_series(
    latest_value: float = 1.0,
    observations: int = 240,
) -> pd.DataFrame:
    """Create sufficient deterministic history for indicator tests."""

    values = [
        ((index % 24) - 12) / 20
        for index in range(observations)
    ]

    values[-6:] = [
        latest_value - 0.5,
        latest_value - 0.4,
        latest_value - 0.3,
        latest_value - 0.2,
        latest_value - 0.1,
        latest_value,
    ]

    return make_monthly_data(values)


@patch(
    "macro_engine.pipelines.growth."
    "get_usa_personal_income_mom_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_retail_sales_mom_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_personal_consumption_mom_data"
)
def test_run_usa_household_demand_returns_valid_bucket(
    mock_consumption,
    mock_retail_sales,
    mock_income,
) -> None:
    mock_consumption.return_value = make_stable_series(0.30)
    mock_retail_sales.return_value = make_stable_series(0.40)
    mock_income.return_value = make_stable_series(0.20)

    result = run_usa_household_demand()

    assert result.bucket_id == "usa_household_demand"
    assert result.name == "Household Demand"
    assert result.economy == "USA"
    assert result.pillar == "growth"
    assert result.indicators_used == 3
    assert len(result.indicator_results) == 3
    assert result.is_valid
    assert -1.0 <= result.state_score <= 1.0
    assert -1.0 <= result.trend_score <= 1.0
    assert -1.0 <= result.breadth_score <= 1.0
    assert 0.0 <= result.confidence_score <= 1.0

    indicator_ids = {
        indicator.indicator_id
        for indicator in result.indicator_results
    }

    assert indicator_ids == {
        "usa_real_personal_consumption",
        "usa_retail_sales",
        "usa_personal_income",
    }


@patch(
    "macro_engine.pipelines.growth."
    "get_usa_durable_goods_orders_mom_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_capacity_utilization_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_industrial_production_mom_data"
)
def test_run_usa_industrial_activity_returns_valid_bucket(
    mock_industrial_production,
    mock_capacity_utilization,
    mock_durable_goods,
) -> None:
    mock_industrial_production.return_value = make_stable_series(0.25)
    mock_capacity_utilization.return_value = make_stable_series(76.0)
    mock_durable_goods.return_value = make_stable_series(0.50)

    result = run_usa_industrial_activity()

    assert result.bucket_id == "usa_industrial_activity"
    assert result.name == "Industrial Activity"
    assert result.economy == "USA"
    assert result.pillar == "growth"
    assert result.indicators_used == 3
    assert len(result.indicator_results) == 3
    assert result.is_valid
    assert -1.0 <= result.state_score <= 1.0
    assert -1.0 <= result.trend_score <= 1.0
    assert -1.0 <= result.breadth_score <= 1.0
    assert 0.0 <= result.confidence_score <= 1.0

    indicator_ids = {
        indicator.indicator_id
        for indicator in result.indicator_results
    }

    assert indicator_ids == {
        "usa_industrial_production",
        "usa_capacity_utilization",
        "usa_durable_goods_orders",
    }

@patch(
    "macro_engine.pipelines.growth."
    "get_usa_new_home_sales_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_building_permits_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_housing_starts_data"
)
def test_run_usa_housing_returns_valid_bucket(
    mock_housing_starts,
    mock_building_permits,
    mock_new_home_sales,
) -> None:
    mock_housing_starts.return_value = make_stable_series(1400.0)
    mock_building_permits.return_value = make_stable_series(1450.0)
    mock_new_home_sales.return_value = make_stable_series(650.0)

    result = run_usa_housing()

    assert result.bucket_id == "usa_housing"
    assert result.name == "Housing"
    assert result.economy == "USA"
    assert result.pillar == "growth"
    assert result.indicators_used == 3
    assert len(result.indicator_results) == 3
    assert result.is_valid

    assert -1.0 <= result.state_score <= 1.0
    assert -1.0 <= result.trend_score <= 1.0
    assert -1.0 <= result.breadth_score <= 1.0
    assert 0.0 <= result.confidence_score <= 1.0

    indicator_ids = {
        indicator.indicator_id
        for indicator in result.indicator_results
    }

    assert indicator_ids == {
        "usa_housing_starts",
        "usa_building_permits",
        "usa_new_home_sales",
    }

@patch(
    "macro_engine.pipelines.growth."
    "get_usa_personal_income_mom_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_retail_sales_mom_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_personal_consumption_mom_data"
)
def test_household_pipeline_calls_each_loader_once(
    mock_consumption,
    mock_retail_sales,
    mock_income,
) -> None:
    data = make_stable_series()

    mock_consumption.return_value = data
    mock_retail_sales.return_value = data
    mock_income.return_value = data

    run_usa_household_demand()

    mock_consumption.assert_called_once_with()
    mock_retail_sales.assert_called_once_with()
    mock_income.assert_called_once_with()


@patch(
    "macro_engine.pipelines.growth."
    "get_usa_durable_goods_orders_mom_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_capacity_utilization_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_industrial_production_mom_data"
)
def test_industrial_pipeline_calls_each_loader_once(
    mock_industrial_production,
    mock_capacity_utilization,
    mock_durable_goods,
) -> None:
    data = make_stable_series()

    mock_industrial_production.return_value = data
    mock_capacity_utilization.return_value = data
    mock_durable_goods.return_value = data

    run_usa_industrial_activity()

    mock_industrial_production.assert_called_once_with()
    mock_capacity_utilization.assert_called_once_with()
    mock_durable_goods.assert_called_once_with()
    
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_new_home_sales_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_building_permits_data"
)
@patch(
    "macro_engine.pipelines.growth."
    "get_usa_housing_starts_data"
)
def test_housing_pipeline_calls_each_loader_once(
    mock_housing_starts,
    mock_building_permits,
    mock_new_home_sales,
) -> None:
    data = make_stable_series()

    mock_housing_starts.return_value = data
    mock_building_permits.return_value = data
    mock_new_home_sales.return_value = data

    run_usa_housing()

    mock_housing_starts.assert_called_once_with()
    mock_building_permits.assert_called_once_with()
    mock_new_home_sales.assert_called_once_with()