import datetime as dt
import pandas as pd
import requests
import streamlit as st
from config import BLS_API_KEY


@st.cache_data(ttl=604800)
def get_bls_series(series_id: str, start_year: int = 2000):
    """Fetch a BLS time series in chunks and return date/value columns."""
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    current_year = dt.date.today().year

    all_rows = []

    chunk_size = 20 if BLS_API_KEY else 10

    for chunk_start in range(start_year, current_year + 1, chunk_size):
        chunk_end = min(chunk_start + chunk_size - 1, current_year)

        payload = {
            "seriesid": [series_id],
            "startyear": str(chunk_start),
            "endyear": str(chunk_end),
        }

        if BLS_API_KEY:
            payload["registrationkey"] = BLS_API_KEY

        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()

        if data.get("status") != "REQUEST_SUCCEEDED":
            message = data.get("message", ["Unknown BLS error"])
            raise RuntimeError(f"BLS request failed for {series_id}: {message}")

        series_list = data.get("Results", {}).get("series", [])

        if not series_list:
            return pd.DataFrame(columns=["date", "value"])

        series = series_list[0].get("data", [])

        for item in series:
            period = item["period"]

            if period == "M13":
                continue

            value_str = item.get("value")

            if value_str in ["-", "", None]:
                continue

            try:
                value = float(value_str)
            except ValueError:
                continue

            year = int(item["year"])

            if period.startswith("M"):
                month = int(period.replace("M", ""))
                date = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

            elif period.startswith("Q"):
                quarter = int(period.replace("Q", ""))
                month = {1: 3, 2: 6, 3: 9, 4: 12}.get(quarter)

                if month is None:
                    continue

                date = pd.Timestamp(year=year, month=month, day=1) + pd.offsets.MonthEnd(0)

            else:
                continue

            all_rows.append({
                "date": date,
                "value": value
            })

    df = pd.DataFrame(all_rows)

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    df = df.drop_duplicates(subset=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    return df