"""
Production pipelines for the Japan Labor pillar.
"""

from datetime import date

from indicators.japan import (
    get_japan_unemployment_rate_data,
    get_japan_wage_growth_data,
)

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.models.bucket import BucketResult

from macro_engine.metadata.buckets import (
    JAPAN_EMPLOYMENT_CONDITIONS,
    JAPAN_LABOR_DEMAND,
)

from macro_engine.metadata.japan_labor import (
    JAPAN_LABOR_WAGE_GROWTH,
    JAPAN_UNEMPLOYMENT_RATE,
)


def run_japan_employment_conditions(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the Japan Employment Conditions bucket."""

    indicator_results = (
        run_indicator(
            get_japan_unemployment_rate_data(),
            JAPAN_UNEMPLOYMENT_RATE,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        JAPAN_EMPLOYMENT_CONDITIONS,
    )


def run_japan_labor_demand(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the Japan Labor Demand bucket."""

    indicator_results = (
        run_indicator(
            get_japan_wage_growth_data(),
            JAPAN_LABOR_WAGE_GROWTH,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        JAPAN_LABOR_DEMAND,
    )