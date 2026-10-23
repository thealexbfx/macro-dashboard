from indicators.euro import (
    get_euro_core_hicp_yoy_data,
    get_euro_ecb_balance_sheet_data,
    get_euro_economic_sentiment_data,
    get_euro_gdp_qoq_data,
    get_euro_gdp_yoy_data,
    get_euro_hicp_yoy_data,
    get_euro_house_price_index_yoy_data,
    get_euro_industrial_production_mom_data,
    get_euro_interest_rate_data,
    get_euro_labor_productivity_yoy_data,
    get_euro_negotiated_wages_yoy_data,
    get_euro_retail_sales_mom_data,
    get_euro_services_hicp_yoy_data,
    get_euro_trade_balance_data,
    get_euro_unemployment_rate_data,
)


EURO_PAGE_DESCRIPTION = (
    "Track Euro Area growth, inflation, labor, monetary policy, liquidity, "
    "housing, sentiment, and external-sector conditions."
)


EURO_CATEGORY_MAP = {
    "Monetary Policy & Liquidity": [
        "Interest Rate",
        "ECB Balance Sheet",
    ],
    "Inflation": [
        "HICP YoY",
        "Core HICP YoY",
        "Services HICP YoY",
    ],
    "Labor Market": [
        "Unemployment Rate",
        "Negotiated Wages YoY",
        "Labor Productivity YoY",
    ],
    "Housing": [
        "House Price Index YoY",
    ],
    "Growth": [
        "GDP QoQ",
        "GDP YoY",
        "Retail Sales MoM",
        "Industrial Production MoM",
    ],
    "Sentiment": [
        "Economic Sentiment Indicator",
    ],
    "External Sector": [
        "Trade Balance",
    ],
}


