import streamlit as st

from indicators.usa import (
    get_usa_gdp_qoq_data,
    get_usa_industrial_production_mom_data,
    get_usa_capacity_utilization_data,
    get_usa_durable_goods_orders_mom_data,
    get_usa_retail_sales_mom_data,
    get_usa_personal_consumption_mom_data,
    get_usa_personal_income_mom_data,
    get_usa_saving_rate_data,
    get_usa_nfp_data,
    get_usa_unemployment_rate_data,
    get_usa_initial_jobless_claims_data,
    get_usa_housing_starts_mom_data,
    get_usa_building_permits_mom_data,
    get_usa_new_home_sales_mom_data,
    get_usa_michigan_consumer_sentiment_data,
)

from models.macro_engine import analyze_weighted_pillar


USA_GROWTH_INDICATORS = {
    "GDP Growth Rate": {
        "func": get_usa_gdp_qoq_data,
        "weight": 0.075,
        "method": "level",
        "component": "Activity",
        "freq": "quarterly",
    },
    "Industrial Production MoM": {
        "func": get_usa_industrial_production_mom_data,
        "weight": 0.075,
        "component": "Activity",
        "freq": "monthly",
    },
    "Capacity Utilization": {
        "func": get_usa_capacity_utilization_data,
        "weight": 0.075,
        "component": "Activity",
        "freq": "monthly",
    },
    "Durable Goods Orders MoM": {
        "func": get_usa_durable_goods_orders_mom_data,
        "weight": 0.075,
        "component": "Activity",
        "freq": "monthly",
    },

    "Retail Sales MoM": {
        "func": get_usa_retail_sales_mom_data,
        "weight": 0.0625,
        "component": "Consumer",
        "freq": "monthly",
    },
    "Personal Consumption MoM": {
        "func": get_usa_personal_consumption_mom_data,
        "weight": 0.0625,
        "component": "Consumer",
        "freq": "monthly",
    },
    "Personal Income MoM": {
        "func": get_usa_personal_income_mom_data,
        "weight": 0.0625,
        "component": "Consumer",
        "freq": "monthly",
    },
    "Saving Rate": {
        "func": get_usa_saving_rate_data,
        "weight": 0.0625,
        "component": "Consumer",
        "freq": "monthly",
        "inverse": True,
    },

    "Non Farm Payrolls": {
        "func": get_usa_nfp_data,
        "weight": 0.10,
        "component": "Labor",
        "freq": "monthly",
    },
    "Unemployment Rate": {
        "func": get_usa_unemployment_rate_data,
        "weight": 0.08,
        "component": "Labor",
        "freq": "monthly",
        "inverse": True,
    },
    "Initial Jobless Claims": {
        "func": get_usa_initial_jobless_claims_data,
        "weight": 0.07,
        "component": "Labor",
        "freq": "weekly",
        "inverse": True,
    },

    "Housing Starts MoM": {
        "func": get_usa_housing_starts_mom_data,
        "weight": 0.05,
        "component": "Housing",
        "freq": "monthly",
    },
    "Building Permits MoM": {
        "func": get_usa_building_permits_mom_data,
        "weight": 0.05,
        "component": "Housing",
        "freq": "monthly",
    },
    "New Home Sales MoM": {
        "func": get_usa_new_home_sales_mom_data,
        "weight": 0.05,
        "component": "Housing",
        "freq": "monthly",
    },

    "Michigan Consumer Sentiment": {
        "func": get_usa_michigan_consumer_sentiment_data,
        "weight": 0.05,
        "component": "Sentiment",
        "freq": "monthly",
    },
}


@st.cache_data(ttl=1800)
def analyze_usa_growth():
    return analyze_weighted_pillar(USA_GROWTH_INDICATORS)