from indicators.usa import (
    get_usa_chicago_fed_nfci_data,
    get_usa_net_fed_liquidity_13w_change_data,
    get_usa_reserve_balances_13w_change_data,
    get_usa_m2_yoy_data,
)

from datetime import date

from macro_engine.engine.indicator_engine import run_indicator
from macro_engine.engine.bucket_engine import run_bucket

from macro_engine.metadata.usa_liquidity import (
    USA_CHICAGO_FED_NFCI,
    USA_NET_FED_LIQUIDITY_13W_CHANGE,
    USA_RESERVE_BALANCES_13W_CHANGE,
    USA_M2_YOY,
)

from macro_engine.metadata.buckets import (
    USA_CENTRAL_BANK_LIQUIDITY_BUCKET,
    USA_FUNDING_CONDITIONS,
    USA_MONEY_CONDITIONS,
)


def run_usa_central_bank_liquidity(
    as_of_date: date | None = None,
):
    net_liquidity_result = run_indicator(
        get_usa_net_fed_liquidity_13w_change_data(),
        USA_NET_FED_LIQUIDITY_13W_CHANGE,
        as_of_date=as_of_date,
    )

    reserve_balances_result = run_indicator(
        get_usa_reserve_balances_13w_change_data(),
        USA_RESERVE_BALANCES_13W_CHANGE,
        as_of_date=as_of_date,
    )

    return run_bucket(
        [
            reserve_balances_result,
            net_liquidity_result,
        ],
        USA_CENTRAL_BANK_LIQUIDITY_BUCKET,
    )
    
def run_usa_money_conditions(
    as_of_date: date | None = None,
):
    m2_result = run_indicator(
        get_usa_m2_yoy_data(),
        USA_M2_YOY,
        as_of_date=as_of_date,
    )

    return run_bucket(
        [m2_result],
        USA_MONEY_CONDITIONS,
    )
    
def run_usa_funding_conditions(
    as_of_date: date | None = None,
):
    nfci_result = run_indicator(
        get_usa_chicago_fed_nfci_data(),
        USA_CHICAGO_FED_NFCI,
        as_of_date=as_of_date,
    )

    return run_bucket(
        [nfci_result],
        USA_FUNDING_CONDITIONS,
    )