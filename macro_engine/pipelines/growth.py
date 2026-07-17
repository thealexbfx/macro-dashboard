"""Production pipelines for US growth buckets."""

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import (
    USA_HOUSEHOLD_DEMAND,
    USA_INDUSTRIAL_ACTIVITY,
)
from macro_engine.metadata.growth import (
    USA_CAPACITY_UTILIZATION,
    USA_DURABLE_GOODS_ORDERS,
    USA_INDUSTRIAL_PRODUCTION,
    USA_PERSONAL_INCOME,
    USA_REAL_PERSONAL_CONSUMPTION,
    USA_RETAIL_SALES,
)
from macro_engine.models.bucket import BucketResult

from indicators.usa import (
    get_usa_capacity_utilization_data,
    get_usa_durable_goods_orders_mom_data,
    get_usa_industrial_production_mom_data,
    get_usa_personal_consumption_mom_data,
    get_usa_personal_income_mom_data,
    get_usa_retail_sales_mom_data,
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