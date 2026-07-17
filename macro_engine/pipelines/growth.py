"""Production pipelines for US growth buckets."""

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import (
    USA_HOUSEHOLD_DEMAND,
    USA_INDUSTRIAL_ACTIVITY,
    USA_HOUSING,
    USA_EMPLOYMENT_MOMENTUM,
)
from macro_engine.metadata.growth import (
    USA_CAPACITY_UTILIZATION,
    USA_DURABLE_GOODS_ORDERS,
    USA_INDUSTRIAL_PRODUCTION,
    USA_PERSONAL_INCOME,
    USA_REAL_PERSONAL_CONSUMPTION,
    USA_RETAIL_SALES,
    USA_BUILDING_PERMITS,
    USA_HOUSING_STARTS,
    USA_NEW_HOME_SALES,
    USA_INITIAL_JOBLESS_CLAIMS,
    USA_JOB_OPENINGS,
    USA_NONFARM_PAYROLLS,
    USA_UNEMPLOYMENT_RATE,
)
from macro_engine.models.bucket import BucketResult

from indicators.usa import (
    get_usa_capacity_utilization_data,
    get_usa_durable_goods_orders_mom_data,
    get_usa_industrial_production_mom_data,
    get_usa_personal_consumption_mom_data,
    get_usa_personal_income_mom_data,
    get_usa_retail_sales_mom_data,
    get_usa_building_permits_data,
    get_usa_housing_starts_data,
    get_usa_new_home_sales_data,
    get_usa_initial_jobless_claims_4wk_average_data,
    get_usa_jolts_job_openings_data,
    get_usa_nfp_3m_average_data,
    get_usa_unemployment_rate_data,
)


def run_usa_household_demand() -> BucketResult:
    """Run the complete US Household Demand bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_personal_consumption_mom_data(),
            USA_REAL_PERSONAL_CONSUMPTION,
        ),
        run_indicator(
            get_usa_retail_sales_mom_data(),
            USA_RETAIL_SALES,
        ),
        run_indicator(
            get_usa_personal_income_mom_data(),
            USA_PERSONAL_INCOME,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_HOUSEHOLD_DEMAND,
    )


def run_usa_industrial_activity() -> BucketResult:
    """Run the complete US Industrial Activity bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_industrial_production_mom_data(),
            USA_INDUSTRIAL_PRODUCTION,
        ),
        run_indicator(
            get_usa_capacity_utilization_data(),
            USA_CAPACITY_UTILIZATION,
        ),
        run_indicator(
            get_usa_durable_goods_orders_mom_data(),
            USA_DURABLE_GOODS_ORDERS,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_INDUSTRIAL_ACTIVITY,
    )
    
def run_usa_housing() -> BucketResult:
    """Run the complete US Housing bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_housing_starts_data(),
            USA_HOUSING_STARTS,
        ),
        run_indicator(
            get_usa_building_permits_data(),
            USA_BUILDING_PERMITS,
        ),
        run_indicator(
            get_usa_new_home_sales_data(),
            USA_NEW_HOME_SALES,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_HOUSING,
    )
    
def run_usa_employment_momentum() -> BucketResult:
    """Run the complete US Employment Momentum bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_nfp_3m_average_data(),
            USA_NONFARM_PAYROLLS,
        ),
        run_indicator(
            get_usa_unemployment_rate_data(),
            USA_UNEMPLOYMENT_RATE,
        ),
        run_indicator(
            get_usa_jolts_job_openings_data(),
            USA_JOB_OPENINGS,
        ),
        run_indicator(
            get_usa_initial_jobless_claims_4wk_average_data(),
            USA_INITIAL_JOBLESS_CLAIMS,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_EMPLOYMENT_MOMENTUM,
    )