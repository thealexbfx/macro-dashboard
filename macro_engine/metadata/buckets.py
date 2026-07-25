"""Bucket metadata for the MacroLens Engine."""

from macro_engine.models.bucket import BucketConfig


USA_HOUSEHOLD_DEMAND = BucketConfig(
    bucket_id="usa_household_demand",
    name="Household Demand",
    economy="USA",
    pillar="growth",
    minimum_indicators=2,
    indicator_weights={
        "usa_real_personal_consumption": 0.45,
        "usa_retail_sales": 0.30,
        "usa_personal_income": 0.25,
    },
    description=(
        "Assesses the strength and direction of current US household demand "
        "using consumption, retail spending, and income growth."
    ),
)

USA_INDUSTRIAL_ACTIVITY = BucketConfig(
    bucket_id="usa_industrial_activity",
    name="Industrial Activity",
    economy="USA",
    pillar="growth",
    minimum_indicators=2,
    indicator_weights={
        "usa_industrial_production": 0.45,
        "usa_capacity_utilization": 0.30,
        "usa_durable_goods_orders": 0.25,
    },
    description=(
        "Assesses the strength and direction of the US industrial economy "
        "using production, capacity usage, and durable-goods demand."
    ),
)

USA_HOUSING = BucketConfig(
    bucket_id="usa_housing",
    name="Housing",
    economy="USA",
    pillar="growth",
    indicator_weights={
        "usa_housing_starts": 0.40,
        "usa_building_permits": 0.35,
        "usa_new_home_sales": 0.25,
    },
    minimum_indicators=2,
    description=(
        "Measures current residential construction, future building "
        "activity, and demand for newly built homes."
    ),
)

USA_EMPLOYMENT_MOMENTUM = BucketConfig(
    bucket_id="usa_employment_momentum",
    name="Employment Momentum",
    economy="USA",
    pillar="growth",
    indicator_weights={
        "usa_nonfarm_payrolls": 0.30,
        "usa_unemployment_rate": 0.35,
        "usa_job_openings": 0.20,
        "usa_initial_jobless_claims": 0.15,
    },
    minimum_indicators=3,
)

USA_CORE_INFLATION_PERSISTENCE = BucketConfig(
    bucket_id="usa_core_inflation_persistence",
    name="Core Inflation Persistence",
    economy="USA",
    pillar="inflation",
    minimum_indicators=2,
    indicator_weights={
        "usa_core_cpi_yoy": 0.45,
        "usa_core_pce_yoy": 0.55,
    },
    description=(
        "Assesses persistent underlying US consumer inflation using core CPI "
        "and core PCE inflation."
    ),
)

USA_HEADLINE_PRICE_PRESSURE = BucketConfig(
    bucket_id="usa_headline_price_pressure",
    name="Headline Price Pressure",
    economy="USA",
    pillar="inflation",
    indicator_weights={
        "usa_headline_cpi_yoy": 0.40,
        "usa_headline_cpi_3m_annualized": 0.25,
        "usa_food_cpi_yoy": 0.20,
        "usa_energy_cpi_yoy": 0.15,
    },
    minimum_indicators=3,
)

USA_PRODUCER_PIPELINE_PRESSURE = BucketConfig(
    bucket_id="usa_producer_pipeline_pressure",
    name="Producer Pipeline Pressure",
    economy="USA",
    pillar="inflation",
    indicator_weights={
        "usa_headline_ppi_yoy": 0.35,
        "usa_core_ppi_yoy": 0.30,
        "usa_import_prices_yoy": 0.20,
        "usa_export_prices_yoy": 0.15,
    },
    minimum_indicators=3,
)

USA_LABOR_COST_PRESSURE = BucketConfig(
    bucket_id="usa_labor_cost_pressure",
    name="Labor Cost Pressure",
    economy="USA",
    pillar="inflation",
    indicator_weights={
        "usa_average_hourly_earnings_yoy": 0.30,
        "usa_eci_total_compensation_yoy": 0.25,
        "usa_eci_wages_salaries_yoy": 0.20,
        "usa_unit_labor_costs_yoy": 0.15,
        "usa_labor_productivity_yoy": 0.10,
    },
    minimum_indicators=4,
)

USA_LABOR_DEMAND = BucketConfig(
    bucket_id="usa_labor_demand",
    name="Labor Demand",
    economy="USA",
    pillar="labor",
    minimum_indicators=2,
    indicator_weights={
        "usa_job_openings": 0.60,
        "usa_quits_rate": 0.40,
    },
    description=(
        "Measures employer demand for labor using job openings and worker confidence through the quits rate."
    ),
)

