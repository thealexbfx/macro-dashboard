import pandas as pd
import requests
import streamlit as st
from config import ESTAT_API_KEY
from io import BytesIO



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


@st.cache_data(ttl=1800, show_spinner=False)
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


@st.cache_data(ttl=1800, show_spinner=False)
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


@st.cache_data(ttl=1800, show_spinner=False)
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

@st.cache_data(ttl=1800, show_spinner=False)
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
    
    
@st.cache_data(ttl=1800, show_spinner=False)
def get_japan_retail_sales_mom_data():
    url = "https://www.e-stat.go.jp/stat-search/file-download?statInfId=000031387999&fileKind=0"

    r = requests.get(url, timeout=(10, 120))
    r.raise_for_status()

    excel = pd.ExcelFile(BytesIO(r.content))

    sheet_name = next(
        s for s in excel.sheet_names
        if ("季調済" in s or "Seasonally" in s)
        and ("月次" in s or "Monthly" in s)
        and ("四半期" not in s and "Quarterly" not in s)
    )

    raw = pd.read_excel(
        excel,
        sheet_name=sheet_name,
        header=None
    )

    rows = []

    for _, row in raw.iloc[8:].iterrows():
        date_code = str(row.iloc[0]).strip()
        value = pd.to_numeric(row.iloc[20], errors="coerce")

        if len(date_code) >= 8 and pd.notna(value):
            year = int(date_code[:4])
            month = int(date_code[6:8])

            rows.append({
                "date": pd.Timestamp(year=year, month=month, day=1),
                "retail_index": value
            })

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    df = df.dropna().sort_values("date").reset_index(drop=True)
    df["value"] = df["retail_index"].pct_change() * 100

    return df[["date", "value"]].dropna().reset_index(drop=True)
    
def parse_dashboard_month_code(time_code):
    code = str(time_code)

    year = int(code[:4])
    month = int(code[4:6])

    return pd.Timestamp(year=year, month=month, day=1)


