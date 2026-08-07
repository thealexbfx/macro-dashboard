"""Indicator metadata for the USA Labor pillar."""

from macro_engine.models.indicator import IndicatorConfig


USA_JOB_OPENINGS = IndicatorConfig(
    indicator_id="usa_job_openings",
    name="JOLTS Job Openings",
    economy="USA",
    pillar="labor",
    bucket="labor_demand",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="thousands",
    description=(
        "Monthly JOLTS job openings. Measures employer demand for labor."
    ),
)


USA_QUITS_RATE = IndicatorConfig(
    indicator_id="usa_quits_rate",
    name="JOLTS Quits Rate",
    economy="USA",
    pillar="labor",
    bucket="labor_demand",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="percent",
    description=(
        "Monthly quits rate from JOLTS. Higher quits indicate stronger worker confidence and labor demand."
    ),
)

USA_NONFARM_PAYROLLS = IndicatorConfig(
    indicator_id="usa_labor_nonfarm_payrolls",
    name="Nonfarm Payrolls 3M Average",
    economy="USA",
    pillar="labor",
    bucket="employment_conditions",
    frequency="monthly",
    economic_direction="positive",
    state_window=1,
    trend_window=1,
    minimum_history=60,
    source="BLS",
    unit="thousands",
    description=(
        "Three-month average monthly change in nonfarm payroll employment. "
        "Measures the underlying pace of US job creation while reducing "
        "month-to-month payroll volatility."
    ),
)


USA_UNEMPLOYMENT_RATE = IndicatorConfig(
    indicator_id="usa_labor_unemployment_rate",
    name="Unemployment Rate",
    economy="USA",
    pillar="labor",
    bucket="employment_conditions",
    frequency="monthly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="percent",
    description=(
        "Share of the civilian labor force that is unemployed. A rising "
        "unemployment rate generally indicates weakening employment "
        "conditions and increasing labor-market slack."
    ),
)


USA_INITIAL_JOBLESS_CLAIMS = IndicatorConfig(
    indicator_id="usa_labor_initial_jobless_claims",
    name="Initial Jobless Claims 4W Average",
    economy="USA",
    pillar="labor",
    bucket="employment_conditions",
    frequency="weekly",
    economic_direction="negative",
    state_window=4,
    trend_window=4,
    minimum_history=104,
    source="FRED",
    unit="claims",
    description=(
        "Four-week moving average of initial unemployment insurance claims. "
        "Measures the pace of new job losses while smoothing weekly noise."
    ),
)

USA_LABOR_FORCE_PARTICIPATION = IndicatorConfig(
    indicator_id="usa_labor_force_participation",
    name="Labor Force Participation Rate",
    economy="USA",
    pillar="labor",
    bucket="labor_supply",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="percent",
    description=(
        "Measures the share of the civilian population participating in the labor force."
    ),
)


USA_PRIME_AGE_PARTICIPATION = IndicatorConfig(
    indicator_id="usa_prime_age_participation",
    name="Prime-Age Labor Force Participation",
    economy="USA",
    pillar="labor",
    bucket="labor_supply",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="percent",
    description=(
        "Labor force participation rate for workers aged 25-54. Removes much of the demographic noise from retirement and schooling."
    ),
)


USA_EMPLOYMENT_POPULATION_RATIO = IndicatorConfig(
    indicator_id="usa_employment_population_ratio",
    name="Employment-Population Ratio",
    economy="USA",
    pillar="labor",
    bucket="labor_supply",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="percent",
    description=(
        "Measures the proportion of the civilian population that is employed."
    ),
)