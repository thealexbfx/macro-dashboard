from data.eurostat import get_eurostat_series
from data.ecb import (
    get_ecb_main_refinancing_rate_data,
    get_ecb_negotiated_wages_data,
    get_ecb_labor_productivity_data,
    get_ecb_balance_sheet_data,
    get_ecb_house_price_index_data,
    get_ecb_trade_balance_data,
)
import streamlit as st



EURO_AREA_GEO = "EA21"

def get_euro_interest_rate_data():
    return get_ecb_main_refinancing_rate_data()


def get_euro_unemployment_rate_data():
    return get_eurostat_series(
        "une_rt_m",
        {
            "geo": EURO_AREA_GEO,
            "sex": "T",
            "age": "TOTAL",
            "s_adj": "SA",
            "unit": "PC_ACT",
            "freq": "M",
        }
    )


def get_euro_gdp_qoq_data():
    return get_eurostat_series(
        "namq_10_gdp",
        {
            "geo": EURO_AREA_GEO,
            "na_item": "B1GQ",
            "s_adj": "SCA",
            "unit": "CLV_PCH_PRE",
            "freq": "Q",
        }
    )


def get_euro_gdp_yoy_data():
    return get_eurostat_series(
        "namq_10_gdp",
        {
            "geo": EURO_AREA_GEO,
            "na_item": "B1GQ",
            "s_adj": "SCA",
            "unit": "CLV_PCH_SM",
            "freq": "Q",
        }
    )


def get_euro_hicp_yoy_data():
    df = get_eurostat_series(
        "prc_hicp_minr",
        {
            "geo": "EA20",
            "unit": "I15",
            "freq": "M",
        }
    )

    df = df.copy()
    df["value"] = df["value"].pct_change(periods=12) * 100
    df = df.dropna(subset=["value"]).reset_index(drop=True)

    return df

def get_euro_core_hicp_yoy_data():
    df = get_eurostat_series(
        "prc_hicp_minr",
        {
            "geo": "EA20",
            "coicop18": "TOT_X_NRG_FOOD",
            "unit": "I15",
            "freq": "M",
        }
    )

    df = df.copy()
    df["value"] = df["value"].pct_change(periods=12) * 100
    df = df.dropna(subset=["value"]).reset_index(drop=True)

    return df


def get_euro_industrial_production_mom_data():
    return get_eurostat_series(
        "sts_inpr_m",
        {
            "geo": "EA20",
            "indic_bt": "PRD",
            "nace_r2": "B-D",
            "s_adj": "SCA",
            "unit": "PCH_PRE",
            "freq": "M",
        }
    )


def get_euro_retail_sales_mom_data():
    return get_eurostat_series(
        "sts_trtu_m",
        {
            "geo": EURO_AREA_GEO,
            "indic_bt": "VOL_SLS",
            "nace_r2": "G47",
            "s_adj": "SCA",
            "unit": "PCH_PRE",
            "freq": "M",
        }
    )

def get_euro_trade_balance_data():
    return get_eurostat_series(
        "tet00066",
        {
            "freq": "A",
            "indic_et": "MIO_BAL_VAL",
            "sitc06": "TOTAL",
            "geo": "EA21",
            "partner": "EXT_EA21",
        }
    )
    
# Eurostat's detailed EA20 Business and Consumer Survey dataset
# provides the historical series through December 2025.
#
# The simplified EA21 series provides the latest observations.
# The overlapping values differ by only 0.1-0.3 index points, so
# EA20 history is retained through Dec 2025 and EA21 is appended
# from Jan 2026 onward.    
    
import pandas as pd
import requests

def get_euro_economic_sentiment_data():
    historical = get_eurostat_series(
        "ei_bssi_m_r2",
        {
            "geo": "EA20",
            "indic": "BS-ESI-I",
            "s_adj": "SA",
            "freq": "M",
            "lastTimePeriod": "240",
        },
    )

    current = get_eurostat_series(
        "teibs010",
        {
            "geo": "EA21",
            "indic": "BS-ESI-I",
            "s_adj": "SA",
            "freq": "M",
            "lastTimePeriod": "24",
        },
    )

    historical = historical[
        historical["date"] < pd.Timestamp("2026-01-01")
    ]

    current = current[
        current["date"] >= pd.Timestamp("2026-01-01")
    ]

    df = pd.concat(
        [historical, current],
        ignore_index=True,
    )

    return (
        df.dropna(subset=["date", "value"])
        .drop_duplicates(subset=["date"], keep="last")
        .sort_values("date")
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    df = get_euro_economic_sentiment_data()
    print(df.tail(20))
    print(df["date"].max())

  
def get_euro_services_hicp_yoy_data():
    df = get_eurostat_series(
        "prc_hicp_minr",
        {
            "geo": "EA20",
            "coicop18": "SERV",
            "unit": "I15",
            "freq": "M",
        }
    )

    df = df.copy()
    df["value"] = df["value"].pct_change(12) * 100

    return df.dropna(subset=["value"]).reset_index(drop=True)
    

def get_euro_negotiated_wages_yoy_data():
    return get_ecb_negotiated_wages_data()
    
def get_euro_labor_productivity_yoy_data():
    return get_ecb_labor_productivity_data()
    
def get_euro_ecb_balance_sheet_data():
    return get_ecb_balance_sheet_data()
    
def get_euro_house_price_index_yoy_data():
    return get_ecb_house_price_index_data()
    
def get_euro_trade_balance_data():
    return get_ecb_trade_balance_data()