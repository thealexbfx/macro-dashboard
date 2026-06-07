import pandas as pd
import requests
import streamlit as st


ECB_BASE_URL = "https://data-api.ecb.europa.eu/service/data"


@st.cache_data(ttl=86400)
def get_ecb_series(flow_ref: str, key: str) -> pd.DataFrame:
    """
    Fetch ECB SDW data and return standardized dataframe:
    date, value
    """
    url = f"{ECB_BASE_URL}/{flow_ref}/{key}"

    params = {
        "format": "csvdata",
    }

    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(pd.io.common.StringIO(response.text))

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    date_col = "TIME_PERIOD"
    value_col = "OBS_VALUE"

    df = df.rename(columns={date_col: "date", value_col: "value"})
    df = df[["date", "value"]].copy()

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["date", "value"])
    df = df.sort_values("date").reset_index(drop=True)

    return df


def get_ecb_main_refinancing_rate_data() -> pd.DataFrame:
    """
    ECB Main Refinancing Operations fixed rate / tender rate.
    """
    return get_ecb_series(
        "FM",
        "B.U2.EUR.4F.KR.MRR_FR.LEV"
    )