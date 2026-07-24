from macro_engine.models.indicator import IndicatorConfig


USA_REAL_POLICY_RATE = IndicatorConfig(
    indicator_id="usa_real_policy_rate",
    name="Real Policy Rate",
    economy="USA",
    pillar="policy",
    bucket="current_policy_stance",
    frequency="monthly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    historical_lookback=180,
    minimum_history=60,
    description=(
        "Federal Reserve target upper bound minus Core PCE inflation. "
        "Higher real policy rates represent a more restrictive monetary stance."
    ),
    source="Federal Reserve / BEA",
    unit="percent",
)


USA_POLICY_RATE = IndicatorConfig(
    indicator_id="usa_policy_rate",
    name="Federal Funds Target Upper Bound",
    economy="USA",
    pillar="policy",
    bucket="current_policy_stance",
    frequency="daily",
    economic_direction="negative",
    state_window=5,
    trend_window=20,
    historical_lookback=520,
    minimum_history=252,
    description=(
        "Upper bound of the Federal Reserve target range. "
        "Higher policy rates indicate a more restrictive monetary stance."
    ),
    source="Federal Reserve",
    unit="percent",
)


USA_POLICY_EXPECTATIONS = IndicatorConfig(
    indicator_id="usa_policy_expectations",
    name="Two-Year Policy Gap",
    economy="USA",
    pillar="policy",
    bucket="policy_expectations",
    frequency="daily",
    economic_direction="negative",
    state_window=5,
    trend_window=20,
    historical_lookback=520,
    minimum_history=252,
    description=(
        "Difference between the US 2-Year Treasury yield and the Federal "
        "Funds target upper bound. Negative values indicate markets expect "
        "future policy easing."
    ),
    source="Federal Reserve / Treasury",
    unit="percentage points",
)