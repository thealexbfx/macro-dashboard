"""Reusable indicator-processing logic for the MacroLens Engine."""

import pandas as pd

from macro_engine.models.indicator import IndicatorConfig


REQUIRED_COLUMNS = {"date", "value"}


def prepare_indicator_data(
    data: pd.DataFrame,
    config: IndicatorConfig,
) -> pd.DataFrame:
    """
    Validate and standardize raw indicator data.

    The function does not calculate scores. It only ensures that the
    Indicator Engine receives a clean chronological date/value series.
    """
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame.")

    missing_columns = REQUIRED_COLUMNS.difference(data.columns)

    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"data is missing required columns: {missing}")

    cleaned = data[["date", "value"]].copy()

    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    cleaned["value"] = pd.to_numeric(cleaned["value"], errors="coerce")

    cleaned = cleaned.dropna(subset=["date", "value"])
    cleaned = cleaned.sort_values("date")
    cleaned = cleaned.drop_duplicates(subset="date", keep="last")
    cleaned = cleaned.reset_index(drop=True)

    if cleaned.empty:
        raise ValueError(
            f"No valid observations remain for {config.indicator_id}."
        )

    return cleaned
    
def calculate_state_value(
    data: pd.DataFrame,
    config: IndicatorConfig,
) -> float:
    """
    Calculate the indicator's current state value.

    Version 1 uses the average of the most recent observations defined
    by config.state_window.
    """
    if len(data) < config.state_window:
        raise ValueError(
            f"{config.indicator_id} requires at least "
            f"{config.state_window} observations to calculate state."
        )

    state_value = data["value"].tail(config.state_window).mean()

    return float(state_value)
    
def calculate_trend_value(
    data: pd.DataFrame,
    config: IndicatorConfig,
) -> float:
    """
    Compare the latest state window with the preceding trend window.
    """
    required_observations = config.state_window + config.trend_window

    if len(data) < required_observations:
        raise ValueError(
            f"{config.indicator_id} requires at least "
            f"{required_observations} observations to calculate trend."
        )

    latest_average = data["value"].tail(config.state_window).mean()

    previous_average = (
        data["value"]
        .iloc[-required_observations:-config.state_window]
        .mean()
    )

    return float(latest_average - previous_average)
    
def calculate_historical_percentile(
    data: pd.DataFrame,
    config: IndicatorConfig,
) -> float:
    """
    Rank the current state against comparable historical rolling states.

    Returns a percentile from 0 to 100.
    """
    if len(data) < config.minimum_history:
        raise ValueError(
            f"{config.indicator_id} requires at least "
            f"{config.minimum_history} observations for historical context."
        )

    comparison_data = data

    if config.historical_lookback is not None:
        comparison_data = data.tail(config.historical_lookback)

    rolling_state = (
        comparison_data["value"]
        .rolling(window=config.state_window)
        .mean()
        .dropna()
    )

    current_state = rolling_state.iloc[-1]
    percentile = (rolling_state <= current_state).mean() * 100

    return float(percentile)
    
def calculate_state_score(
    historical_percentile: float,
    config: IndicatorConfig,
) -> float:
    """
    Convert a 0–100 historical percentile into a -1 to +1 state score.
    """
    score = (historical_percentile - 50.0) / 50.0

    if config.economic_direction == "negative":
        score *= -1

    return float(max(-1.0, min(1.0, score)))


def classify_state(score: float) -> str:
    """Convert a state score into an explainable economic label."""
    if score >= 0.60:
        return "Very Strong"

    if score >= 0.20:
        return "Strong"

    if score > -0.20:
        return "Normal"

    if score > -0.60:
        return "Weak"

    return "Very Weak"
    
def calculate_trend_percentile(
    data: pd.DataFrame,
    config: IndicatorConfig,
) -> float:
    """
    Rank the current trend value against historical trend values.

    A trend value compares the latest state window with the immediately
    preceding trend window. Returns a percentile from 0 to 100.
    """
    required_observations = config.state_window + config.trend_window

    if len(data) < max(config.minimum_history, required_observations):
        raise ValueError(
            f"{config.indicator_id} does not have enough history "
            "to calculate trend context."
        )

    comparison_data = data

    if config.historical_lookback is not None:
        comparison_data = data.tail(config.historical_lookback)

    state_series = (
        comparison_data["value"]
        .rolling(window=config.state_window)
        .mean()
    )

    previous_state_series = state_series.shift(config.trend_window)

    historical_trends = (state_series - previous_state_series).dropna()

    current_trend = historical_trends.iloc[-1]
    percentile = (historical_trends <= current_trend).mean() * 100

    return float(percentile)


