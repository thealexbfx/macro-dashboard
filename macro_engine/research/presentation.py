"""Deterministic descriptive labels; thresholds do not test significance."""

import math
import pandas as pd


def correlation_label(value):
    if value is None or not math.isfinite(value):
        return "Unavailable"
    strength = abs(value)
    label = (
        "Very weak"
        if strength < 0.1
        else "Weak"
        if strength < 0.3
        else "Moderate"
        if strength < 0.5
        else "Strong"
        if strength < 0.7
        else "Very strong"
    )
    return (
        "Zero" if value == 0 else f"{label} {'positive' if value > 0 else 'negative'}"
    )


def stability_rows(stability):
    return [
        {
            "Period": key.replace("_", " ").title(),
            "Observations": item["observations"],
            "Correlation": item["correlation"],
            "Interpretation": correlation_label(item["correlation"]),
            "Start": item.get("start"),
            "End": item.get("end"),
        }
        for key, item in stability.items()
    ]


def evidence_summary(stability, lead_lag):
    full = stability["full_sample"]
    r = full["correlation"]
    if r is None:
        return "Insufficient paired variation or observations to describe the full-sample correlation."
    text = f"The full-sample correlation is {correlation_label(r).lower()} (r={r:.3f}, n={full['observations']})."
    a, b = (stability[key]["correlation"] for key in ("first_half", "second_half"))
    if a is not None and b is not None:
        text += f" First-half r={a:.3f}; second-half r={b:.3f}. These differences are descriptive, not a test of structural change."
    zero = next((x["correlation"] for x in lead_lag if x["lag"] == 0), None)
    nonzero = [
        abs(x["correlation"])
        for x in lead_lag
        if x["lag"] != 0 and x["correlation"] is not None
    ]
    if zero is not None and nonzero and abs(zero) >= max(nonzero):
        text += " The contemporaneous relationship is at least as strong as every scanned nonzero lag."
    text += " Lag scanning does not establish predictive ability or causation."
    return text


def rolling_diagnostics(frame, rolling, window):
    """Attribute missing results without filling values or bridging gaps."""
    paired = frame.notna().all(axis=1)
    counts = paired.astype(int).rolling(window, min_periods=1).sum()
    warmup = [i < window - 1 for i in range(len(frame))]
    incomplete = (
        (~rolling.notna()) & (~pd.Series(warmup, index=frame.index)) & (counts < window)
    )
    constant = (
        rolling.isna() & (~pd.Series(warmup, index=frame.index)) & (counts == window)
    )
    valid = rolling.dropna()
    return {
        "window": window,
        "comparison_periods": len(frame),
        "warmup_periods": min(window - 1, len(frame)),
        "incomplete_windows": int(incomplete.sum()),
        "undefined_complete_windows": int(constant.sum()),
        "valid_windows": len(valid),
        "latest_valid_date": str(valid.index[-1].date()) if len(valid) else None,
        "latest_valid_correlation": float(valid.iloc[-1]) if len(valid) else None,
        "latest_period_available": bool(len(rolling) and rolling.notna().iloc[-1]),
    }
