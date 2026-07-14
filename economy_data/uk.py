from indicators.uk import (
    get_uk_average_weekly_earnings_yoy_data,
    get_uk_boe_balance_sheet_data,
    get_uk_consumer_confidence_data,
    get_uk_core_cpi_yoy_data,
    get_uk_cpi_yoy_data,
    get_uk_gdp_mom_data,
    get_uk_gdp_qoq_data,
    get_uk_house_prices_yoy_data,
    get_uk_industrial_production_mom_data,
    get_uk_interest_rate_data,
    get_uk_retail_sales_mom_data,
    get_uk_services_cpi_yoy_data,
    get_uk_trade_balance_data,
    get_uk_unemployment_rate_data,
    get_uk_unit_labour_costs_yoy_data,
    get_uk_vacancies_data,
)


UK_PAGE_DESCRIPTION = (
    "Track UK growth, inflation, labor, monetary policy, liquidity, housing, "
    "sentiment, and external-sector conditions."
)


UK_CATEGORY_MAP = {
    "Monetary Policy & Liquidity": [
        "Bank Rate",
        "BoE Balance Sheet",
    ],
    "Labor Market": [
        "Unemployment Rate",
        "Average Weekly Earnings YoY",
        "Unit Labour Costs YoY",
        "Vacancies",
    ],
    "Growth": [
        "GDP QoQ",
        "GDP MoM",
        "Retail Sales MoM",
        "Industrial Production MoM",
    ],
    "Inflation": [
        "CPI YoY",
        "Core CPI YoY",
        "Services CPI YoY",
        "House Prices YoY",
    ],
    "Sentiment": [
        "Consumer Confidence",
    ],
    "External Sector": [
        "Trade Balance",
    ],
}


