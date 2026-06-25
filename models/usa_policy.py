import streamlit as st
import pandas as pd

from indicators.usa import (
    get_usa_interest_rate_data,
    get_usa_core_pce_yoy_data,
    get_usa_2yr_yield_data,
    get_usa_10yr_yield_data,
)

from models.macro_engine import analyze_weighted_pillar


POLICY_STANCE_LABELS = {
    2: "Highly Restrictive",
    1: "Restrictive",
    0: "Neutral",
    -1: "Accommodative",
    -2: "Highly Accommodative",
}

POLICY_DIRECTION_LABELS = {
    2: "Rapidly Tightening",
    1: "Tightening",
    0: "Stable",
    -1: "Easing",
    -2: "Rapidly Easing",
}


def classify_policy_stance(score):
    if score >= 1.00:
        return "Highly Restrictive"
    elif score >= 0.35:
        return "Restrictive"
    elif score <= -1.00:
        return "Highly Accommodative"
    elif score <= -0.35:
        return "Accommodative"
    else:
        return "Neutral"


def classify_policy_direction(score):
    if score >= 1.00:
        return "Rapidly Tightening"
    elif score >= 0.35:
        return "Tightening"
    elif score <= -1.00:
        return "Rapidly Easing"
    elif score <= -0.35:
        return "Easing"
    else:
        return "Stable"


def get_usa_real_policy_rate_data():
    fed = get_usa_interest_rate_data().copy()
    core_pce = get_usa_core_pce_yoy_data().copy()

    fed["date"] = pd.to_datetime(fed["date"])
    core_pce["date"] = pd.to_datetime(core_pce["date"])

    fed = fed.sort_values("date")
    core_pce = core_pce.sort_values("date")

    merged = pd.merge_asof(
        fed,
        core_pce,
        on="date",
        direction="backward",
        suffixes=("_fed", "_core_pce"),
    )

    merged["value"] = merged["value_fed"] - merged["value_core_pce"]

    return merged[["date", "value"]].dropna()


USA_POLICY_STANCE_INDICATORS = {
    "Federal Funds Rate": {
        "func": get_usa_interest_rate_data,
        "weight": 0.50,
        "component": "Policy Rates",
        "freq": "daily",
        "method": "level",
        "labels": POLICY_STANCE_LABELS,
    },
    "US 2Y Treasury Yield": {
        "func": get_usa_2yr_yield_data,
        "weight": 0.15,
        "component": "Market Rates",
        "freq": "daily",
        "method": "level",
        "labels": POLICY_STANCE_LABELS,
    },
    "US 10Y Treasury Yield": {
        "func": get_usa_10yr_yield_data,
        "weight": 0.15,
        "component": "Market Rates",
        "freq": "daily",
        "method": "level",
        "labels": POLICY_STANCE_LABELS,
    },
    "Real Policy Rate": {
        "func": get_usa_real_policy_rate_data,
        "weight": 0.20,
        "component": "Real Rates",
        "freq": "daily",
        "method": "level",
        "labels": POLICY_STANCE_LABELS,
    },
}


USA_POLICY_DIRECTION_INDICATORS = {
    "Federal Funds Rate": {
        "func": get_usa_interest_rate_data,
        "weight": 0.50,
        "component": "Policy Rates",
        "freq": "policy",
        "method": "momentum",
        "labels": POLICY_DIRECTION_LABELS,
        "thresholds": {
            "strong_down": -0.50,
            "down": -0.10,
            "up": 0.10,
            "strong_up": 0.50,
        },
    },
    "US 2Y Treasury Yield": {
        "func": get_usa_2yr_yield_data,
        "weight": 0.15,
        "component": "Market Rates",
        "freq": "policy",
        "method": "momentum",
        "labels": POLICY_DIRECTION_LABELS,
        "thresholds": {
            "strong_down": -1.00,
            "down": -0.25,
            "up": 0.25,
            "strong_up": 1.00,
        },
    },
    "US 10Y Treasury Yield": {
        "func": get_usa_10yr_yield_data,
        "weight": 0.15,
        "component": "Market Rates",
        "freq": "policy",
        "method": "momentum",
        "labels": POLICY_DIRECTION_LABELS,
        "thresholds": {
            "strong_down": -1.00,
            "down": -0.25,
            "up": 0.25,
            "strong_up": 1.00,
        },
    },
    "Real Policy Rate": {
        "func": get_usa_real_policy_rate_data,
        "weight": 0.20,
        "component": "Real Rates",
        "freq": "policy",
        "method": "momentum",
        "labels": POLICY_DIRECTION_LABELS,
        "thresholds": {
            "strong_down": -0.50,
            "down": -0.10,
            "up": 0.10,
            "strong_up": 0.50,
        },
    },
}


@st.cache_data(ttl=1800)
def analyze_usa_policy_stance():
    return analyze_weighted_pillar(
        USA_POLICY_STANCE_INDICATORS,
        regime_func=classify_policy_stance,
    )


@st.cache_data(ttl=1800)
def analyze_usa_policy_direction():
    return analyze_weighted_pillar(
        USA_POLICY_DIRECTION_INDICATORS,
        regime_func=classify_policy_direction,
    )


@st.cache_data(ttl=1800)
def analyze_usa_policy():
    stance = analyze_usa_policy_stance()
    direction = analyze_usa_policy_direction()

    return {
        "stance": stance,
        "direction": direction,
        "summary": f"{stance['regime']} / {direction['regime']}",
    }