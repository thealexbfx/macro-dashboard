from indicators.japan import (
    get_japan_boj_balance_sheet_data,
    get_japan_core_cpi_yoy_data,
    get_japan_cpi_yoy_data,
    get_japan_economy_watchers_survey_data,
    get_japan_gdp_qoq_data,
    get_japan_housing_starts_yoy_data,
    get_japan_industrial_production_mom_data,
    get_japan_interest_rate_data,
    get_japan_retail_sales_mom_data,
    get_japan_tankan_large_manufacturers_data,
    get_japan_tokyo_core_cpi_yoy_data,
    get_japan_tokyo_cpi_yoy_data,
    get_japan_trade_balance_data,
    get_japan_unemployment_rate_data,
    get_japan_wage_growth_data,
)


JAPAN_PAGE_DESCRIPTION = (
    "Track Japanese growth, inflation, labor, monetary policy, liquidity, "
    "housing, sentiment, and external-sector conditions."
)


JAPAN_CATEGORY_MAP = {
    "Monetary Policy & Liquidity": [
        "Interest Rate",
        "BOJ Balance Sheet",
    ],
    "Labor Market": [
        "Unemployment Rate",
        "Wage Growth YoY",
    ],
    "Growth": [
        "GDP Growth Rate",
        "Retail Sales MoM",
        "Industrial Production MoM",
    ],
    "Inflation": [
        "CPI YoY",
        "Core CPI YoY",
        "Tokyo CPI YoY",
        "Tokyo Core CPI YoY",
    ],
    "Sentiment": [
        "Tankan Large Manufacturers Index",
        "Economy Watchers Survey",
    ],
    "Housing": [
        "Housing Starts YoY",
    ],
    "External Sector": [
        "Trade Balance",
    ],
}