UK_ECONOMY_MAP = {
    "Bank Rate": {
        "data_func": get_uk_interest_rate_data,
        "frequency": "daily",
        "title": "Bank of England Bank Rate (%)",
        "description": (
            "The Bank Rate is the Bank of England's main policy interest rate. "
            "It influences borrowing costs across the economy, including mortgages, "
            "consumer credit, business loans, and money-market pricing. Markets watch "
            "it closely because it signals the stance of UK monetary policy."
        ),
        "source": "Source: Bank of England (BOE)",
        "decimals": 2,
        "is_policy_rate": True,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "BoE Balance Sheet": {
        "data_func": get_uk_boe_balance_sheet_data,
        "frequency": "daily",
        "title": "Bank of England Balance Sheet (£ Millions)",
        "description": (
            "The Bank of England balance sheet tracks the scale of central-bank "
            "liquidity support, including asset purchases and related facilities. "
            "Changes can affect gilt markets, liquidity, financial conditions, and "
            "risk appetite."
        ),
        "source": "Source: Bank of England (BOE)",
        "decimals": 0,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "currency_scale",
        "unit_label": "",
        "change_type": "absolute",
        "compatible_group": "currency_scale",
    },
    "Unemployment Rate": {
        "data_func": get_uk_unemployment_rate_data,
        "frequency": "monthly",
        "title": "Unemployment Rate (%)",
        "description": (
            "The unemployment rate measures the share of the UK labour force that "
            "is actively seeking work but currently unemployed. It is a key measure "
            "of labour-market slack and household income risk."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Average Weekly Earnings YoY": {
        "data_func": get_uk_average_weekly_earnings_yoy_data,
        "frequency": "monthly",
        "title": "Average Weekly Earnings (YoY, %)",
        "description": (
            "Average weekly earnings measure annual wage growth across the UK "
            "labour market. Wage growth affects household purchasing power, services "
            "inflation, and the Bank of England's inflation outlook."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Unit Labour Costs YoY": {
        "data_func": get_uk_unit_labour_costs_yoy_data,
        "frequency": "quarterly",
        "title": "Unit Labour Costs (YoY, %)",
        "description": (
            "Unit labour costs measure the labour cost required to produce a unit "
            "of output. They combine wage and productivity trends and are a useful "
            "gauge of underlying inflation pressure."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Vacancies": {
        "data_func": get_uk_vacancies_data,
        "frequency": "monthly",
        "title": "Job Vacancies (Thousands)",
        "description": (
            "Job vacancies measure the number of open positions employers are "
            "trying to fill. They provide a forward-looking view of labour demand "
            "and hiring appetite."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 0,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "thousands",
        "unit_label": "K",
        "change_type": "absolute",
        "compatible_group": "labor_count",
    },
    "GDP QoQ": {
        "data_func": get_uk_gdp_qoq_data,
        "frequency": "quarterly",
        "title": "GDP Growth (QoQ, %)",
        "description": (
            "GDP QoQ measures the quarterly change in total UK economic output. "
            "It captures the broad direction of activity across consumption, "
            "investment, government spending, and trade."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "GDP MoM": {
        "data_func": get_uk_gdp_mom_data,
        "frequency": "monthly",
        "title": "GDP Growth (MoM, %)",
        "description": (
            "Monthly GDP measures the month-to-month change in total UK economic "
            "output and provides a timelier view of growth momentum than quarterly GDP."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Retail Sales MoM": {
        "data_func": get_uk_retail_sales_mom_data,
        "frequency": "monthly",
        "title": "Retail Sales (MoM, %)",
        "description": (
            "Retail sales measure the monthly change in the volume of goods sold "
            "by retailers. They are an important gauge of household consumption "
            "and consumer demand."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Industrial Production MoM": {
        "data_func": get_uk_industrial_production_mom_data,
        "frequency": "monthly",
        "title": "Industrial Production (MoM, %)",
        "description": (
            "Industrial production measures the monthly change in output from "
            "manufacturing, mining, energy, and related production industries."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "CPI YoY": {
        "data_func": get_uk_cpi_yoy_data,
        "frequency": "monthly",
        "title": "Consumer Price Inflation (YoY, %)",
        "description": (
            "Consumer Price Inflation measures the annual change in the price of "
            "a broad basket of goods and services purchased by UK households. It is "
            "the headline inflation measure most closely watched by policymakers "
            "and markets."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Core CPI YoY": {
        "data_func": get_uk_core_cpi_yoy_data,
        "frequency": "monthly",
        "title": "Core Consumer Price Inflation (YoY, %)",
        "description": (
            "Core CPI excludes volatile components such as energy, food, alcohol, "
            "and tobacco. It helps identify the underlying inflation trend."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Services CPI YoY": {
        "data_func": get_uk_services_cpi_yoy_data,
        "frequency": "monthly",
        "title": "Services CPI Inflation (YoY, %)",
        "description": (
            "Services CPI measures annual inflation across UK services. Services "
            "inflation tends to be stickier than goods inflation and is closely "
            "watched by the Bank of England."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "House Prices YoY": {
        "data_func": get_uk_house_prices_yoy_data,
        "frequency": "monthly",
        "title": "House Price Growth (YoY, %)",
        "description": (
            "House-price growth measures the annual change in UK residential "
            "property prices. It provides insight into housing momentum, household "
            "wealth, mortgage affordability, and credit conditions."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Consumer Confidence": {
        "data_func": get_uk_consumer_confidence_data,
        "frequency": "monthly",
        "title": "UK Consumer Confidence Index",
        "description": (
            "Consumer confidence measures household expectations about the economy "
            "and personal finances. It is useful for assessing future consumption, "
            "saving behaviour, and recession risk."
        ),
        "source": "Source: OECD via FRED",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "index",
        "unit_label": "",
        "change_type": "absolute",
        "compatible_group": "index",
    },
    "Trade Balance": {
        "data_func": get_uk_trade_balance_data,
        "frequency": "monthly",
        "title": "Trade Balance (£ Millions)",
        "description": (
            "The trade balance measures the difference between UK exports and "
            "imports of goods and services. It helps assess external demand, "
            "domestic import demand, currency sensitivity, and net trade."
        ),
        "source": "Source: Office for National Statistics (ONS)",
        "decimals": 0,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "currency_scale",
        "unit_label": "",
        "change_type": "absolute",
        "compatible_group": "currency_scale",
    },
}