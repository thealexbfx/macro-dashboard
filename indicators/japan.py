import streamlit as st
from data.japan import (
    get_estat_series,
    get_japan_unemployment_rate_data,
    get_japan_retail_sales_mom_data as load_japan_retail_sales_mom_data,
    get_japan_industrial_production_mom_data as load_japan_industrial_production_mom_data,
)
from data.japan import get_japan_gdp_qoq_data as load_japan_gdp_qoq_data
from data.boj import get_japan_policy_rate_proxy_data
from data.japan import get_japan_wage_growth_data as load_japan_wage_growth_data
from data.japan import get_japan_tankan_large_manufacturers_data as load_japan_tankan_large_manufacturers_data

from data.japan import get_japan_housing_starts_yoy_data as load_japan_housing_starts_yoy_data

from data.japan import get_japan_trade_balance_data as load_japan_trade_balance_data

from data.japan import get_japan_economy_watchers_survey_data as load_japan_economy_watchers_survey_data

from data.japan import get_boj_balance_sheet_data as load_boj_balance_sheet_data

from data.japan import get_japan_m3_yoy_data as load_japan_m3_yoy_data

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_m3_yoy_data():
    return load_japan_m3_yoy_data()

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_boj_balance_sheet_data():
    return load_boj_balance_sheet_data()
    
@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_boj_balance_sheet_yoy_data():
    df = load_boj_balance_sheet_data().copy()

    if df.empty:
        return df

    df = (
        df[["date", "value"]]
        .dropna()
        .sort_values("date")
        .reset_index(drop=True)
    )

    df["value"] = df["value"].pct_change(12) * 100

    return (
        df[["date", "value"]]
        .dropna()
        .reset_index(drop=True)
    )

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_economy_watchers_survey_data():
    return load_japan_economy_watchers_survey_data()

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_trade_balance_data():
    return load_japan_trade_balance_data()

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_housing_starts_yoy_data():
    return load_japan_housing_starts_yoy_data()

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_tankan_large_manufacturers_data():
    return load_japan_tankan_large_manufacturers_data()

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_wage_growth_data():
    return load_japan_wage_growth_data()

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_gdp_qoq_data():
    return load_japan_gdp_qoq_data()

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_cpi_yoy_data():
    return get_estat_series(
        stats_data_id="0003427113",
        cd_tab="3",
        cd_cat01="0001",
        cd_area="00000",
    )


@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_core_cpi_yoy_data():
    return get_estat_series(
        stats_data_id="0003427113",
        cd_tab="3",
        cd_cat01="0161",
        cd_area="00000",
    )
    
@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_tokyo_cpi_yoy_data():
    return get_estat_series(
        stats_data_id="0003427113",
        cd_tab="3",
        cd_cat01="0001",
        cd_area="00013",
    )
    
@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_tokyo_core_cpi_yoy_data():
    return get_estat_series(
        stats_data_id="0003427113",
        cd_tab="3",
        cd_cat01="0161",
        cd_area="00013",
    )

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_interest_rate_data():
    return get_japan_policy_rate_proxy_data()

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_retail_sales_mom_data():
    return load_japan_retail_sales_mom_data()

@st.cache_data(ttl=86400, show_spinner=False)
def get_japan_industrial_production_mom_data():
    return load_japan_industrial_production_mom_data()