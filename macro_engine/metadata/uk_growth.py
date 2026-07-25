"""UK Growth indicator metadata."""

from macro_engine.models.indicator import IndicatorConfig


UK_GDP_QOQ = IndicatorConfig(
    indicator_id="uk_gdp_qoq",
    name="UK GDP QoQ",
    economy="United Kingdom",
    pillar="growth",
    bucket="economic_activity",
    frequency="quarterly",
    economic_direction="positive",
    state_window=2,
    trend_window=2,
    minimum_history=24,
    historical_lookback=80,
    description=(
        "Measures quarter-on-quarter real GDP growth in the United Kingdom."
    ),
    source="ONS",
    unit="Percent",
)


UK_GDP_MOM = IndicatorConfig(
    indicator_id="uk_gdp_mom",
    name="UK GDP MoM",
    economy="United Kingdom",
    pillar="growth",
    bucket="economic_activity",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Measures month-on-month real GDP growth in the United Kingdom."
    ),
    source="ONS",
    unit="Percent",
)


UK_RETAIL_SALES = IndicatorConfig(
    indicator_id="uk_retail_sales",
    name="UK Retail Sales MoM",
    economy="United Kingdom",
    pillar="growth",
    bucket="household_demand",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Measures monthly changes in UK retail sales volumes."
    ),
    source="ONS",
    unit="Percent",
)


UK_INDUSTRIAL_PRODUCTION = IndicatorConfig(
    indicator_id="uk_industrial_production",
    name="UK Industrial Production MoM",
    economy="United Kingdom",
    pillar="growth",
    bucket="industrial_activity",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Measures monthly changes in UK industrial production."
    ),
    source="ONS",
    unit="Percent",
)


UK_CONSUMER_CONFIDENCE = IndicatorConfig(
    indicator_id="uk_consumer_confidence",
    name="UK Consumer Confidence",
    economy="United Kingdom",
    pillar="growth",
    bucket="forward_looking",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Measures household confidence and forward-looking consumer sentiment "
        "in the United Kingdom."
    ),
    source="OECD via FRED",
    unit="Index",
)