JAPAN_ECONOMY_MAP = {
    "Interest Rate": {
        "data_func": get_japan_interest_rate_data,
        "frequency": "daily",
        "title": "Bank of Japan Policy Rate (%)",
        "description": (
            "The Bank of Japan policy rate is the benchmark interest rate set by "
            "the BOJ. It influences short-term borrowing costs, financial conditions, "
            "the yen, and expectations for monetary tightening or easing."
        ),
        "source": "Source: Bank of Japan (BOJ)",
        "decimals": 2,
        "is_policy_rate": True,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "BOJ Balance Sheet": {
        "data_func": get_japan_boj_balance_sheet_data,
        "frequency": "monthly",
        "title": "BOJ Balance Sheet (¥100 Million)",
        "description": (
            "The Bank of Japan balance sheet tracks the size of the BOJ's asset "
            "holdings. Changes reflect quantitative easing or tightening and provide "
            "a broad measure of monetary liquidity in the Japanese economy."
        ),
        "source": "Source: Bank of Japan",
        "decimals": 0,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "currency_scale",
        "unit_label": "",
        "change_type": "absolute",
        "compatible_group": "currency_scale",
    },
    "Unemployment Rate": {
        "data_func": get_japan_unemployment_rate_data,
        "frequency": "monthly",
        "title": "Unemployment Rate (%)",
        "description": (
            "The unemployment rate measures the share of Japan's labor force that "
            "is actively seeking work but unemployed. It is a primary indicator of "
            "labor-market health, household income risk, and domestic demand."
        ),
        "source": "Source: Statistics Bureau of Japan / e-Stat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Wage Growth YoY": {
        "data_func": get_japan_wage_growth_data,
        "frequency": "monthly",
        "title": "Wage Growth (YoY, %)",
        "description": (
            "Wage growth tracks changes in worker earnings across Japan. Sustained "
            "wage growth is an important condition for the Bank of Japan to view "
            "inflation as durable rather than temporary."
        ),
        "source": "Source: Statistics Dashboard / e-Stat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "GDP Growth Rate": {
        "data_func": get_japan_gdp_qoq_data,
        "frequency": "quarterly",
        "title": "GDP Growth Rate (QoQ Annualized, %)",
        "description": (
            "The GDP growth rate measures the pace at which the Japanese economy "
            "is expanding or contracting. It reflects changes in consumption, "
            "investment, government spending, inventories, and trade."
        ),
        "source": "Source: Cabinet Office of Japan / e-Stat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Retail Sales MoM": {
        "data_func": get_japan_retail_sales_mom_data,
        "frequency": "monthly",
        "title": "Retail Sales (MoM, %)",
        "description": (
            "Retail sales measure the monthly change in consumer spending at "
            "retailers across Japan. They provide insight into domestic demand, "
            "household confidence, and consumption momentum."
        ),
        "source": "Source: Ministry of Economy, Trade and Industry (METI)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Industrial Production MoM": {
        "data_func": get_japan_industrial_production_mom_data,
        "frequency": "monthly",
        "title": "Industrial Production (MoM, %)",
        "description": (
            "Industrial production measures the monthly change in Japan's factory "
            "and manufacturing output. It is a key cyclical indicator for the "
            "goods-producing economy and global trade exposure."
        ),
        "source": "Source: Statistics Dashboard / METI",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "CPI YoY": {
        "data_func": get_japan_cpi_yoy_data,
        "frequency": "monthly",
        "title": "Consumer Price Index (YoY, %)",
        "description": (
            "The Consumer Price Index tracks the annual change in the cost of a "
            "basket of goods and services in Japan. It is a key inflation measure "
            "for households, markets, wages, and Bank of Japan policy."
        ),
        "source": "Source: Statistics Bureau of Japan / e-Stat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Core CPI YoY": {
        "data_func": get_japan_core_cpi_yoy_data,
        "frequency": "monthly",
        "title": "Core Consumer Price Index (YoY, %)",
        "description": (
            "Core CPI tracks Japan's underlying inflation trend by excluding more "
            "volatile items. It is closely watched by the Bank of Japan when "
            "assessing whether inflation is becoming sustained."
        ),
        "source": "Source: Statistics Bureau of Japan / e-Stat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Tokyo CPI YoY": {
        "data_func": get_japan_tokyo_cpi_yoy_data,
        "frequency": "monthly",
        "title": "Tokyo Consumer Price Index (YoY, %)",
        "description": (
            "Tokyo CPI tracks inflation in the Tokyo area and is released before "
            "the national CPI figures. It is useful as an early signal of Japan's "
            "national inflation trend."
        ),
        "source": "Source: Statistics Bureau of Japan / e-Stat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Tokyo Core CPI YoY": {
        "data_func": get_japan_tokyo_core_cpi_yoy_data,
        "frequency": "monthly",
        "title": "Tokyo Core Consumer Price Index (YoY, %)",
        "description": (
            "Tokyo Core CPI excludes fresh food and serves as one of the earliest "
            "indicators of underlying inflation trends in Japan. Markets monitor "
            "it as a leading signal for national inflation and BOJ policy."
        ),
        "source": "Source: Statistics Bureau of Japan / e-Stat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Tankan Large Manufacturers Index": {
        "data_func": get_japan_tankan_large_manufacturers_data,
        "frequency": "quarterly",
        "title": "Tankan Large Manufacturers Index",
        "description": (
            "The Tankan Large Manufacturers Index measures business conditions "
            "among Japan's large manufacturing firms. It is one of Japan's most "
            "important business-sentiment indicators."
        ),
        "source": "Source: Bank of Japan (BOJ)",
        "decimals": 0,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "index",
        "unit_label": "",
        "change_type": "absolute",
        "compatible_group": "index",
    },
    "Economy Watchers Survey": {
        "data_func": get_japan_economy_watchers_survey_data,
        "frequency": "monthly",
        "title": "Economy Watchers Survey",
        "description": (
            "The Economy Watchers Survey tracks current business and household "
            "sentiment across Japan. It is a timely gauge of domestic demand, "
            "confidence, and turning points in the economic cycle."
        ),
        "source": "Source: Cabinet Office of Japan",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "index",
        "unit_label": "",
        "change_type": "absolute",
        "compatible_group": "index",
    },
    "Housing Starts YoY": {
        "data_func": get_japan_housing_starts_yoy_data,
        "frequency": "monthly",
        "title": "Housing Starts (YoY, %)",
        "description": (
            "Housing starts measure the annual change in new residential "
            "construction activity in Japan. They help track housing demand, "
            "construction momentum, and interest-rate sensitivity."
        ),
        "source": (
            "Source: Ministry of Land, Infrastructure, Transport and Tourism / e-Stat"
        ),
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Trade Balance": {
        "data_func": get_japan_trade_balance_data,
        "frequency": "monthly",
        "title": "Trade Balance (¥ Billions)",
        "description": (
            "Japan's trade balance measures the difference between exports and "
            "imports. It provides insight into external demand, import costs, "
            "competitiveness, the yen, and net trade's contribution to growth."
        ),
        "source": "Source: Japan Customs",
        "decimals": 0,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "currency_scale",
        "unit_label": "",
        "change_type": "absolute",
        "compatible_group": "currency_scale",
    },
}