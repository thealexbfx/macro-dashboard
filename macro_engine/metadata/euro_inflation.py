"""Indicator metadata for the Euro Area Inflation pillar."""

from macro_engine.models.indicator import IndicatorConfig


EURO_HEADLINE_HICP = IndicatorConfig(
    indicator_id="euro_headline_hicp_yoy",
    name="Euro Area Headline HICP YoY",
    economy="Euro Area",
    pillar="inflation",
    bucket="headline_price_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="Eurostat",
    unit="percent",
    description=(
        "Year-over-year change in the Euro Area Harmonised Index of Consumer "
        "Prices. Measures broad consumer price pressure including food and energy."
    ),
)


EURO_CORE_HICP = IndicatorConfig(
    indicator_id="euro_core_hicp_yoy",
    name="Euro Area Core HICP YoY",
    economy="Euro Area",
    pillar="inflation",
    bucket="core_inflation_persistence",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="Eurostat",
    unit="percent",
    description=(
        "Year-over-year change in Euro Area HICP excluding energy and food. "
        "Measures persistent underlying consumer inflation."
    ),
)


EURO_SERVICES_HICP = IndicatorConfig(
    indicator_id="euro_services_hicp_yoy",
    name="Euro Area Services HICP YoY",
    economy="Euro Area",
    pillar="inflation",
    bucket="core_inflation_persistence",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="Eurostat",
    unit="percent",
    description=(
        "Year-over-year change in Euro Area services prices. Measures "
        "persistent domestically generated inflation pressure."
    ),
)


EURO_NEGOTIATED_WAGES = IndicatorConfig(
    indicator_id="euro_negotiated_wages_yoy",
    name="Euro Area Negotiated Wages YoY",
    economy="Euro Area",
    pillar="inflation",
    bucket="wage_cost_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="ECB",
    unit="percent",
    description=(
        "Measures negotiated wage growth across the Euro Area as an indicator "
        "of domestic labor-cost inflation pressure."
    ),
)


EURO_LABOR_PRODUCTIVITY = IndicatorConfig(
    indicator_id="euro_labor_productivity_yoy",
    name="Euro Area Labor Productivity YoY",
    economy="Euro Area",
    pillar="inflation",
    bucket="wage_cost_pressure",
    frequency="quarterly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    minimum_history=24,
    source="ECB",
    unit="percent",
    description=(
        "Measures labor productivity growth, with stronger productivity "
        "interpreted as reducing wage-related inflation pressure."
    ),
)


EURO_ECB_REFINANCING_RATE = IndicatorConfig(
    indicator_id="euro_ecb_refinancing_rate",
    name="ECB Main Refinancing Rate",
    economy="Euro Area",
    pillar="inflation",
    bucket="monetary_policy_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=24,
    historical_lookback=240,
    description=(
        "Measures the ECB main refinancing rate as an indicator of current "
        "monetary policy restraint."
    ),
    source="ECB",
    unit="percent",
)