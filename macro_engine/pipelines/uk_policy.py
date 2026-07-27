from datetime import date

from indicators.uk import (
    get_uk_bank_rate_monthly_data,
    get_uk_real_policy_rate_data,
)


from macro_engine.engine.pillar_engine import run_pillar
from macro_engine.metadata.pillars import UK_POLICY
from macro_engine.models.pillar import PillarResult
from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import UK_CURRENT_POLICY_STANCE
from macro_engine.metadata.uk_policy import (
    UK_POLICY_RATE,
    UK_REAL_POLICY_RATE,
)
from macro_engine.models.bucket import BucketResult


def run_uk_current_policy_stance(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the UK Current Policy Stance bucket."""

    real_policy_rate_result = run_indicator(
        get_uk_real_policy_rate_data(
            as_of_date=as_of_date,
        ),
        UK_REAL_POLICY_RATE,
        as_of_date=as_of_date,
    )

    nominal_policy_rate_result = run_indicator(
        get_uk_bank_rate_monthly_data(
            as_of_date=as_of_date,
        ),
        UK_POLICY_RATE,
        as_of_date=as_of_date,
    )

    return run_bucket(
        [
            real_policy_rate_result,
            nominal_policy_rate_result,
        ],
        UK_CURRENT_POLICY_STANCE,
    )
    
def run_uk_policy(
    as_of_date: date | None = None,
) -> PillarResult:
    """Run the UK Policy pillar."""

    current_policy_stance = run_uk_current_policy_stance(
        as_of_date=as_of_date,
    )

    return run_pillar(
        [
            current_policy_stance,
        ],
        UK_POLICY,
    )