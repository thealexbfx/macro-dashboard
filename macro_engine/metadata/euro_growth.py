"""Euro Area growth indicator metadata for the MacroLens Engine."""

from macro_engine.models.indicator import IndicatorConfig


EURO_GDP_QOQ = IndicatorConfig(
    indicator_id="euro_gdp_qoq",
    name="GDP QoQ",
    economy="Euro Area",
    pillar="growth",
    bucket="economic_activity",
    frequency="quarterly",
    economic_direction="positive",
    state_window=2,
    trend_window=2,
    minimum_history=24,
    historical_lookback=80,
    description=(
        "Quarter-on-quarter growth in real Euro Area gross domestic product."
    ),
    source="Eurostat: namq_10_gdp",
    unit="percent change from previous quarter",
)


EURO_GDP_YOY = IndicatorConfig(
    indicator_id="euro_gdp_yoy",
    name="GDP YoY",
    economy="Euro Area",
    pillar="growth",
    bucket="economic_activity",
    frequency="quarterly",
    economic_direction="positive",
    state_window=2,
    trend_window=2,
    minimum_history=24,
    historical_lookback=80,
    description=(
        "Year-on-year growth in real Euro Area gross domestic product."
    ),
    source="Eurostat: namq_10_gdp",
    unit="percent change from same quarter previous year",
)


EURO_RETAIL_SALES = IndicatorConfig(
    indicator_id="euro_retail_sales",
    name="Retail Sales",
    economy="Euro Area",
    pillar="growth",
    bucket="household_demand",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Monthly percentage change in the volume of Euro Area retail trade."
    ),
    source="Eurostat: sts_trtu_m",
    unit="percent change from previous month",
)


EURO_INDUSTRIAL_PRODUCTION = IndicatorConfig(
    indicator_id="euro_industrial_production",
    name="Industrial Production",
    economy="Euro Area",
    pillar="growth",
    bucket="industrial_activity",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Monthly percentage change in Euro Area industrial production."
    ),
    source="Eurostat: sts_inpr_m",
    unit="percent change from previous month",
)


EURO_ECONOMIC_SENTIMENT = IndicatorConfig(
    indicator_id="euro_economic_sentiment",
    name="Economic Sentiment",
    economy="Euro Area",
    pillar="growth",
    bucket="forward_looking",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Euro Area Economic Sentiment Indicator, measuring confidence across "
        "industry, services, consumers, retail, and construction."
    ),
    source="European Commission / Eurostat: teibs010",
    unit="index",
)