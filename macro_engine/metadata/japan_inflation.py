"""Indicator metadata for the Japan Inflation pillar."""

from macro_engine.models.indicator import IndicatorConfig


JAPAN_CPI = IndicatorConfig(
    indicator_id="japan_cpi_yoy",
    name="Japan CPI YoY",
    economy="Japan",
    pillar="inflation",
    bucket="headline_price_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="Statistics Bureau of Japan",
    unit="percent",
    description=(
        "Year-over-year change in Japan's national Consumer Price Index. "
        "Measures broad consumer price pressure including food and energy."
    ),
)


JAPAN_CORE_CPI = IndicatorConfig(
    indicator_id="japan_core_cpi_yoy",
    name="Japan Core CPI YoY",
    economy="Japan",
    pillar="inflation",
    bucket="core_inflation_persistence",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="Statistics Bureau of Japan",
    unit="percent",
    description=(
        "Year-over-year change in Japan's core Consumer Price Index. "
        "Measures persistent underlying consumer inflation pressure."
    ),
)


JAPAN_TOKYO_CPI = IndicatorConfig(
    indicator_id="japan_tokyo_cpi_yoy",
    name="Japan Tokyo CPI YoY",
    economy="Japan",
    pillar="inflation",
    bucket="headline_price_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="Statistics Bureau of Japan",
    unit="percent",
    description=(
        "Year-over-year change in the Consumer Price Index for Tokyo. "
        "Provides an early indication of national consumer price pressure."
    ),
)


JAPAN_TOKYO_CORE_CPI = IndicatorConfig(
    indicator_id="japan_tokyo_core_cpi_yoy",
    name="Japan Tokyo Core CPI YoY",
    economy="Japan",
    pillar="inflation",
    bucket="core_inflation_persistence",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="Statistics Bureau of Japan",
    unit="percent",
    description=(
        "Year-over-year change in Tokyo's core Consumer Price Index. "
        "Provides an early indication of persistent underlying inflation "
        "pressure at the national level."
    ),
)


JAPAN_WAGE_GROWTH = IndicatorConfig(
    indicator_id="japan_wage_growth_yoy",
    name="Japan Wage Growth YoY",
    economy="Japan",
    pillar="inflation",
    bucket="wage_cost_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="Statistics Bureau of Japan",
    unit="percent",
    description=(
        "Measures annual growth in Japan's wage index as an indicator of "
        "domestic wage-cost inflation pressure."
    ),
)