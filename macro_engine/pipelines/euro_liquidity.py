"""Production pipelines for Euro Area liquidity buckets."""

from datetime import date

from indicators.euro import (
    get_euro_ecb_balance_sheet_13w_change_data,
    get_euro_m3_yoy_data,
)

from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import (
    EURO_CENTRAL_BANK_LIQUIDITY,
    EURO_MONEY_CONDITIONS,
)
from macro_engine.metadata.euro_liquidity import (
    EURO_ECB_BALANCE_SHEET_13W_CHANGE,
    EURO_M3_YOY,
)
from macro_engine.models.bucket import BucketResult


def run_euro_central_bank_liquidity(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the Euro Area Central Bank Liquidity bucket."""

    indicator_result = run_indicator(
        get_euro_ecb_balance_sheet_13w_change_data(),
        EURO_ECB_BALANCE_SHEET_13W_CHANGE,
        as_of_date=as_of_date,
    )

    return run_bucket(
        [indicator_result],
        EURO_CENTRAL_BANK_LIQUIDITY,
    )


def run_euro_money_conditions(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the Euro Area Money Conditions bucket."""

    indicator_result = run_indicator(
        get_euro_m3_yoy_data(),
        EURO_M3_YOY,
        as_of_date=as_of_date,
    )

    return run_bucket(
        [indicator_result],
        EURO_MONEY_CONDITIONS,
    )