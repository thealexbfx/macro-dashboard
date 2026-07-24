from __future__ import annotations

import time

import pandas as pd
import requests
import streamlit as st

from config import FRED_API_KEY


FRED_URL = "https://api.stlouisfed.org/fred/series/observations"

RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}


@st.cache_data(ttl=1800, show_spinner=False)
def get_fred_series(
    series_id: str,
    max_attempts: int = 3,
    timeout_seconds: int = 20,
) -> pd.DataFrame:
    """
    Fetch a single FRED time series and return date/value columns.

    Temporary network failures and retryable HTTP responses are retried
    with a short exponential backoff. Invalid requests and permanent HTTP
    errors fail immediately.
    """
    if not series_id or not series_id.strip():
        raise ValueError("series_id must be a non-empty string")

    params = {
        "series_id": series_id.strip(),
        "api_key": FRED_API_KEY,
        "file_type": "json",
    }

    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                FRED_URL,
                params=params,
                timeout=timeout_seconds,
            )

            if response.status_code == 200:
                return _parse_fred_response(
                    series_id=series_id,
                    response=response,
                )

            if response.status_code not in RETRYABLE_STATUS_CODES:
                raise RuntimeError(
                    f"FRED request failed for {series_id}: "
                    f"{response.status_code} - {response.text[:300]}"
                )

            last_error = RuntimeError(
                f"FRED temporarily unavailable for {series_id}: "
                f"{response.status_code} - {response.text[:300]}"
            )

        except (
            requests.Timeout,
            requests.ConnectionError,
        ) as exc:
            last_error = exc

        if attempt < max_attempts:
            delay_seconds = 2 ** (attempt - 1)
            time.sleep(delay_seconds)

    raise RuntimeError(
        f"FRED request failed for {series_id} after "
        f"{max_attempts} attempts: {last_error}"
    ) from last_error


def _parse_fred_response(
    series_id: str,
    response: requests.Response,
) -> pd.DataFrame:
    """Validate and transform a successful FRED response."""
    try:
        data = response.json()
    except requests.JSONDecodeError as exc:
        raise RuntimeError(
            f"FRED returned invalid JSON for {series_id}"
        ) from exc

    if "observations" not in data:
        error_message = data.get(
            "error_message",
            "response missing observations",
        )

        raise RuntimeError(
            f"FRED response invalid for {series_id}: "
            f"{error_message}"
        )

    df = pd.DataFrame(data["observations"])

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    required_columns = {"date", "value"}
    missing_columns = required_columns.difference(df.columns)

    if missing_columns:
        raise RuntimeError(
            f"FRED response for {series_id} is missing columns: "
            f"{sorted(missing_columns)}"
        )

    df = df[["date", "value"]].copy()
    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce",
    )
    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    return (
        df.dropna(subset=["date", "value"])
        .sort_values("date")
        .reset_index(drop=True)
    )


@st.cache_data(ttl=1800, show_spinner=False)
def get_usa_yield_data(series_id: str) -> pd.DataFrame:
    """Alias for FRED Treasury yield series."""
    return get_fred_series(series_id)