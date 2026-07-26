from macro_engine.models.indicator import IndicatorConfig


EURO_REAL_POLICY_RATE = IndicatorConfig(
    indicator_id="euro_real_policy_rate",
    name="Real ECB Policy Rate",
    economy="Euro Area",
    pillar="policy",
    bucket="current_policy_stance",
    frequency="monthly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    historical_lookback=180,
    minimum_history=60,
    description=(
        "ECB main refinancing rate minus Euro Area core HICP inflation. "
        "Higher real policy rates represent a more restrictive monetary stance."
    ),
    source="ECB / Eurostat",
    unit="percent",
)


EURO_POLICY_RATE = IndicatorConfig(
    indicator_id="euro_policy_rate",
    name="ECB Main Refinancing Rate",
    economy="Euro Area",
    pillar="policy",
    bucket="current_policy_stance",
    frequency="monthly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    historical_lookback=180,
    minimum_history=60,
    description=(
        "ECB main refinancing operations rate. Higher policy rates represent "
        "a more restrictive nominal monetary-policy stance."
    ),
    source="ECB",
    unit="percent",
)