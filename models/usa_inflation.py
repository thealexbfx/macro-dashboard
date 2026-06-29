import streamlit as st

from indicators.usa import (
    get_usa_cpi_yoy_data,
    get_usa_core_cpi_yoy_data,
    get_usa_pce_yoy_data,
    get_usa_core_pce_yoy_data,
    get_usa_ppi_yoy_data,
    get_usa_core_ppi_yoy_data,
    get_usa_average_hourly_earnings_yoy_data,
    get_usa_eci_total_compensation_yoy_data,
    get_usa_eci_wages_salaries_yoy_data,
)

from models.macro_engine import analyze_weighted_pillar

INFLATION_LABELS = {
    2: "Strongly Accelerating",
    1: "Accelerating",
    0: "Stable",
    -1: "Cooling",
    -2: "Strongly Cooling",
}


def classify_inflation_regime(score):
    if score >= 1.00:
        return "Strong Inflationary Pressure"
    elif score >= 0.35:
        return "Inflation Rising"
    elif score <= -1.00:
        return "Disinflation"
    elif score <= -0.35:
        return "Inflation Cooling"
    else:
        return "Inflation Stable"


USA_INFLATION_INDICATORS = {
    "CPI YoY": {
        "func": get_usa_cpi_yoy_data,
        "weight": 0.10,
        "component": "Consumer Prices",
        "freq": "monthly",
        "method": "momentum",
        "labels": INFLATION_LABELS,
    },
    "Core CPI YoY": {
        "func": get_usa_core_cpi_yoy_data,
        "weight": 0.10,
        "component": "Consumer Prices",
        "freq": "monthly",
        "method": "momentum",
        "labels": INFLATION_LABELS,
    },
    "PCE YoY": {
        "func": get_usa_pce_yoy_data,
        "weight": 0.10,
        "component": "Consumer Prices",
        "freq": "monthly",
        "method": "momentum",
        "labels": INFLATION_LABELS,
    },
    "Core PCE YoY": {
        "func": get_usa_core_pce_yoy_data,
        "weight": 0.10,
        "component": "Consumer Prices",
        "freq": "monthly",
        "method": "momentum",
        "labels": INFLATION_LABELS,
    },

    "PPI YoY": {
        "func": get_usa_ppi_yoy_data,
        "weight": 0.10,
        "component": "Producer Prices",
        "freq": "monthly",
        "method": "momentum",
        "labels": INFLATION_LABELS,
    },
    "Core PPI YoY": {
        "func": get_usa_core_ppi_yoy_data,
        "weight": 0.10,
        "component": "Producer Prices",
        "freq": "monthly",
        "method": "momentum",
        "labels": INFLATION_LABELS,
    },

    "Average Hourly Earnings YoY": {
        "func": get_usa_average_hourly_earnings_yoy_data,
        "weight": 0.15,
        "component": "Wage Inflation",
        "freq": "monthly",
        "method": "momentum",
        "labels": INFLATION_LABELS,
    },
    "ECI Total Compensation YoY": {
        "func": get_usa_eci_total_compensation_yoy_data,
        "weight": 0.125,
        "component": "Wage Inflation",
        "freq": "quarterly",
        "method": "momentum",
        "labels": INFLATION_LABELS,
    },
    "ECI Wages & Salaries YoY": {
        "func": get_usa_eci_wages_salaries_yoy_data,
        "weight": 0.125,
        "component": "Wage Inflation",
        "freq": "quarterly",
        "method": "momentum",
        "labels": INFLATION_LABELS,
    },
}


@st.cache_data(ttl=1800, show_spinner=False)
def analyze_usa_inflation():
    return analyze_weighted_pillar(
        USA_INFLATION_INDICATORS,
        regime_func=classify_inflation_regime,
    )