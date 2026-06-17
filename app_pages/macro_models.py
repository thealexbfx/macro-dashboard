# app_pages/macro_models.py

import pandas as pd


def trend_to_score(trend):
    if trend == "up":
        return 1
    if trend == "down":
        return -1
    return 0


def score_signal(score, positive_label, negative_label, neutral_label="Neutral"):
    if score >= 2:
        return positive_label
    if score <= -2:
        return negative_label
    return neutral_label


def calculate_group_signal(results, indicators, positive_label, negative_label):
    score = 0
    used_indicators = []

    for indicator in indicators:
        if indicator in results:
            trend = results[indicator].get("trend")
            score += trend_to_score(trend)
            used_indicators.append(indicator)

    signal = score_signal(
        score,
        positive_label=positive_label,
        negative_label=negative_label,
    )

    return {
        "signal": signal,
        "score": score,
        "indicators_used": used_indicators,
    }


def calculate_policy_signal(results, policy_indicator, restrictive_threshold):
    if policy_indicator not in results:
        return {
            "signal": "Unavailable",
            "latest": None,
        }

    latest = results[policy_indicator].get("latest")

    if latest is None:
        signal = "Unavailable"
    elif latest >= restrictive_threshold or latest >= restrictive_threshold / 100:
        signal = "Restrictive"
    else:
        signal = "Accommodative"

    return {
        "signal": signal,
        "latest": latest,
    }


def build_country_macro_signal(country, results):
    country_configs = {
        "United States": {
            "growth": [
                "GDP Growth Rate",
                "Retail Sales MoM",
                "Industrial Production MoM",
                "Housing Starts MoM",
                "Non Farm Payrolls",
            ],
            "inflation": [
                "CPI YoY",
                "Core CPI YoY",
                "PCE YoY",
                "Core PCE YoY",
            ],
            "policy_indicator": "Federal Funds Rate",
            "restrictive_threshold": 4.0,
        },
        "United Kingdom": {
            "growth": [
                "GDP QoQ",
                "Retail Sales MoM",
                "Industrial Production MoM",
                "Vacancies",
            ],
            "inflation": [
                "CPI YoY",
                "Core CPI YoY",
            ],
            "policy_indicator": "Bank Rate",
            "restrictive_threshold": 4.0,
        },
        "Euro Area": {
            "growth": [
                "GDP QoQ",
                "GDP YoY",
                "Retail Sales MoM",
                "Industrial Production MoM",
            ],
            "inflation": [
                "HICP YoY",
                "Core HICP YoY",
            ],
            "policy_indicator": "Interest Rate",
            "restrictive_threshold": 3.0,
        },
        "Japan": {
            "growth": [
                "GDP Growth Rate",
                "Unemployment Rate",
            ],
            "inflation": [
                "CPI YoY",
                "Core CPI YoY",
            ],
            "policy_indicator": "Interest Rate",
            "restrictive_threshold": 2.0,
        },
    }

    config = country_configs[country]

    growth = calculate_group_signal(
        results,
        config["growth"],
        positive_label="Improving",
        negative_label="Slowing",
    )

    inflation = calculate_group_signal(
        results,
        config["inflation"],
        positive_label="Rising",
        negative_label="Cooling",
    )

    policy = calculate_policy_signal(
        results,
        config["policy_indicator"],
        config["restrictive_threshold"],
    )

    return {
        "Country": country,
        "Growth": growth["signal"],
        "Growth Score": growth["score"],
        "Inflation": inflation["signal"],
        "Inflation Score": inflation["score"],
        "Policy": policy["signal"],
        "Policy Rate": policy["latest"],
    }


def build_global_macro_table(usa, uk, euro, japan):
    rows = [
        build_country_macro_signal("United States", usa),
        build_country_macro_signal("United Kingdom", uk),
        build_country_macro_signal("Euro Area", euro),
        build_country_macro_signal("Japan", japan),
    ]

    return pd.DataFrame(rows)