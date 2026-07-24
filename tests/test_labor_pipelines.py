"""Tests for US labor bucket pipelines."""

from unittest.mock import patch

import pandas as pd

from macro_engine.pipelines.labor import (
    run_usa_employment_conditions,
    run_usa_labor_demand,
    run_usa_labor_supply,
)


def make_test_data() -> pd.DataFrame:
    """Create sufficient monthly history for indicator-engine tests."""

    dates = pd.date_range(
        start="2015-01-31",
        periods=120,
        freq="ME",
    )

    values = [
        100.0 + index
        for index in range(len(dates))
    ]

    return pd.DataFrame(
        {
            "date": dates,
            "value": values,
        }
    )


def test_run_usa_labor_demand_returns_valid_bucket() -> None:
    result = run_usa_labor_demand()

    assert result.bucket_id == "usa_labor_demand"
    assert result.pillar == "labor"
    assert result.economy == "USA"
    assert result.indicators_used == 2
    assert result.is_valid


@patch(
    "macro_engine.pipelines.labor."
    "get_usa_quits_rate_data"
)
@patch(
    "macro_engine.pipelines.labor."
    "get_usa_jolts_job_openings_data"
)
def test_labor_demand_calls_each_loader_once(
    mock_job_openings,
    mock_quits_rate,
) -> None:
    test_data = make_test_data()

    mock_job_openings.return_value = test_data
    mock_quits_rate.return_value = test_data

    result = run_usa_labor_demand()

    mock_job_openings.assert_called_once_with()
    mock_quits_rate.assert_called_once_with()

    assert result.indicators_used == 2
    assert result.is_valid

def test_run_usa_employment_conditions_returns_valid_bucket() -> None:
    result = run_usa_employment_conditions()

    assert result.bucket_id == "usa_employment_conditions"
    assert result.pillar == "labor"
    assert result.economy == "USA"
    assert result.indicators_used == 3
    assert result.is_valid
    
@patch(
    "macro_engine.pipelines.labor."
    "get_usa_initial_jobless_claims_4wk_average_data"
)
@patch(
    "macro_engine.pipelines.labor."
    "get_usa_unemployment_rate_data"
)
@patch(
    "macro_engine.pipelines.labor."
    "get_usa_nfp_3m_average_data"
)
def test_employment_conditions_calls_each_loader_once(
    mock_nfp,
    mock_unemployment,
    mock_claims,
) -> None:
    test_data = make_test_data()

    mock_nfp.return_value = test_data
    mock_unemployment.return_value = test_data
    mock_claims.return_value = test_data

    result = run_usa_employment_conditions()

    mock_nfp.assert_called_once_with()
    mock_unemployment.assert_called_once_with()
    mock_claims.assert_called_once_with()

    assert result.indicators_used == 3
    assert result.is_valid
    
def test_run_usa_labor_supply_returns_valid_bucket() -> None:
    result = run_usa_labor_supply()

    assert result.bucket_id == "usa_labor_supply"
    assert result.pillar == "labor"
    assert result.economy == "USA"
    assert result.indicators_used == 3
    assert result.is_valid
    
@patch(
    "macro_engine.pipelines.labor."
    "get_usa_employment_population_ratio_data"
)
@patch(
    "macro_engine.pipelines.labor."
    "get_usa_prime_age_labor_force_participation_data"
)
@patch(
    "macro_engine.pipelines.labor."
    "get_usa_labor_force_participation_data"
)
def test_labor_supply_calls_each_loader_once(
    mock_lfpr,
    mock_prime_age,
    mock_emp_pop,
) -> None:
    test_data = make_test_data()

    mock_lfpr.return_value = test_data
    mock_prime_age.return_value = test_data
    mock_emp_pop.return_value = test_data

    result = run_usa_labor_supply()

    mock_lfpr.assert_called_once_with()
    mock_prime_age.assert_called_once_with()
    mock_emp_pop.assert_called_once_with()

    assert result.indicators_used == 3
    assert result.is_valid