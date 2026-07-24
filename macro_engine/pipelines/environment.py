from __future__ import annotations

from datetime import date

from macro_engine.engine.environment_engine import build_environment_result
from macro_engine.models.environment import (
    MacroEnvironmentConfig,
    MacroEnvironmentResult,
)
from macro_engine.pipelines.pillars import (
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