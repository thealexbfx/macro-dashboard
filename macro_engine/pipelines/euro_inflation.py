"""
Production pipelines for the Euro Area Inflation pillar.
"""

from datetime import date

from indicators.euro import (
    get_euro_core_hicp_yoy_data,
    get_euro_hicp_yoy_data,
    get_euro_interest_rate_data,
    get_euro_labor_productivity_yoy_data,
    get_euro_negotiated_wages_yoy_data,
    get_euro_services_hicp_yoy_data,
)

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.models.bucket import BucketResult

from macro_engine.metadata.buckets import (
    EURO_CORE_INFLATION_PERSISTENCE,
    EURO_HEADLINE_PRICE_PRESSURE,
    EURO_MONETARY_POLICY_PRESSURE,
    EURO_WAGE_COST_PRESSURE,
)

from macro_engine.metadata.euro_inflation import (
    EURO_CORE_HICP,
    EURO_ECB_REFINANCING_RATE,
    EURO_HEADLINE_HICP,
    EURO_LABOR_PRODUCTIVITY,
    EURO_NEGOTIATED_WAGES,
    EURO_SERVICES_HICP,
)


def run_euro_core_inflation_persistence(
    as_of_date: date | None = None,
) -> BucketResult:
    """
    Execute the Euro Area Core Inflation Persistence bucket.
    """

    indicator_results = (
        run_indicator(
            get_euro_core_hicp_yoy_data(),
            EURO_CORE_HICP,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_euro_services_hicp_yoy_data(),
            EURO_SERVICES_HICP,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        EURO_CORE_INFLATION_PERSISTENCE,
    )


def run_euro_headline_price_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """
    Execute the Euro Area Headline Price Pressure bucket.
    """

    indicator_results = (
        run_indicator(
            get_euro_hicp_yoy_data(),
            EURO_HEADLINE_HICP,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        EURO_HEADLINE_PRICE_PRESSURE,
    )


def run_euro_wage_cost_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """
    Execute the Euro Area Wage Cost Pressure bucket.
    """

    indicator_results = (
        run_indicator(
            get_euro_negotiated_wages_yoy_data(),
            EURO_NEGOTIATED_WAGES,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_euro_labor_productivity_yoy_data(),
            EURO_LABOR_PRODUCTIVITY,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        EURO_WAGE_COST_PRESSURE,
    )


def run_euro_monetary_policy_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """
    Execute the Euro Area Monetary Policy Pressure bucket.
    """

    indicator_results = (
        run_indicator(
            get_euro_interest_rate_data(),
            EURO_ECB_REFINANCING_RATE,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        EURO_MONETARY_POLICY_PRESSURE,
    )