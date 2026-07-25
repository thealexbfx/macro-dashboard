"""
MacroLens Pillar Pipelines.

Each function orchestrates the bucket pipelines for one macro pillar.
"""
from datetime import date

from macro_engine.engine.pillar_engine import run_pillar
from macro_engine.models.pillar import PillarResult

from macro_engine.metadata.pillars import (
    EURO_GROWTH,
    USA_GROWTH,
    USA_INFLATION,
    USA_LABOR,
    USA_LIQUIDITY,
    USA_POLICY,
)

from macro_engine.pipelines.growth import (
    run_usa_household_demand,
    run_usa_employment_momentum,
    run_usa_industrial_activity,
    run_usa_housing,
)
from macro_engine.pipelines.euro_growth import (
    run_euro_economic_activity,
    run_euro_forward_looking,
    run_euro_household_demand,
    run_euro_industrial_activity,
)

from macro_engine.pipelines.inflation import (
    run_usa_core_inflation_persistence,
    run_usa_headline_price_pressure,
    run_usa_producer_pipeline_pressure,
    run_usa_labor_cost_pressure,
)

from macro_engine.pipelines.labor import (
    run_usa_employment_conditions,
    run_usa_labor_demand,
    run_usa_labor_supply,
)

from macro_engine.pipelines.liquidity import (
    run_usa_central_bank_liquidity,
    run_usa_funding_conditions,
)

from macro_engine.pipelines.policy import (
    run_usa_current_policy_stance,
    run_usa_policy_expectations,
)

def run_usa_growth(
    as_of_date: date | None = None,
):
    """
    Execute the complete USA Growth pillar.
    """

    bucket_results = (
        run_usa_household_demand(
            as_of_date=as_of_date,
        ),
        run_usa_employment_momentum(
            as_of_date=as_of_date,
        ),
        run_usa_industrial_activity(
            as_of_date=as_of_date,
        ),
        run_usa_housing(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        USA_GROWTH,
    )
    
def run_euro_growth(
    as_of_date: date | None = None,
) -> PillarResult:
    """
    Execute the complete Euro Area Growth pillar.
    """

    bucket_results = (
        run_euro_economic_activity(
            as_of_date=as_of_date,
        ),
        run_euro_household_demand(
            as_of_date=as_of_date,
        ),
        run_euro_industrial_activity(
            as_of_date=as_of_date,
        ),
        run_euro_forward_looking(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        EURO_GROWTH,
    )

def run_usa_inflation(
    as_of_date: date | None = None,
):
    """
    Execute the complete USA Inflation pillar.
    """

    bucket_results = (
        run_usa_core_inflation_persistence(
            as_of_date=as_of_date,
        ),
        run_usa_headline_price_pressure(
            as_of_date=as_of_date,
        ),
        run_usa_producer_pipeline_pressure(
            as_of_date=as_of_date,
        ),
        run_usa_labor_cost_pressure(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        USA_INFLATION,
    )
    
def run_usa_labor(
    as_of_date: date | None = None,
):
    """
    Execute the complete USA Labor pillar.
    """

    bucket_results = (
        run_usa_employment_conditions(
            as_of_date=as_of_date,
        ),
        run_usa_labor_demand(
            as_of_date=as_of_date,
        ),
        run_usa_labor_supply(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        USA_LABOR,
    )

def run_usa_liquidity_pillar(
    as_of_date: date | None = None,
):
    """
    Execute the complete USA Liquidity pillar.
    """

    bucket_results = (
        run_usa_central_bank_liquidity(
            as_of_date=as_of_date,
        ),
        run_usa_funding_conditions(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        USA_LIQUIDITY,
    )

def run_usa_policy_pillar(
    as_of_date: date | None = None,
):
    """
    Execute the complete USA Policy pillar.
    """

    bucket_results = (
        run_usa_current_policy_stance(
            as_of_date=as_of_date,
        ),
        run_usa_policy_expectations(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        USA_POLICY,
    )