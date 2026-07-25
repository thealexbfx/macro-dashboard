"""Production pipelines for Euro Area growth buckets."""

from datetime import date

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import (
    EURO_ECONOMIC_ACTIVITY,
    EURO_FORWARD_LOOKING,
    EURO_HOUSEHOLD_DEMAND,
    EURO_INDUSTRIAL_ACTIVITY,
)
from macro_engine.metadata.euro_growth import (
    EURO_ECONOMIC_SENTIMENT,
    EURO_GDP_QOQ,
    EURO_GDP_YOY,
    EURO_INDUSTRIAL_PRODUCTION,
    EURO_RETAIL_SALES,
)
from macro_engine.models.bucket import BucketResult

from indicators.euro import (
    get_euro_economic_sentiment_data,
    get_euro_gdp_qoq_data,
    get_euro_gdp_yoy_data,
    get_euro_industrial_production_mom_data,
    get_euro_retail_sales_mom_data,
)


def run_euro_economic_activity(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete Euro Area Economic Activity bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_euro_gdp_qoq_data(),
            EURO_GDP_QOQ,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_euro_gdp_yoy_data(),
            EURO_GDP_YOY,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        EURO_ECONOMIC_ACTIVITY,
    )


def run_euro_household_demand(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete Euro Area Household Demand bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_euro_retail_sales_mom_data(),
            EURO_RETAIL_SALES,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        EURO_HOUSEHOLD_DEMAND,
    )


def run_euro_industrial_activity(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete Euro Area Industrial Activity bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_euro_industrial_production_mom_data(),
            EURO_INDUSTRIAL_PRODUCTION,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        EURO_INDUSTRIAL_ACTIVITY,
    )


def run_euro_forward_looking(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete Euro Area Forward Looking bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_euro_economic_sentiment_data(),
            EURO_ECONOMIC_SENTIMENT,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        EURO_FORWARD_LOOKING,
    )