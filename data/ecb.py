import pandas as pd
import streamlit as st


@st.cache_data(ttl=60)
def get_ecb_main_refinancing_rate_data():
    """
    ECB Main Refinancing Rate
    Official ECB Data Portal
    """

    url = (
        "https://data-api.ecb.europa.eu/service/data/"
        "FM/B.U2.EUR.4F.KR.MRR_FR.LEV?format=csvdata"
    )

    df = pd.read_csv(url)

    df = df[["TIME_PERIOD", "OBS_VALUE"]].copy()

    df = df.rename(
        columns={
            "TIME_PERIOD": "date",
            "OBS_VALUE": "value"
        }
    )

    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna()
    df = df.sort_values("date").reset_index(drop=True)

    return df