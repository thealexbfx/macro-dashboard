from macro_engine.models.indicator import IndicatorConfig


USA_NET_FED_LIQUIDITY_13W_CHANGE = IndicatorConfig(
    indicator_id="usa_net_fed_liquidity_13w_change",
    name="Net Fed Liquidity",
    economy="USA",
    pillar="liquidity",
    bucket="central_bank_liquidity",
    frequency="weekly",
    economic_direction="positive",
    state_window=4,
    trend_window=4,
    historical_lookback=520,
    minimum_history=104,
    description=(
        "Thirteen-week change in a net Federal Reserve liquidity proxy "
        "constructed from Federal Reserve assets less the Treasury General "
        "Account and the Overnight Reverse Repo Facility."
    ),
    source="FRED: WALCL, WTREGEN, RRPONTSYD",
    unit="millions of US dollars",
)


USA_RESERVE_BALANCES_13W_CHANGE = IndicatorConfig(
    indicator_id="usa_reserve_balances_13w_change",
    name="Reserve Balances",
    economy="USA",
    pillar="liquidity",
    bucket="central_bank_liquidity",
    frequency="weekly",
    economic_direction="positive",
    state_window=4,
    trend_window=4,
    historical_lookback=520,
    minimum_history=104,
    description=(
        "Thirteen-week change in reserve balances held by depository "
        "institutions at Federal Reserve Banks."
    ),
    source="FRED: WRESBAL",
    unit="millions of US dollars",
)

USA_CHICAGO_FED_NFCI = IndicatorConfig(
    indicator_id="usa_chicago_fed_nfci",
    name="Chicago Fed Financial Conditions",
    economy="USA",
    pillar="liquidity",
    bucket="funding_conditions",
    frequency="weekly",
    economic_direction="negative",
    state_window=4,
    trend_window=4,
    historical_lookback=520,
    minimum_history=104,
    description=(
        "Chicago Fed National Financial Conditions Index. Lower values "
        "represent looser and more supportive financial conditions, while "
        "higher values represent tighter financial conditions."
    ),
    source="Federal Reserve Economic Data: NFCI",
    unit="index",
)

USA_M2_YOY = IndicatorConfig(
    indicator_id="usa_m2_yoy",
    name="M2 Money Supply",
    economy="USA",
    pillar="liquidity",
    bucket="money_conditions",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    historical_lookback=240,
    minimum_history=36,
    description=(
        "Annual growth in the US M2 money supply."
    ),
    source="FRED: M2SL",
    unit="percent",
)