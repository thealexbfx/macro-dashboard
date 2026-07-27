"""Production pipelines for United Kingdom liquidity buckets."""

from datetime import date

from indicators.uk import get_uk_boe_balance_sheet_13w_change_data
from macro_engine.engine.bucket_engine import run_bucket
from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.metadata.buckets import UK_CENTRAL_BANK_LIQUIDITY
from macro_engine.metadata.uk_liquidity import (
    UK_BOE_BALANCE_SHEET_13W_CHANGE,
)
from macro_engine.models.bucket import BucketResult


def run_uk_central_bank_liquidity(
    as_of_date: date | None = None,
) -> BucketResult:
    """Run the United Kingdom Central Bank Liquidity bucket."""

    indicator_result = run_indicator(
        get_uk_boe_balance_sheet_13w_change_data(),
        UK_BOE_BALANCE_SHEET_13W_CHANGE,
        as_of_date=as_of_date,
    )

    return run_bucket(
        [indicator_result],
        UK_CENTRAL_BANK_LIQUIDITY,
    )