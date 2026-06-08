import pandas as pd
import requests
import streamlit as st
from config import ESTAT_API_KEY


ESTAT_BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json"


def parse_estat_month_code(time_code: str):
    code = str(time_code)

    if len(code) < 8:
        return pd.NaT

    year = int(code[:4])
    month = int(code[-2:])

    if month < 1 or month > 12:
        return pd.NaT

    return pd.Timestamp(year=year, month=month, day=1)


@st.cache_data(ttl=86400)
def get_estat_series(
    stats_data_id: str,
    cd_tab: str | None = None,
    cd_cat01: str | None = None,
    cd_cat02: str | None = None,
    cd_cat03: str | None = None,
    cd_area: str | None = None,
    limit: int = 100000,
):
    params = {
        "appId": ESTAT_API_KEY,
        "statsDataId": stats_data_id,
        "limit": limit,
    }

    if cd_tab is not None:
        params["cdTab"] = cd_tab

    if cd_cat01 is not None:
        params["cdCat01"] = cd_cat01

    if cd_cat02 is not None:
        params["cdCat02"] = cd_cat02

    if cd_cat03 is not None:
        params["cdCat03"] = cd_cat03

    if cd_area is not None:
        params["cdArea"] = cd_area

    r = requests.get(
        f"{ESTAT_BASE_URL}/getStatsData",
        params=params,
        timeout=30
    )

    r.raise_for_status()
    data = r.json()

    values = (
        data.get("GET_STATS_DATA", {})
        .get("STATISTICAL_DATA", {})
        .get("DATA_INF", {})
        .get("VALUE", [])
    )

    if isinstance(values, dict):
        values = [values]

    rows = []

    for item in values:
        rows.append({
            "date": parse_estat_month_code(item.get("@time")),
            "value": item.get("$"),
        })

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df[["date", "value"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )

from io import BytesIO


@st.cache_data(ttl=86400)
def get_japan_unemployment_sa_excel():
    url = "https://www.e-stat.go.jp/en/stat-search/file-download?statInfId=000031831365&fileKind=0"

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    df = pd.read_excel(
        BytesIO(r.content),
        sheet_name="季節調整値",
        header=None
    )

    return df


def parse_japan_lfs_year(value, current_year=None):
    """
    The Excel file shows the year only in January rows.
    Sometimes it appears as 2026, sometimes as Japanese era text.
    """
    if pd.isna(value):
        return current_year

    text = str(value).strip()

    if text.isdigit():
        return int(text)

    if "令和" in text:
        # Example: 令和 8年 = 2018 + 8 = 2026
        import re
        m = re.search(r"令和\s*(\d+)", text)
        if m:
            return 2018 + int(m.group(1))

    return current_year


@st.cache_data(ttl=86400)
def get_japan_unemployment_rate_data():
    df = get_japan_unemployment_sa_excel()

    rows = []
    current_year = None

    month_map = {
        "1月": 1, "2月": 2, "3月": 3, "4月": 4,
        "5月": 5, "6月": 6, "7月": 7, "8月": 8,
        "9月": 9, "10月": 10, "11月": 11, "12月": 12,
    }

    for _, row in df.iterrows():
        current_year = parse_japan_lfs_year(row[0], current_year)

        month_text = str(row[1]).strip()
        month = month_map.get(month_text)

        value = pd.to_numeric(row[4], errors="coerce")

        if current_year and month and pd.notna(value):
            rows.append({
                "date": pd.Timestamp(year=current_year, month=month, day=1),
                "value": value
            })

    out = pd.DataFrame(rows)

    if out.empty:
        return pd.DataFrame(columns=["date", "value"])

    return (
        out[["date", "value"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )

@st.cache_data(ttl=86400)
def get_japan_gdp_qoq_data():
    url = "https://www.e-stat.go.jp/en/stat-search/file-download?statInfId=000040457275&fileKind=1"

    r = requests.get(url, timeout=30)
    r.raise_for_status()

    raw = pd.read_csv(BytesIO(r.content), encoding="cp932")

    rows = []
    current_year = None

    quarter_month_map = {
        "1- 3.": 3,
        "4- 6.": 6,
        "7- 9.": 9,
        "10-12.": 12,
    }

    for _, row in raw.iloc[6:].iterrows():
        period = str(row.iloc[0]).strip()
        value = pd.to_numeric(row.iloc[1], errors="coerce")

        if "/" in period:
            year_part, quarter_part = period.split("/")
            current_year = int(year_part.strip())
            quarter_text = quarter_part.strip()
        else:
            quarter_text = period.strip()

        month = quarter_month_map.get(quarter_text)

        if current_year and month and pd.notna(value):
            rows.append({
                "date": pd.Timestamp(year=current_year, month=month, day=1) + pd.offsets.MonthEnd(0),
                "value": value
            })

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    return df[["date", "value"]].dropna().sort_values("date").reset_index(drop=True)