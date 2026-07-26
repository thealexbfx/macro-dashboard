from datetime import date

from indicators.euro import (
    get_euro_policy_rate_monthly_data,
    get_euro_real_policy_rate_data,
)

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator

from macro_engine.metadata.buckets import (
    EURO_CURRENT_POLICY_STANCE,
)

from macro_engine.metadata.euro_policy import (
    EURO_POLICY_RATE,
    EURO_REAL_POLICY_RATE,
)

from macro_engine.models.bucket import BucketResult


def run_euro_current_policy_stance(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the Euro Area Current Policy Stance bucket."""

    real_policy_rate_result = run_indicator(
        get_euro_real_policy_rate_data(),
        EURO_REAL_POLICY_RATE,
        as_of_date=as_of_date,
    )

    nominal_policy_rate_result = run_indicator(
        get_euro_policy_rate_monthly_data(),
        EURO_POLICY_RATE,
        as_of_date=as_of_date,
    )

    return run_bucket(
        [
            real_policy_rate_result,
            nominal_policy_rate_result,
        ],
        EURO_CURRENT_POLICY_STANCE,
    )