import pandas as pd
import requests
import streamlit as st
from io import StringIO


BOJ_IR01_CSV_URL = "https://www.stat-search.boj.or.jp/ssi/mtshtml/csv/ir01_d_1_en.csv"


@st.cache_data(ttl=86400)
def get_boj_ir01_data():
    """
    Official BOJ IR01 series:
    Basic Discount Rate and Basic Loan Rate.
    Series code: IR01'MADR1Z@D
    """

    r = requests.get(BOJ_IR01_CSV_URL, timeout=30)
    r.raise_for_status()

    text = r.text
    lines = text.splitlines()

    data_lines = []
    for line in lines:
        # Actual data rows look like: 1998/01/01,0.5
        if line[:4].isdigit() and "," in line:
            data_lines.append(line)

    df = pd.read_csv(
        StringIO("\n".join(data_lines)),
        names=["date", "ir01"]
    )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["ir01"] = pd.to_numeric(df["ir01"], errors="coerce")

    return (
        df.dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )


@st.cache_data(ttl=86400)
def get_japan_policy_rate_proxy_data():
    """
    BOJ policy-rate proxy derived from official BOJ IR01 series.

    IR01 is the Basic Discount Rate and Basic Loan Rate, not the exact
    FXStreet / Forex Factory policy-rate field.

    Mapping used:
    - 0.30 -> -0.10 during the negative-rate regime
    - otherwise: policy proxy = IR01 - 0.25

    This is designed to approximate the BOJ policy target rate:
    "uncollateralized overnight call rate around X percent."
    """

    df = get_boj_ir01_data().copy()

    def convert_ir01_to_policy_proxy(ir01):
        if pd.isna(ir01):
            return pd.NA

        ir01 = round(float(ir01), 2)

        if ir01 == 0.30:
            return -0.10

        return ir01 - 0.25

    df["value"] = df["ir01"].apply(convert_ir01_to_policy_proxy)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df[["date", "value"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )