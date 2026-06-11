import streamlit as st
from data.ons import get_ons_timeseries

from data.boe import get_uk_bank_rate_data


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