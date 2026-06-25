import streamlit as st

from indicators.usa import (
    get_usa_fed_balance_sheet_data,
    get_usa_chicago_fed_nfci_data,
)

from models.macro_engine import analyze_weighted_pillar


LIQUIDITY_LABELS = {
    2: "Rapid Expansion",
    1: "Expansion",
    0: "Neutral",
    -1: "Contraction",
    -2: "Rapid Contraction",
}


def classify_liquidity_regime(score):
    if score >= 1.00:
        return "Abundant Liquidity"
    elif score >= 0.35:
        return "Supportive Liquidity"
    elif score <= -1.00:
        return "Liquidity Drain"
    elif score <= -0.35:
        return "Restrictive Liquidity"
    else:
        return "Neutral Liquidity"


USA_LIQUIDITY_INDICATORS = {
    "Fed Balance Sheet": {
        "func": get_usa_fed_balance_sheet_data,
        "weight": 0.70,
        "component": "Central Bank Liquidity",
        "freq": "policy",
        "method": "pct_change",
        "labels": LIQUIDITY_LABELS,
    },
    "Chicago Fed NFCI": {
        "func": get_usa_chicago_fed_nfci_data,
        "weight": 0.30,
        "component": "Financial Conditions",
        "freq": "policy",
        "method": "momentum",
        "inverse": True,
        "labels": LIQUIDITY_LABELS,
    },
}


@st.cache_data(ttl=1800)
def analyze_usa_liquidity():
    return analyze_weighted_pillar(
        USA_LIQUIDITY_INDICATORS,
        regime_func=classify_liquidity_regime,
    )