from __future__ import annotations

from datetime import date
from macro_engine.utils.timing import log_runtime
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
    run_uk_growth,
    run_uk_inflation,
    run_uk_labor,
    run_uk_liquidity,
    run_japan_growth,
    run_japan_inflation,
    run_japan_labor,
    run_japan_liquidity,
    run_japan_policy,
)
from macro_engine.pipelines.uk_policy import (
    run_uk_policy,
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

UK_MACRO_ENVIRONMENT = MacroEnvironmentConfig(
    economy="United Kingdom",
    minimum_pillars=4,
    minimum_confidence=0.60,
)

JAPAN_MACRO_ENVIRONMENT = MacroEnvironmentConfig(
    economy="Japan",
    minimum_pillars=5,
    minimum_confidence=0.60,
)

def run_usa_macro_environment(
    as_of_date: date | None = None,
) -> MacroEnvironmentResult:
    """Run the complete USA macro environment pipeline."""

    with log_runtime("USA — Growth pillar"):
        growth = run_usa_growth(
            as_of_date=as_of_date,
        )

    with log_runtime("USA — Inflation pillar"):
        inflation = run_usa_inflation(
            as_of_date=as_of_date,
        )

    with log_runtime("USA — Labor pillar"):
        labor = run_usa_labor(
            as_of_date=as_of_date,
        )

    with log_runtime("USA — Liquidity pillar"):
        liquidity = run_usa_liquidity_pillar(
            as_of_date=as_of_date,
        )

    with log_runtime("USA — Policy pillar"):
        policy = run_usa_policy_pillar(
            as_of_date=as_of_date,
        )

    with log_runtime(
        "USA — Final environment classification"
    ):
        return build_environment_result(
            config=USA_MACRO_ENVIRONMENT,
            pillar_results=(
                growth,
                inflation,
                labor,
                liquidity,
                policy,
            ),
            as_of_date=as_of_date,
        )
    
def run_euro_macro_environment(
    as_of_date: date | None = None,
) -> MacroEnvironmentResult:
    """Run the complete Euro Area macro environment pipeline."""

    with log_runtime("Euro Area — Growth pillar"):
        growth = run_euro_growth(
            as_of_date=as_of_date,
        )

    with log_runtime("Euro Area — Inflation pillar"):
        inflation = run_euro_inflation(
            as_of_date=as_of_date,
        )

    with log_runtime("Euro Area — Labor pillar"):
        labor = run_euro_labor(
            as_of_date=as_of_date,
        )

    with log_runtime("Euro Area — Liquidity pillar"):
        liquidity = run_euro_liquidity(
            as_of_date=as_of_date,
        )

    with log_runtime("Euro Area — Policy pillar"):
        policy = run_euro_policy(
            as_of_date=as_of_date,
        )

    with log_runtime(
        "Euro Area — Final environment classification"
    ):
        return build_environment_result(
            config=EURO_MACRO_ENVIRONMENT,
            pillar_results=(
                growth,
                inflation,
                labor,
                liquidity,
                policy,
            ),
            as_of_date=as_of_date,
        )
    
def run_uk_macro_environment(
    as_of_date: date | None = None,
) -> MacroEnvironmentResult:
    """Run the current UK macro environment pipeline."""

    with log_runtime("UK — Growth pillar"):
        growth = run_uk_growth(
            as_of_date=as_of_date,
        )

    with log_runtime("UK — Inflation pillar"):
        inflation = run_uk_inflation(
            as_of_date=as_of_date,
        )

    with log_runtime("UK — Labor pillar"):
        labor = run_uk_labor(
            as_of_date=as_of_date,
        )

    with log_runtime("UK — Liquidity pillar"):
        liquidity = run_uk_liquidity(
            as_of_date=as_of_date,
        )

    with log_runtime("UK — Policy pillar"):
        policy = run_uk_policy(
            as_of_date=as_of_date,
        )

    with log_runtime(
        "UK — Final environment classification"
    ):
        return build_environment_result(
            config=UK_MACRO_ENVIRONMENT,
            pillar_results=(
                growth,
                inflation,
                labor,
                liquidity,
                policy,
            ),
            as_of_date=as_of_date,
        )
    
def run_japan_macro_environment(
    as_of_date: date | None = None,
) -> MacroEnvironmentResult:
    """Run the complete Japan macro environment pipeline."""

    with log_runtime("Japan — Growth pillar"):
        growth = run_japan_growth(
            as_of_date=as_of_date,
        )

    with log_runtime("Japan — Inflation pillar"):
        inflation = run_japan_inflation(
            as_of_date=as_of_date,
        )

    with log_runtime("Japan — Labor pillar"):
        labor = run_japan_labor(
            as_of_date=as_of_date,
        )

    with log_runtime("Japan — Liquidity pillar"):
        liquidity = run_japan_liquidity(
            as_of_date=as_of_date,
        )

    with log_runtime("Japan — Policy pillar"):
        policy = run_japan_policy(
            as_of_date=as_of_date,
        )

    with log_runtime(
        "Japan — Final environment classification"
    ):
        return build_environment_result(
            config=JAPAN_MACRO_ENVIRONMENT,
            pillar_results=(
                growth,
                inflation,
                labor,
                liquidity,
                policy,
            ),
            as_of_date=as_of_date,
        )