@st.cache_data(ttl=1800, show_spinner=False)
def get_japan_industrial_production_mom_data():
    url = "https://dashboard.e-stat.go.jp/api/1.0/Json/getData"

    params = {
        "Lang": "EN",
        "IndicatorCode": "0502070301000090010",
        "RegionCode": "00000",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    data = r.json()

    items = (
        data.get("GET_STATS", {})
        .get("STATISTICAL_DATA", {})
        .get("DATA_INF", {})
        .get("DATA_OBJ", [])
    )

    rows = []

    for item in items:
        value = item.get("VALUE", {})

        if (
            value.get("@cycle") == "1"
            and value.get("@regionRank") == "2"
            and value.get("@isSeasonal") == "2"
        ):
            rows.append({
                "date": parse_dashboard_month_code(value.get("@time")),
                "industrial_production_index": pd.to_numeric(value.get("$"), errors="coerce"),
            })

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    df = df.dropna().sort_values("date").reset_index(drop=True)
    df["value"] = df["industrial_production_index"].pct_change() * 100

    return df[["date", "value"]].dropna().reset_index(drop=True)
    
@st.cache_data(ttl=1800, show_spinner=False)
def get_japan_wage_growth_data():
    url = "https://dashboard.e-stat.go.jp/api/1.0/Json/getData"

    params = {
        "Lang": "EN",
        "IndicatorCode": "0302030201010090010",
        "RegionCode": "00000",
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()

    data = r.json()

    items = (
        data.get("GET_STATS", {})
        .get("STATISTICAL_DATA", {})
        .get("DATA_INF", {})
        .get("DATA_OBJ", [])
    )

    rows = []

    for item in items:
        value = item.get("VALUE", {})

        if (
            value.get("@cycle") == "1"
            and value.get("@isSeasonal") == "1"
        ):
            rows.append({
                "date": parse_dashboard_month_code(value.get("@time")),
                "wage_index": pd.to_numeric(
                    value.get("$"),
                    errors="coerce"
                ),
            })

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    df = (
        df.dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )

    df["value"] = df["wage_index"].pct_change(12) * 100

    return (
        df[["date", "value"]]
        .dropna()
        .reset_index(drop=True)
    )
    
@st.cache_data(ttl=1800, show_spinner=False)
def get_japan_tankan_large_manufacturers_data():
    url = "https://www.stat-search.boj.or.jp/ssi/mtshtml/co_q_1_en.html"

    raw = pd.read_html(url)[0]

    df = pd.DataFrame({
        "date": pd.to_datetime(raw.iloc[7:, 0], format="%Y/%m", errors="coerce"),
        "value": pd.to_numeric(raw.iloc[7:, 1], errors="coerce")
    })

    return (
        df.dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )
    
@st.cache_data(ttl=1800, show_spinner=False)
def get_japan_housing_starts_yoy_data():
    url = "https://www.e-stat.go.jp/en/stat-search/file-download?statInfId=000040459322&fileKind=0"

    raw = pd.read_excel(
        url,
        sheet_name="juu-e_o",
        header=None
    )

    rows = []
    current_year = None

    for _, row in raw.iloc[42:].iterrows():

        period = str(row.iloc[0]).strip()

        if period == "nan":
            continue

        # Handle Japanese full-width period
        period = period.replace("．", ".")

        try:
            if "." in period:
                year_part, month_part = period.split(".")
                current_year = int(year_part)
                month = int(month_part)

            elif "," in period:
                year_part, month_part = period.split(",")
                current_year = int(year_part)
                month = int(month_part)

            else:
                if current_year is None:
                    continue

                month = int(float(period))

            value = pd.to_numeric(row.iloc[2], errors="coerce")

            if pd.notna(value):
                rows.append({
                    "date": pd.Timestamp(
                        year=current_year,
                        month=month,
                        day=1
                    ),
                    "value": value
                })

        except Exception:
            continue

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(columns=["date", "value"])

    return (
        df.dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )
    
@st.cache_data(ttl=1800, show_spinner=False)
def get_japan_trade_balance_data():
    url = "https://www.customs.go.jp/toukei/suii/html/data/d41ma.csv"

    raw = pd.read_csv(url, encoding="cp932")

    df = raw.iloc[3:].copy()

    df = df.rename(columns={
        df.columns[0]: "date",
        df.columns[1]: "exports",
        df.columns[2]: "imports",
    })

    df["date"] = pd.to_datetime(df["date"], format="%Y/%m", errors="coerce")
    df["exports"] = pd.to_numeric(df["exports"], errors="coerce")
    df["imports"] = pd.to_numeric(df["imports"], errors="coerce")

    df["value"] = (df["exports"] - df["imports"]) / 1_000_000

    df = df[df["value"] != 0]

    return (
        df[["date", "value"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )
    
@st.cache_data(ttl=1800, show_spinner=False)
def get_japan_economy_watchers_survey_data():
    url = "https://www5.cao.go.jp/keizai3/watcher-e/di.xls"

    raw = pd.read_excel(url, sheet_name="3. DI by sector(SA)", header=None)

    rows = []
    current_year = None

    month_map = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
        "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
        "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }

    for _, row in raw.iloc[7:300].iterrows():
        year_raw = row.iloc[0]
        month_raw = str(row.iloc[1]).strip()
        value = pd.to_numeric(row.iloc[2], errors="coerce")

        if pd.notna(year_raw):
            year_text = str(year_raw).strip()
            if year_text.isdigit():
                current_year = int(year_text)

        month_num = month_map.get(month_raw)

        if current_year and month_num and pd.notna(value):
            rows.append({
                "date": pd.Timestamp(year=current_year, month=month_num, day=1),
                "value": value
            })

    df = pd.DataFrame(rows)

    return df.dropna().sort_values("date").reset_index(drop=True)
    
@st.cache_data(ttl=1800, show_spinner=False)
def get_boj_balance_sheet_data():

    url = "https://www.stat-search.boj.or.jp/ssi/html/nme_R031.4119888.20260620143547.02.csv"

    raw = pd.read_csv(url)

    df = raw.iloc[1:].copy()

    df = df.rename(columns={
        df.columns[0]: "date",
        df.columns[1]: "value",
    })

    df["date"] = pd.to_datetime(df["date"], format="%Y/%m", errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return (
        df[["date", "value"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )