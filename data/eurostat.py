import pandas as pd
import requests
import streamlit as st


EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"


@st.cache_data(ttl=1800, show_spinner=False)
def get_eurostat_raw(dataset: str, params: dict) -> dict:
    """
    Fetch raw Eurostat JSON data.
    """
    url = f"{EUROSTAT_BASE_URL}/{dataset}"

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    return response.json()


def parse_eurostat_date(label: str):
    label = str(label)

    if "Q" in label:
        year, quarter = label.split("-Q")
        quarter_month = {
            "1": "03",
            "2": "06",
            "3": "09",
            "4": "12",
        }.get(quarter, "12")

        return pd.to_datetime(f"{year}-{quarter_month}-01") + pd.offsets.MonthEnd(0)

    return pd.to_datetime(label, errors="coerce")


def eurostat_json_to_df(data: dict) -> pd.DataFrame:
    """
    Convert simple Eurostat JSON-stat response into standardized dataframe:
    date, value
    """
    time_categories = data["dimension"]["time"]["category"]["index"]
    values = data.get("value", {})

    rows = []

    for time_label, time_index in time_categories.items():
        value = values.get(str(time_index))

        if value is not None:
            rows.append({
                "date": parse_eurostat_date(time_label),
                "value": value
            })

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"])
    df = df.sort_values("date").reset_index(drop=True)

    return df


@st.cache_data(ttl=1800, show_spinner=False)
def get_eurostat_series(dataset: str, params: dict) -> pd.DataFrame:
    """
    Fetch Eurostat data and return standardized dataframe:
    date, value
    """
    data = get_eurostat_raw(dataset, params)
    return eurostat_json_to_df(data)
    
    