import streamlit as st

from indicators.usa import (
    get_usa_nfp_data,
    get_usa_unemployment_rate_data,
    get_usa_labor_force_participation_data,
    get_usa_jolts_job_openings_data,
    get_usa_initial_jobless_claims_data,
    get_usa_average_hourly_earnings_yoy_data,
)

from models.macro_engine import analyze_weighted_pillar


LABOR_LABELS = {
    2: "Strongly Tightening",
    1: "Tightening",
    0: "Balanced",
    -1: "Softening",
    -2: "Strongly Softening",
}


def classify_labor_regime(score):
    if score >= 1.00:
        return "Very Tight"
    elif score >= 0.35:
        return "Tight"
    elif score <= -1.00:
        return "Weakening"
    elif score <= -0.35:
        return "Softening"
    else:
        return "Balanced"


USA_LABOR_INDICATORS = {
    # Employment Growth: 30%
    "Non Farm Payrolls": {
        "func": get_usa_nfp_data,
        "weight": 0.30,
        "component": "Employment Growth",
        "freq": "monthly",
        "method": "momentum",
        "labels": LABOR_LABELS,
    },

    # Labor Market Slack: 25%
    "Unemployment Rate": {
        "func": get_usa_unemployment_rate_data,
        "weight": 0.25,
        "component": "Labor Market Slack",
        "freq": "monthly",
        "method": "momentum",
        "inverse": True,
        "labels": LABOR_LABELS,
    },
    "Labor Force Participation Rate": {
        "func": get_usa_labor_force_participation_data,
        "weight": 0.05,
        "component": "Labor Market Slack",
        "freq": "monthly",
        "method": "momentum",
        "labels": LABOR_LABELS,
        "thresholds": {
            "strong_down": -0.50,
            "down": -0.25,
            "up": 0.25,
            "strong_up": 0.50,
        },
    },

    # Labor Demand: 15%
    "JOLTS Job Openings": {
        "func": get_usa_jolts_job_openings_data,
        "weight": 0.15,
        "component": "Labor Demand",
        "freq": "monthly",
        "method": "momentum",
        "labels": LABOR_LABELS,
    },
    "Initial Jobless Claims": {
        "func": get_usa_initial_jobless_claims_data,
        "weight": 0.15,
        "component": "Labor Demand",
        "freq": "weekly",
        "method": "momentum",
        "inverse": True,
        "labels": LABOR_LABELS,
    },

    # Wage Pressure: 10%
    "Average Hourly Earnings YoY": {
        "func": get_usa_average_hourly_earnings_yoy_data,
        "weight": 0.10,
        "component": "Wage Pressure",
        "freq": "monthly",
        "method": "momentum",
        "labels": LABOR_LABELS,
    },
}


@st.cache_data(ttl=1800)
def analyze_usa_labor():
    return analyze_weighted_pillar(
        USA_LABOR_INDICATORS,
        regime_func=classify_labor_regime,
    )