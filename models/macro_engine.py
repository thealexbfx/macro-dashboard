import pandas as pd


def prepare_model_df(df, start_date="2000-01-01"):
    df = df.dropna().sort_values("date").copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] >= pd.to_datetime(start_date)]
    return df.reset_index(drop=True)


def get_window_size(freq):
    if freq == "quarterly":
        return 2
    if freq == "policy":
        return 30
    return 3

def calculate_historical_changes(df, window):
    changes = []

    for i in range(window * 2, len(df) + 1):
        latest_avg = df["value"].iloc[i - window:i].mean()
        previous_avg = df["value"].iloc[i - window * 2:i - window].mean()
        changes.append(latest_avg - previous_avg)

    return pd.Series(changes).dropna()


def calculate_historical_levels(df):
    return df["value"].dropna()


def score_by_percentile(value, historical_values, labels=None):
    if historical_values.empty:
        return 0, "Insufficient Data", None

    percentile = (historical_values <= value).mean()

    if labels is None:
        labels = {
            2: "Strongly Improving",
            1: "Improving",
            0: "Neutral",
            -1: "Deteriorating",
            -2: "Strongly Deteriorating",
        }

    if percentile >= 0.90:
        score = 2
    elif percentile >= 0.70:
        score = 1
    elif percentile >= 0.30:
        score = 0
    elif percentile >= 0.10:
        score = -1
    else:
        score = -2

    return score, labels[score], percentile

def calculate_percent_change(latest_avg, previous_avg):
    if previous_avg == 0:
        return 0

    return ((latest_avg - previous_avg) / abs(previous_avg)) * 100

def calculate_historical_pct_changes(df, window):
    changes = []

    for i in range(window * 2, len(df) + 1):
        latest_avg = df["value"].iloc[i - window:i].mean()
        previous_avg = df["value"].iloc[i - window * 2:i - window].mean()

        if previous_avg == 0:
            continue

        pct_change = ((latest_avg - previous_avg) / abs(previous_avg)) * 100
        changes.append(pct_change)

    return pd.Series(changes).dropna()
    
def analyze_momentum_indicator(df, freq="monthly", inverse=False, start_date="2000-01-01", labels=None, thresholds=None, method="momentum",):
    df = prepare_model_df(df, start_date=start_date)
    window = get_window_size(freq)

    if len(df) < window * 2 + 12:
        return {
            "score": 0,
            "direction": "Insufficient Data",
            "latest_avg": None,
            "previous_avg": None,
            "change": None,
            "percentile": None,
            "method": method,
        }

    latest_avg = df["value"].iloc[-window:].mean()
    previous_avg = df["value"].iloc[-window * 2:-window].mean()
    if method == "pct_change":
        current_change = calculate_percent_change(
            latest_avg,
            previous_avg,
        )
    else:
        current_change = latest_avg - previous_avg

    if method == "pct_change":
        historical_changes = calculate_historical_pct_changes(df, window)
    else:
        historical_changes = calculate_historical_changes(df, window)

    if inverse:
        current_change = -current_change
        historical_changes = -historical_changes

    if thresholds:
        strong_down = thresholds["strong_down"]
        down = thresholds["down"]
        up = thresholds["up"]
        strong_up = thresholds["strong_up"]

        if current_change >= strong_up:
            score = 2
        elif current_change >= up:
            score = 1
        elif current_change <= strong_down:
            score = -2
        elif current_change <= down:
            score = -1
        else:
            score = 0

        if labels is None:
            labels = {
                2: "Strongly Improving",
                1: "Improving",
                0: "Neutral",
                -1: "Deteriorating",
                -2: "Strongly Deteriorating",
            }

        percentile = (historical_changes <= current_change).mean()

        return {
            "score": score,
            "direction": labels[score],
            "latest_avg": latest_avg,
            "previous_avg": previous_avg,
            "change": current_change,
            "percentile": percentile,
            "method": method,
        }

    score, direction, percentile = score_by_percentile(
        current_change,
        historical_changes,
        labels=labels,
    )

    return {
        "score": score,
        "direction": direction,
        "latest_avg": latest_avg,
        "previous_avg": previous_avg,
        "change": current_change,
        "percentile": percentile,
        "method": method,
    }

