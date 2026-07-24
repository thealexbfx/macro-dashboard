"""Production pipelines for US inflation buckets."""

from datetime import date

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import (
    USA_CORE_INFLATION_PERSISTENCE,
    USA_HEADLINE_PRICE_PRESSURE,
    USA_LABOR_COST_PRESSURE,
    USA_PRODUCER_PIPELINE_PRESSURE,
)
from macro_engine.metadata.inflation import (
    USA_AVERAGE_HOURLY_EARNINGS,
    USA_CORE_CPI,
    USA_CORE_PCE,
    USA_CORE_PPI,
    USA_ECI_TOTAL_COMPENSATION,
    USA_ECI_WAGES_SALARIES,
    USA_ENERGY_CPI,
    USA_EXPORT_PRICES,
    USA_FOOD_CPI,
    USA_HEADLINE_CPI,
    USA_HEADLINE_CPI_3M_ANNUALIZED,
    USA_HEADLINE_PPI,
    USA_IMPORT_PRICES,
    USA_LABOR_PRODUCTIVITY,
    USA_UNIT_LABOR_COSTS,
)
from macro_engine.models.bucket import BucketResult

from indicators.usa import (
    get_usa_average_hourly_earnings_yoy_data,
    get_usa_core_cpi_yoy_data,
    get_usa_core_pce_yoy_data,
    get_usa_core_ppi_yoy_data,
    get_usa_cpi_yoy_data,
    get_usa_eci_total_compensation_yoy_data,
    get_usa_eci_wages_salaries_yoy_data,
    get_usa_energy_cpi_yoy_data,
    get_usa_export_prices_yoy_data,
    get_usa_food_cpi_yoy_data,
    get_usa_headline_cpi_3m_annualized_data,
    get_usa_import_prices_yoy_data,
    get_usa_labor_productivity_data,
    get_usa_ppi_yoy_data,
    get_usa_unit_labor_costs_data,
)


def run_usa_core_inflation_persistence(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Core Inflation Persistence bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_core_cpi_yoy_data(),
            USA_CORE_CPI,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_core_pce_yoy_data(),
            USA_CORE_PCE,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_CORE_INFLATION_PERSISTENCE,
    )


def run_usa_headline_price_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Headline Price Pressure bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_cpi_yoy_data(),
            USA_HEADLINE_CPI,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_headline_cpi_3m_annualized_data(),
            USA_HEADLINE_CPI_3M_ANNUALIZED,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_food_cpi_yoy_data(),
            USA_FOOD_CPI,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_energy_cpi_yoy_data(),
            USA_ENERGY_CPI,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_HEADLINE_PRICE_PRESSURE,
    )


def run_usa_producer_pipeline_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Producer Pipeline Pressure bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_ppi_yoy_data(),
            USA_HEADLINE_PPI,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_core_ppi_yoy_data(),
            USA_CORE_PPI,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_import_prices_yoy_data(),
            USA_IMPORT_PRICES,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_export_prices_yoy_data(),
            USA_EXPORT_PRICES,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_PRODUCER_PIPELINE_PRESSURE,
    )


def run_usa_labor_cost_pressure(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Labor Cost Pressure bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_average_hourly_earnings_yoy_data(),
            USA_AVERAGE_HOURLY_EARNINGS,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_eci_total_compensation_yoy_data(),
            USA_ECI_TOTAL_COMPENSATION,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_eci_wages_salaries_yoy_data(),
            USA_ECI_WAGES_SALARIES,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_unit_labor_costs_data(),
            USA_UNIT_LABOR_COSTS,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_labor_productivity_data(),
            USA_LABOR_PRODUCTIVITY,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_LABOR_COST_PRESSURE,
    )