USA_EMPLOYMENT_CONDITIONS = BucketConfig(
    bucket_id="usa_employment_conditions",
    name="Employment Conditions",
    economy="USA",
    pillar="labor",
    minimum_indicators=3,
    indicator_weights={
        "usa_labor_nonfarm_payrolls": 0.40,
        "usa_labor_unemployment_rate": 0.30,
        "usa_labor_initial_jobless_claims": 0.30,
    },
    description=(
        "Assesses current US employment conditions using the underlying pace "
        "of payroll growth, unemployment, and the flow of new job losses."
    ),
)

USA_LABOR_SUPPLY = BucketConfig(
    bucket_id="usa_labor_supply",
    name="Labor Supply",
    economy="USA",
    pillar="labor",
    minimum_indicators=2,
    indicator_weights={
        "usa_labor_force_participation": 0.35,
        "usa_prime_age_participation": 0.40,
        "usa_employment_population_ratio": 0.25,
    },
    description=(
        "Measures the availability of labor using overall participation, prime-age participation, and the employment-population ratio."
    ),
)

USA_CENTRAL_BANK_LIQUIDITY_BUCKET = BucketConfig(
    bucket_id="usa_central_bank_liquidity",
    name="Central Bank Liquidity",
    economy="USA",
    pillar="liquidity",
    minimum_indicators=2,
    indicator_weights={
        "usa_reserve_balances_13w_change": 0.55,
        "usa_net_fed_liquidity_13w_change": 0.45,
    },
    description=(
        "Measures whether Federal Reserve and Treasury balance-sheet flows "
        "are adding or removing liquidity from the US banking system."
    ),
)

USA_FUNDING_CONDITIONS = BucketConfig(
    bucket_id="usa_funding_conditions",
    name="Funding Conditions",
    economy="USA",
    pillar="liquidity",
    minimum_indicators=1,
    indicator_weights={
        "usa_chicago_fed_nfci": 1.00,
    },
    description=(
        "Measures whether broad US financial conditions are supportive or "
        "restrictive using the Chicago Fed National Financial Conditions Index."
    ),
)

USA_CURRENT_POLICY_STANCE = BucketConfig(
    bucket_id="usa_current_policy_stance",
    name="Current Policy Stance",
    economy="USA",
    pillar="policy",
    minimum_indicators=2,
    indicator_weights={
        "usa_real_policy_rate": 0.70,
        "usa_policy_rate": 0.30,
    },
    description=(
        "Measures how restrictive current Federal Reserve policy is using "
        "real and nominal policy rates."
    ),
)

USA_POLICY_EXPECTATIONS = BucketConfig(
    bucket_id="usa_policy_expectations",
    name="Policy Expectations",
    economy="USA",
    pillar="policy",
    minimum_indicators=1,
    indicator_weights={
        "usa_policy_expectations": 1.0,
    },
    description=(
        "Measures whether markets expect future monetary policy to become "
        "more accommodative or more restrictive."
    ),
)

EURO_ECONOMIC_ACTIVITY = BucketConfig(
    bucket_id="euro_economic_activity",
    name="Economic Activity",
    economy="Euro Area",
    pillar="growth",
    minimum_indicators=2,
    indicator_weights={
        "euro_gdp_qoq": 0.65,
        "euro_gdp_yoy": 0.35,
    },
    description=(
        "Measures overall Euro Area economic activity using quarterly real "
        "GDP growth on both a quarter-on-quarter and year-on-year basis."
    ),
)

EURO_HOUSEHOLD_DEMAND = BucketConfig(
    bucket_id="euro_household_demand",
    name="Household Demand",
    economy="Euro Area",
    pillar="growth",
    minimum_indicators=1,
    indicator_weights={
        "euro_retail_sales": 1.00,
    },
    description=(
        "Measures current Euro Area household demand using retail sales."
    ),
)

EURO_INDUSTRIAL_ACTIVITY = BucketConfig(
    bucket_id="euro_industrial_activity",
    name="Industrial Activity",
    economy="Euro Area",
    pillar="growth",
    minimum_indicators=1,
    indicator_weights={
        "euro_industrial_production": 1.00,
    },
    description=(
        "Measures Euro Area industrial production activity."
    ),
)

EURO_FORWARD_LOOKING = BucketConfig(
    bucket_id="euro_forward_looking",
    name="Forward Looking",
    economy="Euro Area",
    pillar="growth",
    minimum_indicators=1,
    indicator_weights={
        "euro_economic_sentiment": 1.00,
    },
    description=(
        "Measures forward-looking business and consumer confidence using the "
        "European Commission Economic Sentiment Indicator."
    ),
)