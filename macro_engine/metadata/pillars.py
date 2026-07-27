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
    minimum_buckets=3,
    bucket_weights={
        "usa_central_bank_liquidity": 0.40,
        "usa_money_conditions": 0.30,
        "usa_funding_conditions": 0.30,
    },
    description=(
        "Assesses whether US financial liquidity is supportive or restrictive "
        "using Federal Reserve and Treasury balance-sheet flows, broad money "
        "growth, and financial funding conditions."
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

EURO_GROWTH = PillarConfig(
    pillar_id="euro_growth",
    pillar="growth",
    name="Euro Area Growth",
    economy="Euro Area",
    minimum_buckets=3,
    bucket_weights={
        "euro_economic_activity": 0.35,
        "euro_household_demand": 0.20,
        "euro_industrial_activity": 0.20,
        "euro_forward_looking": 0.25,
    },
    description=(
        "Aggregates realized economic activity, household demand, industrial "
        "production, and forward-looking sentiment into a unified assessment "
        "of current Euro Area economic growth."
    ),
)

EURO_INFLATION = PillarConfig(
    pillar_id="euro_inflation",
    pillar="inflation",
    name="Euro Area Inflation",
    economy="Euro Area",
    minimum_buckets=4,
    bucket_weights={
        "euro_core_inflation_persistence": 0.30,
        "euro_headline_price_pressure": 0.25,
        "euro_wage_cost_pressure": 0.25,
        "euro_monetary_policy_pressure": 0.20,
    },
    description=(
        "Aggregates core inflation, headline inflation, wage cost pressures, "
        "and monetary policy into a unified assessment of current Euro Area "
        "inflation."
    ),
)

EURO_LABOR = PillarConfig(
    pillar_id="euro_labor",
    pillar="labor",
    name="Euro Area Labor",
    economy="Euro Area",
    minimum_buckets=1,
    bucket_weights={
        "euro_employment_conditions": 1.00,
    },
    description=(
        "Assesses Euro Area labor-market strength using employment growth "
        "and unemployment conditions."
    ),
)

EURO_LIQUIDITY = PillarConfig(
    pillar_id="euro_liquidity",
    pillar="liquidity",
    name="Euro Area Liquidity",
    economy="Euro Area",
    minimum_buckets=2,
    bucket_weights={
        "euro_central_bank_liquidity": 0.55,
        "euro_money_conditions": 0.45,
    },
    description=(
        "Assesses Euro Area liquidity using Eurosystem balance-sheet flows "
        "and broad money growth."
    ),
)

EURO_POLICY = PillarConfig(
    pillar_id="euro_policy",
    pillar="policy",
    name="Euro Area Policy",
    economy="Euro Area",
    minimum_buckets=1,
    bucket_weights={
        "euro_current_policy_stance": 1.0,
    },
    description=(
        "Assesses the current restrictiveness of ECB monetary policy using "
        "nominal and inflation-adjusted policy rates."
    ),
)

UK_GROWTH = PillarConfig(
    pillar_id="uk_growth",
    pillar="growth",
    name="UK Growth",
    economy="United Kingdom",
    minimum_buckets=3,
    bucket_weights={
        "uk_economic_activity": 0.35,
        "uk_household_demand": 0.20,
        "uk_industrial_activity": 0.20,
        "uk_forward_looking": 0.25,
    },
    description=(
        "Aggregates realized economic activity, household demand, industrial "
        "production, and forward-looking sentiment into a unified assessment "
        "of current UK economic growth."
    ),
)

UK_INFLATION = PillarConfig(
    pillar_id="uk_inflation",
    pillar="inflation",
    name="UK Inflation",
    economy="United Kingdom",
    minimum_buckets=4,
    bucket_weights={
        "uk_core_inflation_persistence": 0.30,
        "uk_headline_price_pressure": 0.25,
        "uk_wage_cost_pressure": 0.25,
        "uk_monetary_policy_pressure": 0.20,
    },
    description=(
        "Aggregates core inflation, headline inflation, wage cost pressures, "
        "and monetary policy into a unified assessment of current UK "
        "inflation."
    ),
)

UK_LABOR = PillarConfig(
    pillar_id="uk_labor",
    name="UK Labor",
    economy="United Kingdom",
    pillar="labor",
    bucket_weights={
        "uk_employment_conditions": 0.60,
        "uk_labor_demand": 0.40,
    },
)

UK_LIQUIDITY = PillarConfig(
    pillar_id="uk_liquidity",
    pillar="liquidity",
    name="UK Liquidity",
    economy="United Kingdom",
    minimum_buckets=1,
    bucket_weights={
        "uk_central_bank_liquidity": 1.00,
    },
    description=(
        "Assesses UK liquidity using changes in the Bank of England "
        "balance sheet."
    ),
)

UK_POLICY = PillarConfig(
    pillar_id="uk_policy",
    name="Policy",
    economy="United Kingdom",
    pillar="policy",
    minimum_buckets=1,
    bucket_weights={
        "uk_current_policy_stance": 1.0,
    },
    description=(
        "Assesses the stance and direction of UK monetary policy."
    ),
)

JAPAN_GROWTH = PillarConfig(
    pillar_id="japan_growth",
    pillar="growth",
    name="Japan Growth",
    economy="Japan",
    minimum_buckets=3,
    bucket_weights={
        "japan_economic_activity": 0.35,
        "japan_household_demand": 0.20,
        "japan_industrial_activity": 0.20,
        "japan_forward_looking": 0.25,
    },
    description=(
        "Aggregates realized economic activity, household demand, industrial "
        "production, and forward-looking sentiment into a unified assessment "
        "of current Japanese economic growth."
    ),
)

JAPAN_INFLATION = PillarConfig(
    pillar_id="japan_inflation",
    pillar="inflation",
    name="Japan Inflation",
    economy="Japan",
    minimum_buckets=3,
    bucket_weights={
        "japan_core_inflation_persistence": 0.40,
        "japan_headline_price_pressure": 0.35,
        "japan_wage_cost_pressure": 0.25,
    },
    description=(
        "Aggregates core inflation, headline inflation, and wage cost "
        "pressures into a unified assessment of current Japanese inflation."
    ),
)

JAPAN_LABOR = PillarConfig(
    pillar_id="japan_labor",
    pillar="labor",
    name="Japan Labor",
    economy="Japan",
    minimum_buckets=2,
    bucket_weights={
        "japan_employment_conditions": 0.60,
        "japan_labor_demand": 0.40,
    },
    description=(
        "Assesses Japanese labor-market conditions using unemployment and "
        "wage growth as indicators of labor-market strength and demand."
    ),
)

JAPAN_LIQUIDITY = PillarConfig(
    pillar_id="japan_liquidity",
    pillar="liquidity",
    name="Japan Liquidity",
    economy="Japan",
    minimum_buckets=2,
    bucket_weights={
        "japan_central_bank_liquidity": 0.60,
        "japan_money_conditions": 0.40,
    },
    description=(
        "Assesses Japanese liquidity conditions using central bank "
        "balance sheet dynamics and broad money growth."
    ),
)

JAPAN_POLICY = PillarConfig(
    pillar_id="japan_policy",
    pillar="policy",
    name="Japan Policy",
    economy="Japan",
    minimum_buckets=1,
    bucket_weights={
        "japan_current_policy_stance": 1.00,
    },
    description=(
        "Assesses the Bank of Japan's current monetary policy stance "
        "using the policy rate."
    ),
)