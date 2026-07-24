"""Production pipelines for US growth buckets."""

from datetime import date

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import (
    USA_EMPLOYMENT_MOMENTUM,
    USA_HOUSEHOLD_DEMAND,
    USA_HOUSING,
    USA_INDUSTRIAL_ACTIVITY,
)
from macro_engine.metadata.growth import (
    USA_BUILDING_PERMITS,
    USA_CAPACITY_UTILIZATION,
    USA_DURABLE_GOODS_ORDERS,
    USA_HOUSING_STARTS,
    USA_INITIAL_JOBLESS_CLAIMS,
    USA_INDUSTRIAL_PRODUCTION,
    USA_JOB_OPENINGS,
    USA_NEW_HOME_SALES,
    USA_NONFARM_PAYROLLS,
    USA_PERSONAL_INCOME,
    USA_REAL_PERSONAL_CONSUMPTION,
    USA_RETAIL_SALES,
    USA_UNEMPLOYMENT_RATE,
)
from macro_engine.models.bucket import BucketResult

from indicators.usa import (
    get_usa_building_permits_data,
    get_usa_capacity_utilization_data,
    get_usa_durable_goods_orders_mom_data,
    get_usa_housing_starts_data,
    get_usa_initial_jobless_claims_4wk_average_data,
    get_usa_industrial_production_mom_data,
    get_usa_jolts_job_openings_data,
    get_usa_new_home_sales_data,
    get_usa_nfp_3m_average_data,
    get_usa_personal_consumption_mom_data,
    get_usa_personal_income_mom_data,
    get_usa_retail_sales_mom_data,
    get_usa_unemployment_rate_data,
)


def run_usa_household_demand(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Household Demand bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_personal_consumption_mom_data(),
            USA_REAL_PERSONAL_CONSUMPTION,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_retail_sales_mom_data(),
            USA_RETAIL_SALES,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_personal_income_mom_data(),
            USA_PERSONAL_INCOME,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_HOUSEHOLD_DEMAND,
    )


def run_usa_industrial_activity(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Industrial Activity bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_industrial_production_mom_data(),
            USA_INDUSTRIAL_PRODUCTION,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_capacity_utilization_data(),
            USA_CAPACITY_UTILIZATION,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_durable_goods_orders_mom_data(),
            USA_DURABLE_GOODS_ORDERS,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_INDUSTRIAL_ACTIVITY,
    )


def run_usa_housing(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Housing bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_housing_starts_data(),
            USA_HOUSING_STARTS,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_building_permits_data(),
            USA_BUILDING_PERMITS,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_new_home_sales_data(),
            USA_NEW_HOME_SALES,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_HOUSING,
    )


def run_usa_employment_momentum(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Employment Momentum bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_nfp_3m_average_data(),
            USA_NONFARM_PAYROLLS,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_unemployment_rate_data(),
            USA_UNEMPLOYMENT_RATE,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_jolts_job_openings_data(),
            USA_JOB_OPENINGS,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_initial_jobless_claims_4wk_average_data(),
            USA_INITIAL_JOBLESS_CLAIMS,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_EMPLOYMENT_MOMENTUM,
    )