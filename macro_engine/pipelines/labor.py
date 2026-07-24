"""Production pipelines for US labor buckets."""
from datetime import date

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator

from macro_engine.metadata.buckets import (
    USA_EMPLOYMENT_CONDITIONS,
    USA_LABOR_DEMAND,
    USA_LABOR_SUPPLY,
)
from macro_engine.metadata.labor import (
    USA_EMPLOYMENT_POPULATION_RATIO,
    USA_INITIAL_JOBLESS_CLAIMS,
    USA_JOB_OPENINGS,
    USA_LABOR_FORCE_PARTICIPATION,
    USA_NONFARM_PAYROLLS,
    USA_PRIME_AGE_PARTICIPATION,
    USA_QUITS_RATE,
    USA_UNEMPLOYMENT_RATE,
)
from macro_engine.models.bucket import BucketResult

from indicators.usa import (
    get_usa_employment_population_ratio_data,
    get_usa_initial_jobless_claims_4wk_average_data,
    get_usa_jolts_job_openings_data,
    get_usa_labor_force_participation_data,
    get_usa_nfp_3m_average_data,
    get_usa_prime_age_labor_force_participation_data,
    get_usa_quits_rate_data,
    get_usa_unemployment_rate_data,
)

def run_usa_employment_conditions(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Employment Conditions bucket pipeline."""

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
            get_usa_initial_jobless_claims_4wk_average_data(),
            USA_INITIAL_JOBLESS_CLAIMS,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_EMPLOYMENT_CONDITIONS,
    )


def run_usa_labor_demand(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Labor Demand bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_jolts_job_openings_data(),
            USA_JOB_OPENINGS,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_quits_rate_data(),
            USA_QUITS_RATE,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_LABOR_DEMAND,
    )


def run_usa_labor_supply(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the complete US Labor Supply bucket pipeline."""

    indicator_results = [
        run_indicator(
            get_usa_labor_force_participation_data(),
            USA_LABOR_FORCE_PARTICIPATION,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_prime_age_labor_force_participation_data(),
            USA_PRIME_AGE_PARTICIPATION,
            as_of_date=as_of_date,
        ),
        run_indicator(
            get_usa_employment_population_ratio_data(),
            USA_EMPLOYMENT_POPULATION_RATIO,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        USA_LABOR_SUPPLY,
    )