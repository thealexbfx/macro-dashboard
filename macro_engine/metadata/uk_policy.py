from macro_engine.models.indicator import IndicatorConfig


UK_REAL_POLICY_RATE = IndicatorConfig(
    indicator_id="uk_real_policy_rate",
    name="Real Bank of England Policy Rate",
    economy="United Kingdom",
    pillar="policy",
    bucket="current_policy_stance",
    frequency="monthly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    historical_lookback=180,
    minimum_history=60,
    description=(
        "Bank of England Bank Rate minus UK core CPI inflation. "
        "Higher real policy rates represent a more restrictive monetary stance."
    ),
    source="Bank of England / ONS",
    unit="percent",
)


UK_POLICY_RATE = IndicatorConfig(
    indicator_id="uk_policy_rate",
    name="Bank of England Bank Rate",
    economy="United Kingdom",
    pillar="policy",
    bucket="current_policy_stance",
    frequency="monthly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    historical_lookback=180,
    minimum_history=60,
    description=(
        "Bank of England Bank Rate. Higher policy rates represent a more "
        "restrictive nominal monetary-policy stance."
    ),
    source="Bank of England",
    unit="percent",
)