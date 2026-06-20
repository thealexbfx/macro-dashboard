import pandas as pd
import requests
import streamlit as st
from io import StringIO


def fix_boe_year(d):
    if pd.isna(d):
        return d

    today_year = pd.Timestamp.today().year

    if d.year > today_year + 1:
        return d - pd.DateOffset(years=100)

    return d


@st.cache_data(ttl=1800)
def get_uk_bank_rate_data():
    url = "https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp"

    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()

    tables = pd.read_html(StringIO(r.text))
    df = tables[0].copy()

    df.columns = df.columns.str.strip()

    date_col = df.columns[0]
    value_col = df.columns[1]

    df = df.rename(columns={date_col: "date", value_col: "value"})

    df["date"] = pd.to_datetime(
    df["date"].astype(str).str.strip(),
    format="%d %b %y",
    errors="coerce"
    )
    df["date"] = df["date"].apply(fix_boe_year)

    df["value"] = (
        df["value"]
        .astype(str)
        .str.replace("%", "", regex=False)
        .str.strip()
    )

    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return df[["date", "value"]].dropna().sort_values("date").reset_index(drop=True)
  
