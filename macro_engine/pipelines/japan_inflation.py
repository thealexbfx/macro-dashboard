"""
Production pipelines for the Japan Inflation pillar.
"""

from datetime import date

from indicators.japan import (
    get_japan_core_cpi_yoy_data,
    get_japan_cpi_yoy_data,
    get_japan_tokyo_core_cpi_yoy_data,
    get_japan_tokyo_cpi_yoy_data,
    get_japan_wage_growth_data,
)

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.models.bucket import BucketResult

from macro_engine.metadata.buckets import (
    JAPAN_CORE_INFLATION_PERSISTENCE,
    JAPAN_HEADLINE_PRICE_PRESSURE,
    JAPAN_WAGE_COST_PRESSURE,
)

from macro_engine.metadata.japan_inflation import (
    JAPAN_CORE_CPI,
    JAPAN_CPI,
    JAPAN_TOKYO_CORE_CPI,
    JAPAN_TOKYO_CPI,
    JAPAN_WAGE_GROWTH,
)


def run_japan_core_inflation_persistence(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the Japan Core Inflation Persistence bucket."""

    indicator_results = (
        run_indicator(
            get_japan_core_cpi_yoy_data(),
            JAPAN_CORE_CPI,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_japan_tokyo_core_cpi_yoy_data(),
            JAPAN_TOKYO_CORE_CPI,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        JAPAN_CORE_INFLATION_PERSISTENCE,
    )


def run_japan_headline_price_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the Japan Headline Price Pressure bucket."""

    indicator_results = (
        run_indicator(
            get_japan_cpi_yoy_data(),
            JAPAN_CPI,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_japan_tokyo_cpi_yoy_data(),
            JAPAN_TOKYO_CPI,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        JAPAN_HEADLINE_PRICE_PRESSURE,
    )


def run_japan_wage_cost_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the Japan Wage Cost Pressure bucket."""

    indicator_results = (
        run_indicator(
            get_japan_wage_growth_data(),
            JAPAN_WAGE_GROWTH,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        JAPAN_WAGE_COST_PRESSURE,
    )