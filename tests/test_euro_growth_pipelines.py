"""Tests for Euro Area growth production pipelines."""

from unittest.mock import patch

import pandas as pd

from macro_engine.pipelines.euro_growth import (
    run_euro_economic_activity,
    run_euro_forward_looking,
    run_euro_household_demand,
    run_euro_industrial_activity,
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


def make_quarterly_data(
    values: list[float],
    start: str = "2000-01-01",
) -> pd.DataFrame:
    """Create deterministic quarterly indicator data."""

    dates = pd.date_range(
        start=start,
        periods=len(values),
        freq="QS",
    )

    return pd.DataFrame(
        {
            "date": dates,
            "value": values,
        }
    )


def make_stable_monthly_series(
    latest_value: float = 1.0,
    observations: int = 240,
) -> pd.DataFrame:
    """Create sufficient monthly history for indicator tests."""

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


def make_stable_quarterly_series(
    latest_value: float = 1.0,
    observations: int = 80,
) -> pd.DataFrame:
    """Create sufficient quarterly history for indicator tests."""

    values = [
        ((index % 16) - 8) / 10
        for index in range(observations)
    ]

    values[-4:] = [
        latest_value - 0.3,
        latest_value - 0.2,
        latest_value - 0.1,
        latest_value,
    ]

    return make_quarterly_data(values)


@patch(
    "macro_engine.pipelines.euro_growth."
    "get_euro_gdp_yoy_data"
)
@patch(
    "macro_engine.pipelines.euro_growth."
    "get_euro_gdp_qoq_data"
)
def test_run_euro_economic_activity_returns_valid_bucket(
    mock_gdp_qoq,
    mock_gdp_yoy,
) -> None:
    mock_gdp_qoq.return_value = make_stable_quarterly_series(0.4)
    mock_gdp_yoy.return_value = make_stable_quarterly_series(1.2)

    result = run_euro_economic_activity()

    assert result.bucket_id == "euro_economic_activity"
    assert result.name == "Economic Activity"
    assert result.economy == "Euro Area"
    assert result.pillar == "growth"
    assert result.indicators_used == 2
    assert len(result.indicator_results) == 2
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
        "euro_gdp_qoq",
        "euro_gdp_yoy",
    }


@patch(
    "macro_engine.pipelines.euro_growth."
    "get_euro_retail_sales_mom_data"
)
def test_run_euro_household_demand_returns_valid_bucket(
    mock_retail_sales,
) -> None:
    mock_retail_sales.return_value = make_stable_monthly_series(0.3)

    result = run_euro_household_demand()

    assert result.bucket_id == "euro_household_demand"
    assert result.name == "Household Demand"
    assert result.economy == "Euro Area"
    assert result.pillar == "growth"
    assert result.indicators_used == 1
    assert len(result.indicator_results) == 1
    assert result.is_valid

    indicator_ids = {
        indicator.indicator_id
        for indicator in result.indicator_results
    }

    assert indicator_ids == {
        "euro_retail_sales",
    }


@patch(
    "macro_engine.pipelines.euro_growth."
    "get_euro_industrial_production_mom_data"
)
def test_run_euro_industrial_activity_returns_valid_bucket(
    mock_industrial_production,
) -> None:
    mock_industrial_production.return_value = (
        make_stable_monthly_series(0.2)
    )

    result = run_euro_industrial_activity()

    assert result.bucket_id == "euro_industrial_activity"
    assert result.name == "Industrial Activity"
    assert result.economy == "Euro Area"
    assert result.pillar == "growth"
    assert result.indicators_used == 1
    assert len(result.indicator_results) == 1
    assert result.is_valid

    indicator_ids = {
        indicator.indicator_id
        for indicator in result.indicator_results
    }

    assert indicator_ids == {
        "euro_industrial_production",
    }


@patch(
    "macro_engine.pipelines.euro_growth."
    "get_euro_economic_sentiment_data"
)
def test_run_euro_forward_looking_returns_valid_bucket(
    mock_sentiment,
) -> None:
    mock_sentiment.return_value = make_stable_monthly_series(101.0)

    result = run_euro_forward_looking()

    assert result.bucket_id == "euro_forward_looking"
    assert result.name == "Forward Looking"
    assert result.economy == "Euro Area"
    assert result.pillar == "growth"
    assert result.indicators_used == 1
    assert len(result.indicator_results) == 1
    assert result.is_valid

    indicator_ids = {
        indicator.indicator_id
        for indicator in result.indicator_results
    }

    assert indicator_ids == {
        "euro_economic_sentiment",
    }


@patch(
    "macro_engine.pipelines.euro_growth."
    "get_euro_gdp_yoy_data"
)
@patch(
    "macro_engine.pipelines.euro_growth."
    "get_euro_gdp_qoq_data"
)
def test_euro_economic_activity_calls_each_loader_once(
    mock_gdp_qoq,
    mock_gdp_yoy,
) -> None:
    data = make_stable_quarterly_series()

    mock_gdp_qoq.return_value = data
    mock_gdp_yoy.return_value = data

    run_euro_economic_activity()

    mock_gdp_qoq.assert_called_once_with()
    mock_gdp_yoy.assert_called_once_with()