"""Growth indicator metadata for the MacroLens Engine."""

from macro_engine.models.indicator import IndicatorConfig


USA_REAL_PERSONAL_CONSUMPTION = IndicatorConfig(
    indicator_id="usa_real_personal_consumption",
    name="Real Personal Consumption",
    economy="USA",
    pillar="growth",
    bucket="household_demand",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    description=(
        "Monthly growth in inflation-adjusted US personal consumption "
        "expenditures."
    ),
    source="BEA NIPA Table 2.8.1, Line 1",
    unit="percent change from previous month",
)

USA_RETAIL_SALES = IndicatorConfig(
    indicator_id="usa_retail_sales",
    name="Retail Sales",
    economy="USA",
    pillar="growth",
    bucket="household_demand",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Monthly percentage change in US retail and food-services sales."
    ),
    source="Federal Reserve Economic Data: RSAFS",
    unit="percent change from previous month",
)

USA_PERSONAL_INCOME = IndicatorConfig(
    indicator_id="usa_personal_income",
    name="Personal Income",
    economy="USA",
    pillar="growth",
    bucket="household_demand",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Monthly percentage change in US personal income."
    ),
    source="BEA NIPA Table 2.6, Line 1",
    unit="percent change from previous month",
)

USA_INDUSTRIAL_PRODUCTION = IndicatorConfig(
    indicator_id="usa_industrial_production",
    name="Industrial Production",
    economy="USA",
    pillar="growth",
    bucket="industrial_activity",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Monthly percentage change in total US industrial production."
    ),
    source="Federal Reserve Economic Data: INDPRO",
    unit="percent change from previous month",
)


USA_CAPACITY_UTILIZATION = IndicatorConfig(
    indicator_id="usa_capacity_utilization",
    name="Capacity Utilization",
    economy="USA",
    pillar="growth",
    bucket="industrial_activity",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Share of US industrial productive capacity currently in use."
    ),
    source="Federal Reserve Economic Data: TCU",
    unit="percent of capacity",
)


USA_DURABLE_GOODS_ORDERS = IndicatorConfig(
    indicator_id="usa_durable_goods_orders",
    name="Durable Goods Orders",
    economy="USA",
    pillar="growth",
    bucket="industrial_activity",
    frequency="monthly",
    economic_direction="positive",
    state_window=6,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Monthly percentage change in new orders for US manufactured "
        "durable goods."
    ),
    source="Federal Reserve Economic Data: DGORDER",
    unit="percent change from previous month",
)

USA_HOUSING_STARTS = IndicatorConfig(
    indicator_id="usa_housing_starts",
    name="Housing Starts",
    economy="USA",
    pillar="growth",
    bucket="housing",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Privately owned US housing units started, expressed at a "
        "seasonally adjusted annual rate."
    ),
    source="Federal Reserve Economic Data: HOUST",
    unit="thousands of units, seasonally adjusted annual rate",
)


USA_BUILDING_PERMITS = IndicatorConfig(
    indicator_id="usa_building_permits",
    name="Building Permits",
    economy="USA",
    pillar="growth",
    bucket="housing",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Privately owned US housing units authorized by building "
        "permits, expressed at a seasonally adjusted annual rate."
    ),
    source="Federal Reserve Economic Data: PERMIT",
    unit="thousands of units, seasonally adjusted annual rate",
)


USA_NEW_HOME_SALES = IndicatorConfig(
    indicator_id="usa_new_home_sales",
    name="New Home Sales",
    economy="USA",
    pillar="growth",
    bucket="housing",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    historical_lookback=240,
    description=(
        "Sales of new single-family houses in the United States, "
        "expressed at a seasonally adjusted annual rate."
    ),
    source="Federal Reserve Economic Data: HSN1F",
    unit="thousands of units, seasonally adjusted annual rate",
)