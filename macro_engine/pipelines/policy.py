from indicators.usa import (
    get_usa_2yr_policy_gap_data,
    get_usa_interest_rate_data,
    get_usa_real_policy_rate_data,
)
from datetime import date

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator

from macro_engine.metadata.buckets import (
    USA_CURRENT_POLICY_STANCE,
    USA_POLICY_EXPECTATIONS,
)

from macro_engine.metadata.usa_policy import (
    USA_POLICY_EXPECTATIONS as USA_POLICY_EXPECTATIONS_INDICATOR,
    USA_POLICY_RATE,
    USA_REAL_POLICY_RATE,
)


def run_usa_current_policy_stance(
    as_of_date: date | None = None,
):
    real_policy_rate_result = run_indicator(
        get_usa_real_policy_rate_data(),
        USA_REAL_POLICY_RATE,
        as_of_date=as_of_date,
    )

    nominal_policy_rate_result = run_indicator(
        get_usa_interest_rate_data(),
        USA_POLICY_RATE,
        as_of_date=as_of_date,
    )

    return run_bucket(
        [
            real_policy_rate_result,
            nominal_policy_rate_result,
        ],
        USA_CURRENT_POLICY_STANCE,
    )


def run_usa_policy_expectations(
    as_of_date: date | None = None,
):
    policy_expectations_result = run_indicator(
        get_usa_2yr_policy_gap_data(),
        USA_POLICY_EXPECTATIONS_INDICATOR,
        as_of_date=as_of_date,
    )

    return run_bucket(
        [policy_expectations_result],
        USA_POLICY_EXPECTATIONS,
    )