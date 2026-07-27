"""Indicator metadata for the UK Inflation pillar."""

from macro_engine.models.indicator import IndicatorConfig


UK_CPI = IndicatorConfig(
    indicator_id="uk_cpi_yoy",
    name="UK CPI YoY",
    economy="United Kingdom",
    pillar="inflation",
    bucket="headline_price_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="ONS",
    unit="percent",
    description=(
        "Year-over-year change in the UK Consumer Prices Index. Measures broad "
        "consumer price pressure including food and energy."
    ),
)


UK_CORE_CPI = IndicatorConfig(
    indicator_id="uk_core_cpi_yoy",
    name="UK Core CPI YoY",
    economy="United Kingdom",
    pillar="inflation",
    bucket="core_inflation_persistence",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="ONS",
    unit="percent",
    description=(
        "Year-over-year change in UK CPI excluding volatile components. "
        "Measures persistent underlying consumer inflation."
    ),
)


UK_SERVICES_CPI = IndicatorConfig(
    indicator_id="uk_services_cpi_yoy",
    name="UK Services CPI YoY",
    economy="United Kingdom",
    pillar="inflation",
    bucket="core_inflation_persistence",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="ONS",
    unit="percent",
    description=(
        "Year-over-year change in UK services prices. Measures persistent "
        "domestically generated inflation pressure."
    ),
)


UK_AVERAGE_WEEKLY_EARNINGS = IndicatorConfig(
    indicator_id="uk_average_weekly_earnings_yoy",
    name="UK Average Weekly Earnings YoY",
    economy="United Kingdom",
    pillar="inflation",
    bucket="wage_cost_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="ONS",
    unit="percent",
    description=(
        "Measures annual growth in average weekly earnings as an indicator of "
        "domestic wage-cost inflation pressure."
    ),
)


UK_BANK_RATE = IndicatorConfig(
    indicator_id="uk_bank_rate",
    name="Bank of England Bank Rate",
    economy="United Kingdom",
    pillar="inflation",
    bucket="monetary_policy_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=24,
    historical_lookback=240,
    source="Bank of England",
    unit="percent",
    description=(
        "Measures the Bank of England policy rate as an indicator of current "
        "monetary policy restraint."
    ),
)

