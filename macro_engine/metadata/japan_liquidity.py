"""Indicator metadata for the Japan Liquidity pillar."""

from macro_engine.models.indicator import IndicatorConfig


JAPAN_CENTRAL_BANK_ASSETS = IndicatorConfig(
    indicator_id="japan_central_bank_assets_yoy",
    name="Central Bank Assets YoY",
    economy="Japan",
    pillar="liquidity",
    bucket="central_bank_liquidity",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="FRED / Bank of Japan",
    unit="percent",
    description=(
        "Measures annual growth in Bank of Japan assets as an indicator "
        "of central bank liquidity."
    ),
)


JAPAN_M3_GROWTH = IndicatorConfig(
    indicator_id="japan_m3_yoy",
    name="M3 Money Supply YoY",
    economy="Japan",
    pillar="liquidity",
    bucket="money_conditions",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="Bank of Japan",
    unit="percent",
    description=(
        "Measures annual growth in Japan's broad money supply (M3)."
    ),
)