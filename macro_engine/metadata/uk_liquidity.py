"""Indicator metadata for the United Kingdom Liquidity pillar."""

from macro_engine.models.indicator import IndicatorConfig


UK_BOE_BALANCE_SHEET_13W_CHANGE = IndicatorConfig(
    indicator_id="uk_boe_balance_sheet_13w_change",
    name="Bank of England Balance Sheet 13W Change",
    economy="United Kingdom",
    pillar="liquidity",
    bucket="central_bank_liquidity",
    frequency="weekly",
    economic_direction="positive",
    state_window=4,
    trend_window=4,
    historical_lookback=520,
    minimum_history=104,
    source="Bank of England",
    unit="balance-sheet units",
    description=(
        "Thirteen-week change in the Bank of England balance sheet. "
        "Positive values indicate balance-sheet expansion, while negative "
        "values indicate central-bank liquidity withdrawal."
    ),
)