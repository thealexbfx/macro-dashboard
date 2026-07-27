"""Indicator metadata for the Japan Labor pillar."""

from macro_engine.models.indicator import IndicatorConfig


JAPAN_UNEMPLOYMENT_RATE = IndicatorConfig(
    indicator_id="japan_unemployment_rate",
    name="Japan Unemployment Rate",
    economy="Japan",
    pillar="labor",
    bucket="employment_conditions",
    frequency="monthly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="Statistics Bureau of Japan",
    unit="percent",
    description=(
        "Measures the share of Japan's labor force that is unemployed. "
        "A lower unemployment rate indicates stronger labor-market conditions."
    ),
)


JAPAN_LABOR_WAGE_GROWTH = IndicatorConfig(
    indicator_id="japan_labor_wage_growth_yoy",
    name="Japan Labor Wage Growth YoY",
    economy="Japan",
    pillar="labor",
    bucket="labor_demand",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="Ministry of Health, Labour and Welfare",
    unit="percent",
    description=(
        "Measures annual wage growth as an indicator of labor-market "
        "tightness and employer demand for workers."
    ),
)