EURO_ECONOMY_MAP = {
    "Interest Rate": {
        "data_func": get_euro_interest_rate_data,
        "frequency": "daily",
        "title": "ECB Main Refinancing Rate (%)",
        "description": (
            "The European Central Bank main refinancing rate is shown using the "
            "official ECB effective date of rate changes. It directly affects "
            "short-term borrowing costs for banks, influencing loans, mortgages, "
            "and business investment across the Euro Area. Changes in the ECB rate "
            "are closely watched as signals of monetary tightening or easing."
        ),
        "source": "Source: European Central Bank (ECB)",
        "decimals": 2,
        "is_policy_rate": True,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "ECB Balance Sheet": {
        "data_func": get_euro_ecb_balance_sheet_data,
        "frequency": "monthly",
        "title": "ECB Balance Sheet (€ Millions)",
        "description": (
            "The ECB balance sheet measures the size of assets held by the European "
            "Central Bank and Eurosystem. It is useful for tracking liquidity "
            "conditions, quantitative easing, quantitative tightening, and the "
            "broader stance of monetary policy beyond interest rates."
        ),
        "source": "Source: European Central Bank (ECB)",
        "decimals": 0,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "currency_scale",
        "unit_label": "",
        "change_type": "absolute",
        "compatible_group": "currency_scale",
    },
    "HICP YoY": {
        "data_func": get_euro_hicp_yoy_data,
        "frequency": "monthly",
        "title": "Euro Area HICP Inflation (YoY, %)",
        "description": (
            "The Harmonised Index of Consumer Prices measures annual inflation "
            "across the Euro Area using a standardized EU methodology. It is the "
            "ECB's main inflation reference and is central to monetary policy, "
            "bond-market, and real-income analysis."
        ),
        "source": "Source: Eurostat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Core HICP YoY": {
        "data_func": get_euro_core_hicp_yoy_data,
        "frequency": "monthly",
        "title": "Euro Area Core HICP Inflation (YoY, %)",
        "description": (
            "Core HICP removes volatile items such as energy and food to provide "
            "a cleaner view of underlying inflation pressure. It is closely watched "
            "by the ECB because persistent core inflation can signal more durable "
            "price pressure."
        ),
        "source": "Source: Eurostat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Services HICP YoY": {
        "data_func": get_euro_services_hicp_yoy_data,
        "frequency": "monthly",
        "title": "Euro Area Services HICP Inflation (YoY, %)",
        "description": (
            "Services HICP measures annual inflation across service sectors such "
            "as housing, transportation, recreation, healthcare, and hospitality. "
            "Because services prices are closely linked to wages and domestic "
            "demand, services inflation tends to be more persistent than goods "
            "inflation."
        ),
        "source": "Source: Eurostat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Unemployment Rate": {
        "data_func": get_euro_unemployment_rate_data,
        "frequency": "monthly",
        "title": "Euro Area Unemployment Rate (%)",
        "description": (
            "The unemployment rate represents the share of the Euro Area labor "
            "force actively seeking work but currently without a job. It is a key "
            "indicator of labor-market slack, household income pressure, and the "
            "broader economic cycle."
        ),
        "source": "Source: Eurostat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Negotiated Wages YoY": {
        "data_func": get_euro_negotiated_wages_yoy_data,
        "frequency": "monthly",
        "title": "Euro Area Negotiated Wages (YoY, %)",
        "description": (
            "Negotiated wages measure annual growth in collectively agreed wages "
            "across the Euro Area. Wage settlements are a major driver of services "
            "inflation and household income growth, so this indicator is closely "
            "monitored by the ECB."
        ),
        "source": "Source: European Central Bank (ECB)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Labor Productivity YoY": {
        "data_func": get_euro_labor_productivity_yoy_data,
        "frequency": "quarterly",
        "title": "Euro Area Labour Productivity (YoY, %)",
        "description": (
            "Labour productivity measures the amount of output produced per hour "
            "worked. Higher productivity allows wages to rise without generating "
            "the same inflation pressure, making it important for assessing "
            "sustainable growth and underlying inflation."
        ),
        "source": "Source: European Central Bank (ECB)",
        "decimals": 2,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "House Price Index YoY": {
        "data_func": get_euro_house_price_index_yoy_data,
        "frequency": "quarterly",
        "title": "Euro Area House Price Index (YoY, %)",
        "description": (
            "House-price growth measures annual changes in residential property "
            "prices across the Euro Area. It provides insight into housing-market "
            "conditions, household wealth, credit growth, and the impact of "
            "interest rates on property demand."
        ),
        "source": "Source: European Central Bank (ECB)",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "GDP QoQ": {
        "data_func": get_euro_gdp_qoq_data,
        "frequency": "quarterly",
        "title": "Euro Area Real GDP Growth (QoQ, %)",
        "description": (
            "Euro Area GDP QoQ measures the quarter-over-quarter change in real "
            "economic output. It captures short-term momentum in consumption, "
            "investment, government spending, and net trade across the currency bloc."
        ),
        "source": "Source: Eurostat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "GDP YoY": {
        "data_func": get_euro_gdp_yoy_data,
        "frequency": "quarterly",
        "title": "Euro Area Real GDP Growth (YoY, %)",
        "description": (
            "Euro Area GDP YoY measures real economic growth compared with the same "
            "quarter one year earlier. It provides a smoother view of the underlying "
            "growth trend than quarter-over-quarter data."
        ),
        "source": "Source: Eurostat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Retail Sales MoM": {
        "data_func": get_euro_retail_sales_mom_data,
        "frequency": "monthly",
        "title": "Euro Area Retail Sales Volume (MoM, %)",
        "description": (
            "Retail Sales MoM tracks the monthly change in retail trade volumes "
            "across the Euro Area. It is a timely gauge of household consumption "
            "momentum and consumer demand."
        ),
        "source": "Source: Eurostat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Industrial Production MoM": {
        "data_func": get_euro_industrial_production_mom_data,
        "frequency": "monthly",
        "title": "Industrial Production (MoM, %)",
        "description": (
            "Industrial production measures changes in factory, utility, and mining "
            "output across the Euro Area. It is a key indicator of manufacturing "
            "momentum and can provide an early signal of changes in growth."
        ),
        "source": "Source: Eurostat",
        "decimals": 1,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "percent",
        "unit_label": "%",
        "change_type": "percentage_points",
        "compatible_group": "percent",
    },
    "Economic Sentiment Indicator": {
        "data_func": get_euro_economic_sentiment_data,
        "frequency": "monthly",
        "title": "Euro Area Economic Sentiment Indicator",
        "description": (
            "The Economic Sentiment Indicator is a composite survey measure from "
            "the European Commission. It combines confidence readings from industry, "
            "services, consumers, retail trade, and construction to provide a "
            "forward-looking view of Euro Area activity."
        ),
        "source": "Source: European Commission Business and Consumer Surveys",
        "decimals": 2,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "index",
        "unit_label": "",
        "change_type": "absolute",
        "compatible_group": "index",
    },
    "Trade Balance": {
        "data_func": get_euro_trade_balance_data,
        "frequency": "monthly",
        "title": "Euro Area Trade Balance (€ Millions)",
        "description": (
            "The trade balance measures the difference between Euro Area exports "
            "and imports of goods. It provides insight into external demand, "
            "competitiveness, and the contribution of trade to economic growth."
        ),
        "source": "Source: Eurostat",
        "decimals": 0,
        "is_policy_rate": False,
        "tickformat_override": None,
        "unit_type": "currency_scale",
        "unit_label": "",
        "change_type": "absolute",
        "compatible_group": "currency_scale",
    },
}
# This connector reports effective ECB policy-rate events, not sampled prices.
# Persistence is explicit, bounded, and never applied to unrelated macro series.
EURO_ECONOMY_MAP["Interest Rate"]["carry_forward_days"] = 1096
EURO_ECONOMY_MAP["Interest Rate"]["date_convention"] = "effective policy-rate dates; bounded state persistence; publication timing unverified"