def calculate_trend_score(
    trend_percentile: float,
    config: IndicatorConfig,
) -> float:
    """
    Convert a trend percentile into a -1 to +1 directional score.
    """
    score = (trend_percentile - 50.0) / 50.0

    if config.economic_direction == "negative":
        score *= -1

    return float(max(-1.0, min(1.0, score)))


def classify_trend(score: float) -> str:
    """Convert a trend score into a directional label."""
    if score >= 0.20:
        return "Improving"

    if score <= -0.20:
        return "Deteriorating"

    return "Stable"

def calculate_freshness_score(
    latest_date: pd.Timestamp,
    config: IndicatorConfig,
    reference_date: pd.Timestamp | None = None,
) -> tuple[float, list[str]]:
    """
    Score whether the latest observation is reasonably current.

    The limits allow for normal publication delays.
    """
    reference_date = reference_date or pd.Timestamp.today().normalize()
    latest_date = pd.Timestamp(latest_date).normalize()

    age_days = max((reference_date - latest_date).days, 0)

    freshness_ranges = {
        "daily": (3, 10, 21),
        "weekly": (10, 21, 42),
        "monthly": (45, 75, 120),
        "quarterly": (120, 180, 270),
        "annual": (400, 500, 650),
    }

    fresh_limit, aging_limit, stale_limit = freshness_ranges[config.frequency]

    if age_days <= fresh_limit:
        return 1.0, []

    if age_days <= aging_limit:
        return 0.85, ["aging_data"]

    if age_days >= stale_limit:
        return 0.0, ["stale_data"]

    score = 0.85 * (
        1.0
        - (age_days - aging_limit)
        / (stale_limit - aging_limit)
    )

    return float(max(score, 0.0)), ["aging_data"]
    
def calculate_continuity_score(
    data: pd.DataFrame,
    config: IndicatorConfig,
) -> tuple[float, list[str]]:
    """
    Check whether observations arrive at roughly the expected frequency.
    """
    dates = pd.to_datetime(data["date"]).sort_values()

    if len(dates) < 2:
        return 0.0, ["insufficient_history"]

    expected_days = {
        "daily": 1,
        "weekly": 7,
        "monthly": 31,
        "quarterly": 92,
        "annual": 366,
    }

    expected = expected_days[config.frequency]

    recent_dates = dates.tail(
        min(
            len(dates),
            config.historical_lookback or len(dates),
        )
    )

    gaps = recent_dates.diff().dt.days.dropna()

    # Allow normal calendar variation and publication structure.
    excessive_gaps = gaps > expected * 1.75
    gap_ratio = excessive_gaps.mean()

    if gap_ratio == 0:
        return 1.0, []

    score = max(0.0, 1.0 - gap_ratio * 4.0)

    flags = ["missing_observations"]

    return float(score), flags


def calculate_history_score(
    data: pd.DataFrame,
    config: IndicatorConfig,
) -> tuple[float, list[str]]:
    """
    Score the amount of usable historical data.

    Minimum history earns a usable but incomplete score.
    Full lookback coverage earns the maximum history score.
    """
    observations = len(data)

    if observations < config.minimum_history:
        return 0.0, ["insufficient_history"]

    target_history = (
        config.historical_lookback
        if config.historical_lookback is not None
        else config.minimum_history * 2
    )

    coverage = min(observations / target_history, 1.0)

    # Reaching minimum history should not immediately imply high confidence.
    score = 0.50 + (coverage * 0.50)

    flags: list[str] = []

    if coverage < 1.0:
        flags.append("limited_history")

    return float(score), flags


