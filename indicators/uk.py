import streamlit as st
import pandas as pd
from data.ons import get_ons_timeseries
from io import StringIO
import requests
from data.ons import parse_ons_date
from data.boe import get_uk_bank_rate_data
from data.fred import get_fred_series


@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_interest_rate_data():
    return get_uk_bank_rate_data()

@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_cpi_yoy_data():
    return get_ons_timeseries(
        "D7G7", "MM23",
        "economy/inflationandpriceindices"
    )


@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_core_cpi_yoy_data():
    return get_ons_timeseries(
        "L55O", "MM23",
        "economy/inflationandpriceindices"
    )


@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_unemployment_rate_data():
    return get_ons_timeseries(
        "MGSX", "LMS",
        "employmentandlabourmarket/peoplenotinwork/unemployment"
    )

@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_gdp_qoq_data():
    return get_ons_timeseries(
        "IHYQ", "PN2",
        "economy/grossdomesticproductgdp"
    )

@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_retail_sales_mom_data():

    df = get_ons_timeseries(
        "J5EK",
        "DRSI",
        "businessindustryandtrade/retailindustry"
    ).copy()

    df["value"] = df["value"].pct_change() * 100

    return df.dropna().reset_index(drop=True)

@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_average_weekly_earnings_yoy_data():
    return get_ons_timeseries(
        "KAC3", "LMS",
        "employmentandlabourmarket/peopleinwork/earningsandworkinghours"
    )

@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_industrial_production_mom_data():
    df = get_ons_timeseries(
        "K22A", "DIOP",
        "economy/economicoutputandproductivity/output"
    ).copy()

    df["value"] = df["value"].pct_change() * 100

    return df.dropna().reset_index(drop=True)

@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_trade_balance_data():
    return get_ons_timeseries(
        "IKBJ", "MRET",
        "economy/nationalaccounts/balanceofpayments"
    )


@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_house_prices_yoy_data():

    df = get_ons_timeseries(
        "L55K", "MM23",
        "economy/inflationandpriceindices"
    ).copy()

    df["value"] = df["value"].pct_change(12) * 100

    return df.dropna().reset_index(drop=True)


@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_vacancies_data():
    return get_ons_timeseries(
        "JP9Z", "LMS",
        "employmentandlabourmarket/peopleinwork/employmentandemployeetypes"
    )
    
def get_uk_consumer_confidence_data():
    return get_fred_series("CSCICP02GBM460S")
    
@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_services_cpi_yoy_data():
    return get_ons_timeseries(
        "D7NN", "MM23",
        "economy/inflationandpriceindices"
    )
    
@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_gdp_mom_data():
    df = get_ons_timeseries(
        "ECY2", "MGDP",
        "economy/grossdomesticproductgdp"
    ).copy()

    df["value"] = df["value"].pct_change() * 100

    return df.dropna().reset_index(drop=True)
    
@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_unit_labour_costs_yoy_data():

    url = (
        "https://www.ons.gov.uk/file?uri="
        "/employmentandlabourmarket/peopleinwork/labourproductivity/"
        "datasets/unitlabourcostandunitwagecosttimeseries/current/ucst.csv"
    )

    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()

    df_raw = pd.read_csv(StringIO(r.text), header=None)

    # Data begins at row 79
    df_raw = df_raw.iloc[78:].copy()

    df = pd.DataFrame({
        "date": df_raw.iloc[:, 0].apply(parse_ons_date),
        "value": pd.to_numeric(df_raw.iloc[:, 14], errors="coerce")  # Column O
    })

    df = (
        df.dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )

    # Calculate YoY change from quarterly index
    df["value"] = df["value"].pct_change(4) * 100

    return df.dropna().reset_index(drop=True)
    
@st.cache_data(ttl=86400, show_spinner=False)
def get_uk_boe_balance_sheet_data():

    series = [
        "RPWB55A", "RPWB56A", "RPWB59A", "RPWB67A",
        "RPWZ4TJ", "RPWZ4TK", "RPWZOQ4", "RPWZ4TL",
        "RPWZ4TM", "RPWZOI7", "RPWZ4TN"
    ]

    url = "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"

    params = {
        "csv.x": "yes",
        "Datefrom": "01/Jan/1963",
        "Dateto": "now",
        "SeriesCodes": ",".join(series),
        "UsingCodes": "Y",
        "CSVF": "TN",
        "VPD": "Y",
    }

    headers = {"User-Agent": "Mozilla/5.0"}

    r = requests.get(url, params=params, headers=headers, timeout=30)
    r.raise_for_status()

    df_raw = pd.read_csv(StringIO(r.text))

    df = pd.DataFrame({
        "date": pd.to_datetime(df_raw["DATE"], format="%d %b %Y", errors="coerce"),
        "value": pd.to_numeric(df_raw["RPWZ4TM"], errors="coerce")
    })

    return df.dropna().sort_values("date").reset_index(drop=True)