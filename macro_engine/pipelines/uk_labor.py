"""
Production pipelines for the UK Labor pillar.
"""

from datetime import date

from indicators.uk import (
    get_uk_unemployment_rate_data,
    get_uk_vacancies_data,
)

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.models.bucket import BucketResult

from macro_engine.metadata.buckets import (
    UK_EMPLOYMENT_CONDITIONS,
    UK_LABOR_DEMAND,
)

from macro_engine.metadata.uk_labor import (
    UK_UNEMPLOYMENT_RATE,
    UK_VACANCIES,
)


def run_uk_employment_conditions(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the UK Employment Conditions bucket."""

    indicator_results = (
        run_indicator(
            get_uk_unemployment_rate_data(),
            UK_UNEMPLOYMENT_RATE,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        UK_EMPLOYMENT_CONDITIONS,
    )


def run_uk_labor_demand(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the UK Labor Demand bucket."""

    indicator_results = (
        run_indicator(
            get_uk_vacancies_data(),
            UK_VACANCIES,
            as_of_date=as_of_date,
        ),
    )

    return run_bucket(
        indicator_results,
        UK_LABOR_DEMAND,
    )