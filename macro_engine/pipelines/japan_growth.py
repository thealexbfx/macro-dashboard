"""Production pipelines for Japan growth buckets."""

from datetime import date

from indicators.japan import (
    get_japan_economy_watchers_survey_data,
    get_japan_gdp_qoq_data,
    get_japan_industrial_production_mom_data,
    get_japan_retail_sales_mom_data,
)
from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import (
    JAPAN_ECONOMIC_ACTIVITY,
    JAPAN_FORWARD_LOOKING,
    JAPAN_HOUSEHOLD_DEMAND,
    JAPAN_INDUSTRIAL_ACTIVITY,
)
from macro_engine.metadata.japan_growth import (
    JAPAN_ECONOMY_WATCHERS,
    JAPAN_GDP_QOQ,
    JAPAN_INDUSTRIAL_PRODUCTION,
    JAPAN_RETAIL_SALES,
)
from macro_engine.models.bucket import BucketResult


def run_japan_economic_activity(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete Japan Economic Activity bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_japan_gdp_qoq_data(),
            JAPAN_GDP_QOQ,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        JAPAN_ECONOMIC_ACTIVITY,
    )


def run_japan_household_demand(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete Japan Household Demand bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_japan_retail_sales_mom_data(),
            JAPAN_RETAIL_SALES,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        JAPAN_HOUSEHOLD_DEMAND,
    )


def run_japan_industrial_activity(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete Japan Industrial Activity bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_japan_industrial_production_mom_data(),
            JAPAN_INDUSTRIAL_PRODUCTION,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        JAPAN_INDUSTRIAL_ACTIVITY,
    )


def run_japan_forward_looking(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete Japan Forward Looking bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_japan_economy_watchers_survey_data(),
            JAPAN_ECONOMY_WATCHERS,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        JAPAN_FORWARD_LOOKING,
    )