"""Japan Liquidity pillar bucket pipelines."""

from datetime import date

from indicators.japan import (
    get_japan_boj_balance_sheet_yoy_data,
    get_japan_m3_yoy_data,
)
from macro_engine.metadata.buckets import (
    JAPAN_CENTRAL_BANK_LIQUIDITY,
    JAPAN_MONEY_CONDITIONS,
)
from macro_engine.metadata.japan_liquidity import (
    JAPAN_CENTRAL_BANK_ASSETS,
    JAPAN_M3_GROWTH,
)
from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.models.bucket import BucketResult


def run_japan_central_bank_liquidity(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the Japan Central Bank Liquidity bucket."""

    indicator_results = [
        run_indicator(
            get_japan_boj_balance_sheet_yoy_data(),
            JAPAN_CENTRAL_BANK_ASSETS,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        JAPAN_CENTRAL_BANK_LIQUIDITY,
    )


def run_japan_money_conditions(
    as_of_date: date | None = None,
) -> BucketResult:
    """Execute the Japan Money Conditions bucket."""

    indicator_results = [
        run_indicator(
            get_japan_m3_yoy_data(),
            JAPAN_M3_GROWTH,
            as_of_date=as_of_date,
        ),
    ]

    return run_bucket(
        indicator_results,
        JAPAN_MONEY_CONDITIONS,
    )