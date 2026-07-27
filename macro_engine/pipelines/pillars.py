"""
MacroLens Pillar Pipelines.

Each function orchestrates the bucket pipelines for one macro pillar.
"""
from datetime import date

from macro_engine.engine.pillar_engine import run_pillar
from macro_engine.models.pillar import PillarResult

from macro_engine.metadata.pillars import (
    UK_GROWTH,
    UK_INFLATION,
    UK_LABOR,
    UK_LIQUIDITY,
    JAPAN_GROWTH,
    JAPAN_INFLATION,
    JAPAN_LABOR,
    JAPAN_LIQUIDITY,
    JAPAN_POLICY,
    EURO_GROWTH,
    EURO_INFLATION,
    EURO_LABOR,
    EURO_LIQUIDITY,
    EURO_POLICY,
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

from macro_engine.pipelines.euro_inflation import (
    run_euro_core_inflation_persistence,
    run_euro_headline_price_pressure,
    run_euro_wage_cost_pressure,
    run_euro_monetary_policy_pressure,
)

from macro_engine.pipelines.euro_labor import (
    run_euro_employment_conditions,
)

from macro_engine.pipelines.liquidity import (
    run_usa_central_bank_liquidity,
    run_usa_money_conditions,
    run_usa_funding_conditions,
)

from macro_engine.pipelines.euro_liquidity import (
    run_euro_central_bank_liquidity,
    run_euro_money_conditions,
)

from macro_engine.pipelines.euro_policy import (
    run_euro_current_policy_stance,
)

from macro_engine.pipelines.uk_growth import (
    run_uk_economic_activity,
    run_uk_forward_looking,
    run_uk_household_demand,
    run_uk_industrial_activity,
)

from macro_engine.pipelines.uk_inflation import (
    run_uk_core_inflation_persistence,
    run_uk_headline_price_pressure,
    run_uk_wage_cost_pressure,
    run_uk_monetary_policy_pressure,
)

from macro_engine.pipelines.uk_labor import (
    run_uk_employment_conditions,
    run_uk_labor_demand,
)

from macro_engine.pipelines.uk_liquidity import (
    run_uk_central_bank_liquidity,
)

from macro_engine.pipelines.japan_growth import (
    run_japan_economic_activity,
    run_japan_forward_looking,
    run_japan_household_demand,
    run_japan_industrial_activity,
)

from macro_engine.pipelines.japan_inflation import (
    run_japan_core_inflation_persistence,
    run_japan_headline_price_pressure,
    run_japan_wage_cost_pressure,
)

from macro_engine.pipelines.japan_labor import (
    run_japan_employment_conditions,
    run_japan_labor_demand,
)

from macro_engine.pipelines.japan_liquidity import (
    run_japan_central_bank_liquidity,
    run_japan_money_conditions,
)

from macro_engine.pipelines.japan_policy import (
    run_japan_current_policy_stance,
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
    
def run_euro_inflation(
    as_of_date: date | None = None,
) -> PillarResult:
    """
    Execute the complete Euro Area Inflation pillar.
    """

    bucket_results = (
        run_euro_core_inflation_persistence(
            as_of_date=as_of_date,
        ),
        run_euro_headline_price_pressure(
            as_of_date=as_of_date,
        ),
        run_euro_wage_cost_pressure(
            as_of_date=as_of_date,
        ),
        run_euro_monetary_policy_pressure(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        EURO_INFLATION,
    )
    
    
def run_euro_labor(
    as_of_date: date | None = None,
) -> PillarResult:
    """Run the complete Euro Area Labor pillar pipeline."""

    bucket_results = [
        run_euro_employment_conditions(
            as_of_date=as_of_date,
        ),
    ]

    return run_pillar(
        bucket_results,
        EURO_LABOR,
    )
    
def run_euro_liquidity(
    as_of_date: date | None = None,
) -> PillarResult:
    """Run the complete Euro Area Liquidity pillar pipeline."""

    bucket_results = [
        run_euro_central_bank_liquidity(
            as_of_date=as_of_date,
        ),
        run_euro_money_conditions(
            as_of_date=as_of_date,
        ),
    ]

    return run_pillar(
        bucket_results,
        EURO_LIQUIDITY,
    )
    
def run_euro_policy(
    as_of_date: date | None = None,
) -> PillarResult:
    """Run the complete Euro Area Policy pillar pipeline."""

    bucket_results = [
        run_euro_current_policy_stance(
            as_of_date=as_of_date,
        ),
    ]

    return run_pillar(
        bucket_results,
        EURO_POLICY,
    )

def run_uk_growth(
    as_of_date: date | None = None,
) -> PillarResult:
    """
    Execute the complete UK Growth pillar.
    """

    bucket_results = (
        run_uk_economic_activity(
            as_of_date=as_of_date,
        ),
        run_uk_household_demand(
            as_of_date=as_of_date,
        ),
        run_uk_industrial_activity(
            as_of_date=as_of_date,
        ),
        run_uk_forward_looking(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        UK_GROWTH,
    )
    
def run_uk_inflation(
    as_of_date: date | None = None,
):
    """
    Execute the UK Inflation pillar.
    """

    bucket_results = (
        run_uk_core_inflation_persistence(
            as_of_date=as_of_date,
        ),
        run_uk_headline_price_pressure(
            as_of_date=as_of_date,
        ),
        run_uk_wage_cost_pressure(
            as_of_date=as_of_date,
        ),
        run_uk_monetary_policy_pressure(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        UK_INFLATION,
    )

def run_uk_labor(
    as_of_date: date | None = None,
) -> PillarResult:
    """Execute the UK Labor pillar."""

    bucket_results = (
        run_uk_employment_conditions(
            as_of_date=as_of_date,
        ),
        run_uk_labor_demand(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        UK_LABOR,
    )

def run_uk_liquidity(
    as_of_date: date | None = None,
) -> PillarResult:
    """Run the current UK Liquidity pillar pipeline."""

    bucket_results = [
        run_uk_central_bank_liquidity(
            as_of_date=as_of_date,
        ),
    ]

    return run_pillar(
        bucket_results,
        UK_LIQUIDITY,
    )
    


def run_japan_growth(
    as_of_date: date | None = None,
):
    """
    Execute the complete Japan Growth pillar.
    """

    bucket_results = (
        run_japan_economic_activity(
            as_of_date=as_of_date,
        ),
        run_japan_household_demand(
            as_of_date=as_of_date,
        ),
        run_japan_industrial_activity(
            as_of_date=as_of_date,
        ),
        run_japan_forward_looking(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        JAPAN_GROWTH,
    )

def run_japan_inflation(
    as_of_date: date | None = None,
) -> PillarResult:
    """
    Execute the complete Japan Inflation pillar.
    """

    bucket_results = (
        run_japan_core_inflation_persistence(
            as_of_date=as_of_date,
        ),
        run_japan_headline_price_pressure(
            as_of_date=as_of_date,
        ),
        run_japan_wage_cost_pressure(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        JAPAN_INFLATION,
    )

def run_japan_labor(
    as_of_date: date | None = None,
) -> PillarResult:
    """Execute the Japan Labor pillar."""

    bucket_results = (
        run_japan_employment_conditions(
            as_of_date=as_of_date,
        ),
        run_japan_labor_demand(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        JAPAN_LABOR,
    )

def run_japan_liquidity(
    as_of_date: date | None = None,
) -> PillarResult:
    """Execute the Japan Liquidity pillar."""

    bucket_results = (
        run_japan_central_bank_liquidity(
            as_of_date=as_of_date,
        ),
        run_japan_money_conditions(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        JAPAN_LIQUIDITY,
    )

def run_japan_policy(
    as_of_date: date | None = None,
) -> PillarResult:
    """Execute the Japan Policy pillar."""

    bucket_results = (
        run_japan_current_policy_stance(
            as_of_date=as_of_date,
        ),
    )

    return run_pillar(
        bucket_results,
        JAPAN_POLICY,
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
    bucket_results = [
        run_usa_central_bank_liquidity(
            as_of_date=as_of_date,
        ),
        run_usa_money_conditions(
            as_of_date=as_of_date,
        ),
        run_usa_funding_conditions(
            as_of_date=as_of_date,
        ),
    ]

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