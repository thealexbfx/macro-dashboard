from __future__ import annotations

from datetime import date

from macro_engine.engine.environment_engine import build_environment_result
from macro_engine.models.environment import (
    MacroEnvironmentConfig,
    MacroEnvironmentResult,
)
from macro_engine.pipelines.pillars import (
    run_euro_growth,
    run_euro_inflation,
    run_euro_labor,
    run_euro_liquidity,
    run_euro_policy,
    run_usa_growth,
    run_usa_inflation,
    run_usa_labor,
    run_usa_liquidity_pillar,
    run_usa_policy_pillar,
)


USA_MACRO_ENVIRONMENT = MacroEnvironmentConfig(
    economy="USA",
    minimum_pillars=5,
    minimum_confidence=0.60,
)

EURO_MACRO_ENVIRONMENT = MacroEnvironmentConfig(
    economy="Euro Area",
    minimum_pillars=5,
    minimum_confidence=0.60,
)


def run_usa_macro_environment(
    as_of_date: date | None = None,
) -> MacroEnvironmentResult:
    """
    Run the complete USA macro environment pipeline.

    The environment combines the five primary USA macro pillars:

    - Growth
    - Inflation
    - Labor
    - Liquidity
    - Policy
    """

    pillar_results = (
        run_usa_growth(
            as_of_date=as_of_date,
        ),
        run_usa_inflation(
            as_of_date=as_of_date,
        ),
        run_usa_labor(
            as_of_date=as_of_date,
        ),
        run_usa_liquidity_pillar(
            as_of_date=as_of_date,
        ),
        run_usa_policy_pillar(
            as_of_date=as_of_date,
        ),
    )

    return build_environment_result(
        config=USA_MACRO_ENVIRONMENT,
        pillar_results=pillar_results,
        as_of_date=as_of_date,
    )
    
def run_euro_macro_environment(
    as_of_date: date | None = None,
) -> MacroEnvironmentResult:
    """
    Run the complete Euro Area macro environment pipeline.

    The environment combines the five primary Euro Area macro pillars:

    - Growth
    - Inflation
    - Labor
    - Liquidity
    - Policy
    """

    pillar_results = (
        run_euro_growth(
            as_of_date=as_of_date,
        ),
        run_euro_inflation(
            as_of_date=as_of_date,
        ),
        run_euro_labor(
            as_of_date=as_of_date,
        ),
        run_euro_liquidity(
            as_of_date=as_of_date,
        ),
        run_euro_policy(
            as_of_date=as_of_date,
        ),
    )

    return build_environment_result(
        config=EURO_MACRO_ENVIRONMENT,
        pillar_results=pillar_results,
        as_of_date=as_of_date,
    )