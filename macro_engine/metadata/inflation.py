"""Indicator metadata for the USA Inflation pillar."""

from macro_engine.models.indicator import IndicatorConfig


USA_CORE_CPI = IndicatorConfig(
    indicator_id="usa_core_cpi_yoy",
    name="Core CPI YoY",
    economy="USA",
    pillar="inflation",
    bucket="core_inflation_persistence",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="percent",
    description=(
        "Year-over-year change in the US Consumer Price Index excluding "
        "food and energy. Measures underlying consumer price pressure."
    ),
)


USA_CORE_PCE = IndicatorConfig(
    indicator_id="usa_core_pce_yoy",
    name="Core PCE YoY",
    economy="USA",
    pillar="inflation",
    bucket="core_inflation_persistence",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BEA",
    unit="percent",
    description=(
        "Year-over-year change in the US Personal Consumption Expenditures "
        "price index excluding food and energy. Measures persistent "
        "underlying consumer inflation."
    ),
)

USA_HEADLINE_CPI = IndicatorConfig(
    indicator_id="usa_headline_cpi_yoy",
    name="Headline CPI YoY",
    economy="USA",
    pillar="inflation",
    bucket="headline_price_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="percent",
    description=(
        "Year-over-year change in the full US Consumer Price Index. "
        "Measures broad consumer price pressure including food and energy."
    ),
)


USA_HEADLINE_CPI_3M_ANNUALIZED = IndicatorConfig(
    indicator_id="usa_headline_cpi_3m_annualized",
    name="Headline CPI 3M Annualized",
    economy="USA",
    pillar="inflation",
    bucket="headline_price_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="percent",
    description=(
        "Three-month annualized change in the full US Consumer Price Index. "
        "Measures recent headline inflation momentum and identifies turning "
        "points faster than the year-over-year rate."
    ),
)


USA_FOOD_CPI = IndicatorConfig(
    indicator_id="usa_food_cpi_yoy",
    name="Food CPI YoY",
    economy="USA",
    pillar="inflation",
    bucket="headline_price_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="percent",
    description=(
        "Year-over-year change in the US Consumer Price Index for food. "
        "Measures food-price pressure directly experienced by households."
    ),
)


USA_ENERGY_CPI = IndicatorConfig(
    indicator_id="usa_energy_cpi_yoy",
    name="Energy CPI YoY",
    economy="USA",
    pillar="inflation",
    bucket="headline_price_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=60,
    source="BLS",
    unit="percent",
    description=(
        "Year-over-year change in the US Consumer Price Index for energy. "
        "Measures volatile energy-price pressure affecting headline inflation."
    ),
)

USA_HEADLINE_PPI = IndicatorConfig(
    indicator_id="usa_headline_ppi_yoy",
    name="Headline PPI YoY",
    economy="USA",
    pillar="inflation",
    bucket="producer_pipeline_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="BLS",
)

USA_CORE_PPI = IndicatorConfig(
    indicator_id="usa_core_ppi_yoy",
    name="Core PPI YoY",
    economy="USA",
    pillar="inflation",
    bucket="producer_pipeline_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="BLS",
)

USA_IMPORT_PRICES = IndicatorConfig(
    indicator_id="usa_import_prices_yoy",
    name="Import Prices YoY",
    economy="USA",
    pillar="inflation",
    bucket="producer_pipeline_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="BLS",
)

USA_EXPORT_PRICES = IndicatorConfig(
    indicator_id="usa_export_prices_yoy",
    name="Export Prices YoY",
    economy="USA",
    pillar="inflation",
    bucket="producer_pipeline_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="BLS",
)

USA_AVERAGE_HOURLY_EARNINGS = IndicatorConfig(
    indicator_id="usa_average_hourly_earnings_yoy",
    name="Average Hourly Earnings YoY",
    economy="USA",
    pillar="inflation",
    bucket="labor_cost_pressure",
    frequency="monthly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=36,
    source="BLS",
)

USA_ECI_TOTAL_COMPENSATION = IndicatorConfig(
    indicator_id="usa_eci_total_compensation_yoy",
    name="ECI Total Compensation YoY",
    economy="USA",
    pillar="inflation",
    bucket="labor_cost_pressure",
    frequency="quarterly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=24,
    source="BLS",
)

USA_ECI_WAGES_SALARIES = IndicatorConfig(
    indicator_id="usa_eci_wages_salaries_yoy",
    name="ECI Wages & Salaries YoY",
    economy="USA",
    pillar="inflation",
    bucket="labor_cost_pressure",
    frequency="quarterly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=24,
    source="BLS",
)

USA_UNIT_LABOR_COSTS = IndicatorConfig(
    indicator_id="usa_unit_labor_costs_yoy",
    name="Unit Labor Costs YoY",
    economy="USA",
    pillar="inflation",
    bucket="labor_cost_pressure",
    frequency="quarterly",
    economic_direction="positive",
    state_window=3,
    trend_window=3,
    minimum_history=24,
    source="BLS",
)

USA_LABOR_PRODUCTIVITY = IndicatorConfig(
    indicator_id="usa_labor_productivity_yoy",
    name="Labor Productivity YoY",
    economy="USA",
    pillar="inflation",
    bucket="labor_cost_pressure",
    frequency="quarterly",
    economic_direction="negative",
    state_window=3,
    trend_window=3,
    minimum_history=24,
    source="BLS",
)