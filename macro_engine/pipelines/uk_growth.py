"""Production pipelines for UK growth buckets."""

from datetime import date

from indicators.uk import (
    get_uk_consumer_confidence_data,
    get_uk_gdp_mom_data,
    get_uk_gdp_qoq_data,
    get_uk_industrial_production_mom_data,
    get_uk_retail_sales_mom_data,
)
from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import (
    UK_ECONOMIC_ACTIVITY,
    UK_FORWARD_LOOKING,
    UK_HOUSEHOLD_DEMAND,
    UK_INDUSTRIAL_ACTIVITY,
)
from macro_engine.metadata.uk_growth import (
    UK_CONSUMER_CONFIDENCE,
    UK_GDP_MOM,
    UK_GDP_QOQ,
    UK_INDUSTRIAL_PRODUCTION,
    UK_RETAIL_SALES,
)
from macro_engine.models.bucket import BucketResult


def run_uk_economic_activity(
    as_of_date: date | None = None,
) -> BucketResult:
    """
    Run the complete UK Economic Activity bucket pipeline.
    """

    indicator_results = [
        run_indicator(
            get_uk_gdp_qoq_data(),
            UK_GDP_QOQ,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_uk_gdp_mom_data(),
            UK_GDP_MOM,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        UK_ECONOMIC_ACTIVITY,
    )


def run_uk_household_demand(
    as_of_date: date | None = None,
) -> BucketResult:
    """
    Run the complete UK Household Demand bucket pipeline.
    """

    indicator_results = [
        run_indicator(
            get_uk_retail_sales_mom_data(),
            UK_RETAIL_SALES,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        UK_HOUSEHOLD_DEMAND,
    )


def run_uk_industrial_activity(
    as_of_date: date | None = None,
) -> BucketResult:
    """
    Run the complete UK Industrial Activity bucket pipeline.
    """

    indicator_results = [
        run_indicator(
            get_uk_industrial_production_mom_data(),
            UK_INDUSTRIAL_PRODUCTION,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        UK_INDUSTRIAL_ACTIVITY,
    )


def run_uk_forward_looking(
    as_of_date: date | None = None,
) -> BucketResult:
    """
    Run the complete UK Forward Looking bucket pipeline.
    """

    indicator_results = [
        run_indicator(
            get_uk_consumer_confidence_data(),
            UK_CONSUMER_CONFIDENCE,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        UK_FORWARD_LOOKING,
    )