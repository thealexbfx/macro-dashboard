import pandas as pd
import requests
import streamlit as st
from io import StringIO

from data.fred import get_usa_yield_data

@st.cache_data(ttl=86400, show_spinner=False)
def get_boe_yield_series(series_code):
    url = (
        "https://www.bankofengland.co.uk/boeapps/database/fromshowcolumns.asp"
        "?Travel=NIxAZxSUx"
        "&FromSeries=1"
        "&ToSeries=50"
        "&DAT=RNG"
        "&FD=1"
        "&FM=Jan"
        "&FY=1963"
        "&TD=31"
        "&TM=Dec"
        "&TY=2040"
        "&FNY=Y"
        "&CSVF=TT"
        "&html.x=66"
        "&html.y=26"
        f"&SeriesCodes={series_code}"
        "&UsingCodes=Y"
        "&Filter=N"
        f"&title={series_code}"
        "&VPD=Y"
    )

    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    tables = pd.read_html(StringIO(r.text))

    df_raw = tables[0]
    return clean_boe_yield_csv(df_raw)

def clean_boe_yield_csv(df):
    value_col = [col for col in df.columns if col != "Date"][0]

    df = df.rename(columns={
        "Date": "date",
        value_col: "value"
    })

    df["date"] = pd.to_datetime(df["date"], format="%d %b %y", errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df[["date", "value"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )
    
@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_yield_data(maturity):
    historical_url = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv"
    current_url = "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/jgbcme.csv"

    historical = pd.read_csv(historical_url, header=1)
    current = pd.read_csv(
        current_url,
        header=1,
        encoding="cp932"
    )

    df = pd.concat([historical, current], ignore_index=True)

    df = df[["Date", maturity]]
    df.columns = ["date", "value"]

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df[["date", "value"]]
        .dropna()
        .drop_duplicates(subset="date", keep="last")
        .sort_values("date")
        .reset_index(drop=True)
    )
    
@st.cache_data(ttl=86400, show_spinner=False)
def get_euro_yield_data(maturity):
    url = (
        "https://data-api.ecb.europa.eu/service/data/YC/"
        f"B.U2.EUR.4F.G_N_A.SV_C_YM.SR_{maturity}"
        "?format=csvdata"
    )

    df = pd.read_csv(url)

    df = df[["TIME_PERIOD", "OBS_VALUE"]]
    df.columns = ["date", "value"]

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df[["date", "value"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )
    
def get_euro_1yr_yield_data():
    return get_euro_yield_data("1Y")

def get_euro_2yr_yield_data():
    return get_euro_yield_data("2Y")

def get_euro_3yr_yield_data():
    return get_euro_yield_data("3Y")

def get_euro_5yr_yield_data():
    return get_euro_yield_data("5Y")

def get_euro_7yr_yield_data():
    return get_euro_yield_data("7Y")

def get_euro_10yr_yield_data():
    return get_euro_yield_data("10Y")

def get_euro_20yr_yield_data():
    return get_euro_yield_data("20Y")

def get_euro_30yr_yield_data():
    return get_euro_yield_data("30Y")
    
def get_japan_1yr_yield_data():
    return get_japan_yield_data("1Y")

def get_japan_2yr_yield_data():
    return get_japan_yield_data("2Y")

def get_japan_3yr_yield_data():
    return get_japan_yield_data("3Y")

def get_japan_5yr_yield_data():
    return get_japan_yield_data("5Y")

def get_japan_7yr_yield_data():
    return get_japan_yield_data("7Y")

def get_japan_10yr_yield_data():
    return get_japan_yield_data("10Y")

def get_japan_20yr_yield_data():
    return get_japan_yield_data("20Y")

def get_japan_30yr_yield_data():
    return get_japan_yield_data("30Y")

def get_japan_40yr_yield_data():
    return get_japan_yield_data("40Y")

def get_uk_5yr_yield_data():
    return get_boe_yield_series("IUDSNPY")

def get_uk_10yr_yield_data():
    return get_boe_yield_series("IUDMNPY")

def get_uk_20yr_yield_data():
    return get_boe_yield_series("IUDLNPY")

def get_usa_1mo_yield_data():
    return get_usa_yield_data("DGS1MO")

def get_usa_3mo_yield_data():
    return get_usa_yield_data("DGS3MO")

def get_usa_6mo_yield_data():
    return get_usa_yield_data("DGS6MO")

def get_usa_1yr_yield_data():
    return get_usa_yield_data("DGS1")

def get_usa_2yr_yield_data():
    return get_usa_yield_data("DGS2")

def get_usa_3yr_yield_data():
    return get_usa_yield_data("DGS3")

def get_usa_5yr_yield_data():
    return get_usa_yield_data("DGS5")

def get_usa_7yr_yield_data():
    return get_usa_yield_data("DGS7")

def get_usa_10yr_yield_data():
    return get_usa_yield_data("DGS10")

def get_usa_20yr_yield_data():
    return get_usa_yield_data("DGS20")

def get_usa_30yr_yield_data():
    return get_usa_yield_data("DGS30")