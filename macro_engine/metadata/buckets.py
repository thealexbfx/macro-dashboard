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