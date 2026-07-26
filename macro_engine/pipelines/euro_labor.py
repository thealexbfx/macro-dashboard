"""Production pipelines for Euro Area labor buckets."""

from datetime import date

from indicators.euro import (
    get_euro_total_employment_yoy_data,
    get_euro_unemployment_rate_data,
)
from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import EURO_EMPLOYMENT_CONDITIONS
from macro_engine.metadata.euro_labor import (
    EURO_TOTAL_EMPLOYMENT_YOY,
    EURO_UNEMPLOYMENT_RATE,
)
from macro_engine.models.bucket import BucketResult


def run_euro_employment_conditions(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the Euro Area Employment Conditions bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_euro_total_employment_yoy_data(),
            EURO_TOTAL_EMPLOYMENT_YOY,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_euro_unemployment_rate_data(),
            EURO_UNEMPLOYMENT_RATE,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        EURO_EMPLOYMENT_CONDITIONS,
    )