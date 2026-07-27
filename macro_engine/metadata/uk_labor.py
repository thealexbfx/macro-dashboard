"""Indicator metadata for the UK Labor pillar."""

from macro_engine.models.indicator import IndicatorConfig


UK_UNEMPLOYMENT_RATE = IndicatorConfig(
    indicator_id="uk_unemployment_rate",
    name="UK Unemployment Rate",
    economy="United Kingdom",
    pillar="labor",
    bucket="employment_conditions",
    frequency="monthly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="ONS",
    unit="percent",
    description=(
        "Seasonally adjusted UK unemployment rate. Rising unemployment "
        "indicates weakening labor-market conditions."
    ),
)


UK_VACANCIES = IndicatorConfig(
    indicator_id="uk_vacancies",
    name="UK Vacancies",
    economy="United Kingdom",
    pillar="labor",
    bucket="labor_demand",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="ONS",
    unit="thousands",
    description=(
        "Estimated number of UK job vacancies. Higher vacancies indicate "
        "stronger labor demand."
    ),
)