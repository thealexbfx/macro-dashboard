"""Japan Policy pillar bucket pipelines."""

from datetime import date

from indicators.japan import get_japan_interest_rate_data

from macro_engine.metadata.buckets import (
    JAPAN_CURRENT_POLICY_STANCE,
)

from macro_engine.metadata.japan_policy import (
    JAPAN_POLICY_RATE,
)

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.models.bucket import BucketResult

def run_japan_current_policy_stance(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the Japan Current Policy Stance bucket."""

    indicator_results = [
        run_indicator(
            get_japan_interest_rate_data(),
            JAPAN_POLICY_RATE,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        JAPAN_CURRENT_POLICY_STANCE,
    )