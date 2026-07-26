"""Indicator metadata for the Euro Area Labor pillar."""

from macro_engine.models.indicator import IndicatorConfig


EURO_TOTAL_EMPLOYMENT_YOY = IndicatorConfig(
    indicator_id="euro_total_employment_yoy",
    name="Total Employment YoY",
    economy="Euro Area",
    pillar="labor",
    bucket="employment_conditions",
    frequency="quarterly",
    economic_direction="positive",
    state_window=4,
    trend_window=4,
    minimum_history=40,
    source="ECB",
    unit="percent",
    description=(
        "Year-over-year growth in Euro Area total employment. Stronger "
        "employment growth indicates improving labor-market conditions."
    ),
)


EURO_UNEMPLOYMENT_RATE = IndicatorConfig(
    indicator_id="euro_unemployment_rate",
    name="Unemployment Rate",
    economy="Euro Area",
    pillar="labor",
    bucket="employment_conditions",
    frequency="monthly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="Eurostat",
    unit="percent",
    description=(
        "Seasonally adjusted Euro Area unemployment rate. A rising rate "
        "indicates weakening employment conditions and increasing labor-market "
        "slack."
    ),
)