def analyze_level_indicator(df, inverse=False, start_date="2000-01-01", labels=None):
    df = prepare_model_df(df, start_date=start_date)

    if len(df) < 36:
        return {
            "score": 0,
            "direction": "Insufficient Data",
            "latest_avg": None,
            "previous_avg": None,
            "change": None,
            "percentile": None,
            "method": "level",
        }

    latest_value = df["value"].iloc[-1]
    historical_levels = calculate_historical_levels(df)

    value_for_scoring = latest_value

    if inverse:
        value_for_scoring = -latest_value
        historical_levels = -historical_levels

    if labels is None:
        labels = {
            2: "Strongly Positive",
            1: "Positive",
            0: "Neutral",
            -1: "Weak",
            -2: "Very Weak",
        }

    score, direction, percentile = score_by_percentile(
        value_for_scoring,
        historical_levels,
        labels=labels,
    )

    return {
        "score": score,
        "direction": direction,
        "latest_avg": latest_value,
        "previous_avg": None,
        "change": None,
        "percentile": percentile,
        "method": "level",
    }


def analyze_indicator(df, freq="monthly", inverse=False, start_date="2000-01-01", method="momentum", labels=None, thresholds=None):
    if method == "level":
        return analyze_level_indicator(
            df=df,
            inverse=inverse,
            start_date=start_date,
            labels=labels,
        )

    return analyze_momentum_indicator(
        df=df,
        freq=freq,
        inverse=inverse,
        start_date=start_date,
        labels=labels,
        thresholds=thresholds,
        method=method,
    )


def classify_breadth(scores):
    valid_scores = [s for s in scores if s is not None]

    improving = sum(1 for s in valid_scores if s > 0)
    deteriorating = sum(1 for s in valid_scores if s < 0)
    total = len(valid_scores)

    if total == 0:
        return "Insufficient Data", 0, 0, 0

    improving_pct = improving / total

    if improving_pct >= 0.65:
        breadth = "Broad"
    elif improving_pct >= 0.40:
        breadth = "Mixed"
    else:
        breadth = "Narrow"

    return breadth, improving, deteriorating, total


def classify_growth_regime(score):
    if score >= 1.00:
        return "Strong Expansion"
    elif score >= 0.35:
        return "Expansion"
    elif score <= -1.00:
        return "Contraction"
    elif score <= -0.35:
        return "Slowing"
    else:
        return "Neutral"


def analyze_weighted_pillar(indicators, regime_func=classify_growth_regime):
    rows = []
    component_scores = {}

    for name, config in indicators.items():
        try:
            df = config["func"]()

            result = analyze_indicator(
                df=df,
                freq=config.get("freq", "monthly"),
                inverse=config.get("inverse", False),
                start_date=config.get("start_date", "2000-01-01"),
                method=config.get("method", "momentum"),
                labels=config.get("labels"),
                thresholds=config.get("thresholds"),
            )

            weighted_score = result["score"] * config["weight"]
            component = config["component"]

            component_scores[component] = component_scores.get(component, 0) + weighted_score

            rows.append({
                "Indicator": name,
                "Component": component,
                "Method": result["method"],
                "Weight": config["weight"],
                "Score": result["score"],
                "Weighted Score": weighted_score,
                "Direction": result["direction"],
                "Latest Avg": round(result["latest_avg"], 2) if result["latest_avg"] is not None else None,
                "Previous Avg": round(result["previous_avg"], 2) if result["previous_avg"] is not None else None,
                "Change": round(result["change"], 2) if result["change"] is not None else None,
                "Percentile": round(result["percentile"], 3) if result["percentile"] is not None else None,
            })

        except Exception as e:
            rows.append({
                "Indicator": name,
                "Component": config.get("component"),
                "Method": config.get("method", "momentum"),
                "Weight": config.get("weight"),
                "Score": 0,
                "Weighted Score": 0,
                "Direction": f"Error: {e}",
                "Latest Avg": None,
                "Previous Avg": None,
                "Change": None,
                "Percentile": None,
            })

    df_results = pd.DataFrame(rows)

    total_score = df_results["Weighted Score"].sum()
    breadth, improving, deteriorating, total = classify_breadth(df_results["Score"].tolist())
    regime = regime_func(total_score)

    return {
        "total_score": total_score,
        "regime": regime,
        "breadth": breadth,
        "improving": improving,
        "deteriorating": deteriorating,
        "total_indicators": total,
        "component_scores": component_scores,
        "details": df_results,
    }