def calculate_stability_score(
    data: pd.DataFrame,
    config: IndicatorConfig,
) -> tuple[float, list[str]]:
    """
    Penalize unusually volatile recent observations.

    Normal volatility earns a good score, but not perfect confidence.
    """
    comparison_data = data

    if config.historical_lookback is not None:
        comparison_data = data.tail(config.historical_lookback)

    historical_std = comparison_data["value"].std()

    recent_window = max(config.state_window * 2, 6)
    recent_std = comparison_data["value"].tail(recent_window).std()

    if pd.isna(historical_std) or historical_std == 0:
        return 0.75, ["uncertain_stability"]

    volatility_ratio = recent_std / historical_std

    if volatility_ratio <= 1.0:
        return 0.90, []

    if volatility_ratio <= 1.5:
        score = 0.90 - ((volatility_ratio - 1.0) * 0.60)
        return float(score), ["elevated_recent_volatility"]

    if volatility_ratio >= 2.5:
        return 0.20, ["high_recent_volatility"]

    score = 0.60 - ((volatility_ratio - 1.5) * 0.40)

    return float(max(score, 0.20)), ["high_recent_volatility"]


def calculate_confidence(
    data: pd.DataFrame,
    config: IndicatorConfig,
) -> tuple[float, tuple[str, ...], dict[str, float]]:
    """
    Calculate signal-quality confidence from 0 to 0.90.

    Confidence reflects data reliability, not forecasting certainty.
    """
    history_score, history_flags = calculate_history_score(data, config)

    freshness_score, freshness_flags = calculate_freshness_score(
        data["date"].iloc[-1],
        config,
    )

    continuity_score, continuity_flags = calculate_continuity_score(
        data,
        config,
    )

    stability_score, stability_flags = calculate_stability_score(
        data,
        config,
    )

    raw_confidence = (
        history_score * 0.25
        + freshness_score * 0.35
        + continuity_score * 0.20
        + stability_score * 0.20
    )

    confidence = min(raw_confidence, 0.90)

    flags = tuple(
        dict.fromkeys(
            history_flags
            + freshness_flags
            + continuity_flags
            + stability_flags
        )
    )

    components = {
        "history_score": history_score,
        "freshness_score": freshness_score,
        "continuity_score": continuity_score,
        "stability_score": stability_score,
        "raw_confidence": raw_confidence,
    }

    return float(confidence), flags, components   
    
def classify_confidence(score: float) -> str:
    """Convert an internal confidence score into a readable label."""
    if score >= 0.85:
        return "Very High"

    if score >= 0.70:
        return "High"

    if score >= 0.55:
        return "Moderate"

    if score >= 0.35:
        return "Low"

    return "Very Low"

def run_indicator(
    data: pd.DataFrame,
    config: IndicatorConfig,
):
    """
    Run the complete Version 1 indicator pipeline.

    Returns a structured IndicatorResult containing the latest reading,
    current state, trend, historical context, confidence, and diagnostics.
    """
    from macro_engine.models.indicator import IndicatorResult

    cleaned = prepare_indicator_data(data, config)

    state_value = calculate_state_value(cleaned, config)
    historical_percentile = calculate_historical_percentile(cleaned, config)
    state_score = calculate_state_score(historical_percentile, config)
    state_label = classify_state(state_score)

    trend_value = calculate_trend_value(cleaned, config)
    trend_percentile = calculate_trend_percentile(cleaned, config)
    trend_score = calculate_trend_score(trend_percentile, config)
    trend_label = classify_trend(trend_score)

    latest_row = cleaned.iloc[-1]

    confidence, flags, confidence_components = calculate_confidence(
        cleaned,
        config,
    )
    
    confidence_label = classify_confidence(confidence)

    return IndicatorResult(
        indicator_id=config.indicator_id,
        name=config.name,
        economy=config.economy,
        pillar=config.pillar,
        bucket=config.bucket,
        latest_date=latest_row["date"].date(),
        latest_value=float(latest_row["value"]),
        state_value=state_value,
        state_score=state_score,
        state_label=state_label,
        trend_value=trend_value,
        trend_score=trend_score,
        trend_label=trend_label,
        historical_percentile=historical_percentile,
        confidence_score=confidence,
        confidence_label=confidence_label,
        observations_used=len(cleaned),
        flags=tuple(flags),
        diagnostics={
            "trend_percentile": trend_percentile,
            "state_window": config.state_window,
            "trend_window": config.trend_window,
            "historical_lookback": config.historical_lookback,
            **confidence_components,
        },
    )