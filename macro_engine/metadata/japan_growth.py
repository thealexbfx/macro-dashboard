"""Japan growth indicator metadata."""

from macro_engine.models.indicator import IndicatorConfig


JAPAN_GDP_QOQ = IndicatorConfig(
    indicator_id="japan_gdp_qoq",
    name="Japan GDP QoQ",
    economy="Japan",
    pillar="growth",
    bucket="economic_activity",
    frequency="quarterly",
    economic_direction="positive",
    state_window=2,
    trend_window=2,
    minimum_history=24,
    historical_lookback=80,
    description=(
        "Measures quarter-on-quarter real GDP growth in Japan."
    ),
    source="Cabinet Office, Government of Japan",
    unit="Percent",
)


JAPAN_RETAIL_SALES = IndicatorConfig(
    indicator_id="japan_retail_sales",
    name="Japan Retail Sales MoM",
    economy="Japan",
    pillar="growth",
    bucket="household_demand",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Measures monthly changes in Japan's retail sales."
    ),
    source="Ministry of Economy, Trade and Industry",
    unit="Percent",
)


JAPAN_INDUSTRIAL_PRODUCTION = IndicatorConfig(
    indicator_id="japan_industrial_production",
    name="Japan Industrial Production MoM",
    economy="Japan",
    pillar="growth",
    bucket="industrial_activity",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Measures monthly changes in Japan's industrial production."
    ),
    source="Ministry of Economy, Trade and Industry",
    unit="Percent",
)


JAPAN_ECONOMY_WATCHERS = IndicatorConfig(
    indicator_id="japan_economy_watchers",
    name="Japan Economy Watchers Survey",
    economy="Japan",
    pillar="growth",
    bucket="forward_looking",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Measures current and expected economic conditions based on the "
        "views of workers exposed to household and business activity."
    ),
    source="Cabinet Office, Government of Japan",
    unit="Index",
)