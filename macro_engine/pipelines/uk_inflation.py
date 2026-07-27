"""
Production pipelines for the UK Inflation pillar.
"""

from datetime import date
import pandas as pd

from indicators.uk import (
    get_uk_average_weekly_earnings_yoy_data,
    get_uk_core_cpi_yoy_data,
    get_uk_cpi_yoy_data,
    get_uk_interest_rate_data,
    get_uk_services_cpi_yoy_data,
    get_uk_bank_rate_monthly_data,
)

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.models.bucket import BucketResult

from macro_engine.metadata.buckets import (
    UK_CORE_INFLATION_PERSISTENCE,
    UK_HEADLINE_PRICE_PRESSURE,
    UK_MONETARY_POLICY_PRESSURE,
    UK_WAGE_COST_PRESSURE,
)

from macro_engine.metadata.uk_inflation import (
    UK_AVERAGE_WEEKLY_EARNINGS,
    UK_BANK_RATE,
    UK_CORE_CPI,
    UK_CPI,
    UK_SERVICES_CPI,
)

def run_uk_core_inflation_persistence(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the UK Core Inflation Persistence bucket."""

    indicator_results = (
        run_indicator(
            get_uk_core_cpi_yoy_data(),
            UK_CORE_CPI,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_uk_services_cpi_yoy_data(),
            UK_SERVICES_CPI,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        UK_CORE_INFLATION_PERSISTENCE,
    )


def run_uk_headline_price_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the UK Headline Price Pressure bucket."""

    indicator_results = (
        run_indicator(
            get_uk_cpi_yoy_data(),
            UK_CPI,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        UK_HEADLINE_PRICE_PRESSURE,
    )


def run_uk_wage_cost_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the UK Wage Cost Pressure bucket."""

    indicator_results = (
        run_indicator(
            get_uk_average_weekly_earnings_yoy_data(),
            UK_AVERAGE_WEEKLY_EARNINGS,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        UK_WAGE_COST_PRESSURE,
    )


def run_uk_monetary_policy_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the UK Monetary Policy Pressure bucket."""

    indicator_results = (
        run_indicator(
            get_uk_bank_rate_monthly_data(
                as_of_date=as_of_date,
            ),
            UK_BANK_RATE,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        UK_MONETARY_POLICY_PRESSURE,
    )