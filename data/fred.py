import pandas as pd
import requests
import streamlit as st
from config import FRED_API_KEY


@st.cache_data(ttl=86400, show_spinner=False)
def get_fred_series(series_id: str):
    """Fetch a single time series from FRED and return date/value columns."""
    url = "https://api.stlouisfed.org/fred/series/observations"

    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
    }

    r = requests.get(url, params=params, timeout=20)

    if r.status_code != 200:
        raise RuntimeError(
            f"FRED request failed for {series_id}: "
            f"{r.status_code} - {r.text[:300]}"
        )

    data = r.json()

    if "observations" not in data:
        raise RuntimeError(f"FRED response missing observations for {series_id}")

    df = pd.DataFrame(data["observations"])

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    df = df[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().sort_values("date").reset_index(drop=True)

    return df


@st.cache_data(ttl=86400, show_spinner=False)
def get_usa_yield_data(series_id: str):
    """Alias for FRED Treasury yield series."""
    return get_fred_series(series_id)