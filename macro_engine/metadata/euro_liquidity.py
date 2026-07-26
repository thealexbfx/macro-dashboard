"""Indicator metadata for the Euro Area Liquidity pillar."""

from macro_engine.models.indicator import IndicatorConfig


EURO_ECB_BALANCE_SHEET_13W_CHANGE = IndicatorConfig(
    indicator_id="euro_ecb_balance_sheet_13w_change",
    name="ECB Balance Sheet 13W Change",
    economy="Euro Area",
    pillar="liquidity",
    bucket="central_bank_liquidity",
    frequency="weekly",
    economic_direction="positive",
    state_window=4,
    trend_window=4,
    historical_lookback=520,
    minimum_history=104,
    source="ECB",
    unit="millions of euros",
    description=(
        "Thirteen-week change in the consolidated balance sheet of the "
        "Eurosystem. Positive values indicate balance-sheet expansion, while "
        "negative values indicate central-bank liquidity withdrawal."
    ),
)


EURO_M3_YOY = IndicatorConfig(
    indicator_id="euro_m3_yoy",
    name="M3 Annual Growth",
    economy="Euro Area",
    pillar="liquidity",
    bucket="money_conditions",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    historical_lookback=240,
    minimum_history=60,
    source="ECB",
    unit="percent",
    description=(
        "Annual growth rate of the Euro Area broad monetary aggregate M3. "
        "Stronger M3 growth generally indicates improving monetary liquidity "
        "and money creation."
    ),
)