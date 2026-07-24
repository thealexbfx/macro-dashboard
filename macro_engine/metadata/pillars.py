"""Pillar metadata for the MacroLens Engine."""

from macro_engine.models.pillar import PillarConfig


USA_GROWTH = PillarConfig(
    pillar_id="usa_growth",
    pillar="growth",
    name="USA Growth",
    economy="USA",
    minimum_buckets=3,
    bucket_weights={
        "usa_household_demand": 0.35,
        "usa_employment_momentum": 0.30,
        "usa_industrial_activity": 0.20,
        "usa_housing": 0.15,
    },
    description=(
        "Aggregates household demand, employment momentum, industrial "
        "activity, and housing into a unified assessment of current US "
        "economic growth."
    ),
)

USA_INFLATION = PillarConfig(
    pillar_id="usa_inflation",
    pillar="inflation",
    name="USA Inflation",
    economy="USA",
    minimum_buckets=4,
    bucket_weights={
        "usa_core_inflation_persistence": 0.30,
        "usa_headline_price_pressure": 0.30,
        "usa_producer_pipeline_pressure": 0.20,
        "usa_labor_cost_pressure": 0.20,
    },
    description=(
        "Aggregates core inflation, headline inflation, producer prices, "
        "and labor cost pressures into a unified assessment of current "
        "US inflation."
    ),
)

USA_LABOR = PillarConfig(
    pillar_id="usa_labor",
    pillar="labor",
    name="USA Labor",
    economy="USA",
    minimum_buckets=3,
    bucket_weights={
        "usa_employment_conditions": 0.40,
        "usa_labor_demand": 0.35,
        "usa_labor_supply": 0.25,
    },
    description=(
        "Assesses the health and direction of the US labor market using "
        "employment outcomes, employer demand, and labor-force participation."
    ),
)

USA_LIQUIDITY = PillarConfig(
    pillar_id="usa_liquidity",
    pillar="liquidity",
    name="USA Liquidity",
    economy="USA",
    minimum_buckets=2,
    bucket_weights={
        "usa_central_bank_liquidity": 0.55,
        "usa_funding_conditions": 0.45,
    },
    description=(
        "Assesses whether US financial liquidity is supportive or restrictive "
        "using Federal Reserve and Treasury balance-sheet flows together with "
        "broader financial funding conditions."
    ),
)

USA_POLICY = PillarConfig(
    pillar_id="usa_policy",
    pillar="policy",
    name="USA Policy",
    economy="USA",
    minimum_buckets=2,
    bucket_weights={
        "usa_current_policy_stance": 0.70,
        "usa_policy_expectations": 0.30,
    },
    description=(
        "Assesses the restrictiveness and direction of US monetary policy "
        "using the current real and nominal policy stance together with "
        "market-implied policy expectations."
    ),
)