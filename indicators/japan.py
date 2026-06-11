import streamlit as st
from data.japan import get_estat_series, get_japan_unemployment_rate_data
from data.japan import get_japan_gdp_qoq_data as load_japan_gdp_qoq_data
from data.boj import get_japan_policy_rate_proxy_data

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
def get_japan_interest_rate_data():
    return get_japan_policy_rate_proxy_data()


