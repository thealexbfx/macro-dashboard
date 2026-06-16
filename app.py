import streamlit as st
import pandas as pd
import plotly.express as px
import datetime as dt
import requests
import io
import numpy as np
import csv
from urllib.parse import urljoin
from io import BytesIO
from datetime import datetime
from dateutil.parser import parse
import gzip
import yfinance as yf
from dotenv import load_dotenv
import os
import plotly.graph_objects as go
import streamlit.components.v1 as components
import calendar
from openai import OpenAI
from app_pages.usa import render_usa_page
from app_pages.japan import render_japan_page
from app_pages.uk import render_uk_page
from app_pages.euro import render_euro_page

IS_PROD = os.getenv("APP_ENV", "dev") == "prod"
if IS_PROD:
    st.set_option("client.showErrorDetails", False)

def safe_render(render_func, section_name):
    try:
        render_func()
    except Exception as e:
        if IS_PROD:
            st.error(f"{section_name} is temporarily unavailable. Please try again later.")
        else:
            st.exception(e)

from components.charts import plot_chart, plot_scenario_chart

from app_pages.global_macro_view import render_global_macro_view

# Modular data loaders - Phase 2A
from data.fred import get_fred_series, get_usa_yield_data
from data.bls import get_bls_series
from data.bea import get_bea_nipa_series
from data.transforms import (
    calculate_yoy_from_index,
    calculate_mom_pct_change,
    calculate_diff,
)

from data.yahoo import get_fx_data_yahoo
from indicators.usa import (
    get_usa_interest_rate_data,
    get_usa_cpi_yoy_data,
    get_usa_core_cpi_yoy_data,
    get_usa_pce_yoy_data,
    get_usa_core_pce_yoy_data,
    get_usa_ppi_yoy_data,
    get_usa_core_ppi_yoy_data,
    get_usa_import_prices_yoy_data,
    get_usa_export_prices_yoy_data,
    get_usa_unemployment_rate_data,
    get_usa_labor_force_participation_data,
    get_usa_nfp_data,
    get_usa_average_hourly_earnings_yoy_data,
    get_usa_jolts_job_openings_data,
    get_usa_quits_rate_data,
    get_usa_eci_total_compensation_yoy_data,
    get_usa_eci_wages_salaries_yoy_data,
    get_usa_gdp_qoq_data,
    get_usa_personal_income_mom_data,
    get_usa_personal_consumption_mom_data,
    get_usa_saving_rate_data,
    get_usa_michigan_consumer_sentiment_data,
    get_usa_chicago_fed_nfci_data,
    get_usa_housing_starts_mom_data,
    get_usa_building_permits_mom_data,
    get_usa_new_home_sales_mom_data,
    get_usa_retail_sales_mom_data,
    get_usa_trade_balance_data,
    get_usa_industrial_production_mom_data,
    get_usa_capacity_utilization_data,
    get_usa_durable_goods_orders_mom_data,
    get_usa_labor_productivity_data,
    get_usa_unit_labor_costs_data,
    get_usa_real_hourly_compensation_data,
    get_usa_initial_jobless_claims_data,
  ##  get_usa_ism_manufacturing_pmi_data,
  ##  get_usa_ism_services_pmi_data,
    get_usa_fed_balance_sheet_data,
    get_usa_1mo_yield_data,
    get_usa_3mo_yield_data,
    get_usa_6mo_yield_data,
    get_usa_1yr_yield_data,
    get_usa_2yr_yield_data,
    get_usa_3yr_yield_data,
    get_usa_5yr_yield_data,
    get_usa_7yr_yield_data,
    get_usa_10yr_yield_data,
    get_usa_20yr_yield_data,
    get_usa_30yr_yield_data,
)

from indicators.euro import (
    get_euro_interest_rate_data,
    get_euro_unemployment_rate_data,
    get_euro_gdp_qoq_data,
    get_euro_gdp_yoy_data,
    get_euro_hicp_yoy_data,
    get_euro_core_hicp_yoy_data,
    get_euro_retail_sales_mom_data,
    get_euro_industrial_production_mom_data,
)

from indicators.uk import (
    get_uk_interest_rate_data,
    get_uk_cpi_yoy_data,
    get_uk_core_cpi_yoy_data,
    get_uk_gdp_qoq_data,
    get_uk_unemployment_rate_data,
    get_uk_retail_sales_mom_data,
    get_uk_average_weekly_earnings_yoy_data,
    get_uk_industrial_production_mom_data,
    get_uk_trade_balance_data,
    get_uk_house_prices_yoy_data,
    get_uk_vacancies_data,
)

from indicators.japan import (
    get_japan_interest_rate_data,
    get_japan_cpi_yoy_data,
    get_japan_core_cpi_yoy_data,
    get_japan_gdp_qoq_data,
    get_japan_unemployment_rate_data,
)

from app_pages.fx import render_fx_page

from app_pages.equities import render_equities_page

from app_pages.commodities import render_commodities_page

from app_pages.rates_bonds import render_rates_bonds_page

from app_pages.crypto import render_crypto_page

load_dotenv()  # loads .env file

FRED_API_KEY = os.getenv("FRED_API_KEY")
ESTAT_API_KEY = os.getenv("ESTAT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # fallback if not using Streamlit secrets
BLS_API_KEY = os.getenv("BLS_API_KEY")        # fallback if not using Streamlit secrets
BEA_API_KEY = os.getenv("BEA_API_KEY")

# ------------------------------
# Initialize OpenAI client
# ------------------------------
try:
    # Prefer Streamlit secrets if available
    OPENAI_API_KEY = st.secrets["openai"]["api_key"]
except Exception:
    # fallback to .env
    if not OPENAI_API_KEY:
        st.error("❌ OpenAI API key not found! Set it in .env or Streamlit secrets.")
        st.stop()
# ------------------------------
# Load BLS API key
# ------------------------------
try:
    BLS_API_KEY = st.secrets["openai"]["BLS_API_KEY"]
except Exception:
    # fallback to .env
    BLS_API_KEY = os.getenv("BLS_API_KEY")
    
try:
    BEA_API_KEY = st.secrets["openai"]["BEA_API_KEY"]
except Exception:
    BEA_API_KEY = os.getenv("BEA_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

def calculate_summary_stats(df_filtered):
    from scipy.stats import linregress

    n_obs = len(df_filtered)

    if n_obs == 0:
        raise ValueError("df_filtered is empty")

    values = df_filtered["value"]
    mean_val = values.mean()
    latest_val = values.iloc[-1]
    start_val = values.iloc[0]
    min_val = values.min()
    max_val = values.max()

    change_since_start = latest_val - start_val
    position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

    if n_obs > 1:
        slope, _, _, _, _ = linregress(range(n_obs), values)
    else:
        slope = 0

    if change_since_start > 0:
        trend = "🔺 Upward"
    elif change_since_start < 0:
        trend = "🔻 Downward"
    else:
        trend = "⏸ Flat"

    volatility = (values.std() / mean_val * 100) if mean_val != 0 else np.nan

    return {
        "n_obs": n_obs,
        "mean_val": mean_val,
        "latest_val": latest_val,
        "change_since_start": change_since_start,
        "position_pct": position_pct,
        "trend": trend,
        "volatility": volatility,
        "slope": slope,
    }

def render_summary_bar(stats):
    change_color = (
        "#06b606" if stats["change_since_start"] > 0
        else "#e63946" if stats["change_since_start"] < 0
        else "#333"
    )

    position_label = (
        "High" if stats["position_pct"] > 70
        else "Low" if stats["position_pct"] < 30
        else "Mid"
    )

    st.markdown(f"""
    <div style="
        background-color:#f9f9f9;
        border:1px solid #dcdcdc;
        border-radius:12px;
        padding:10px 18px;
        text-align:center;
        font-family:'Inter','Segoe UI','Arial',sans-serif;
        font-size:13px;
        color:#111;
        font-weight:500;
        margin-top:5px;
        margin-bottom:18px;
        display:flex;
        justify-content:center;
        flex-wrap:wrap;
        gap:18px;
        box-shadow:0 1px 3px rgba(0,0,0,0.04);
    ">
        <div>Data Points: <b>{stats["n_obs"]}</b></div>
        <div>Mean: <b>{stats["mean_val"]:.2f}</b></div>
        <div>Latest: <b>{stats["latest_val"]:.2f}</b></div>
        <div>Change: <b style='color:{change_color};'>{stats["change_since_start"]:+.2f}</b></div>
        <div>Trend: <b>{stats["trend"]}</b></div>
        <div>Position: <b>{stats["position_pct"]:.0f}% ({position_label})</b></div>
        <div>Volatility: <b>{stats["volatility"]:.1f}%</b></div>
    </div>
    """, unsafe_allow_html=True)

def render_commentary(commentary, indicator):
    st.markdown(
        f"""
        <div style="
            position: relative;
            top: -10px;
            margin-left: 30px;
            font-size:19px;
            font-family: 'Arial Bold';
            font-weight:normal;
            color:#333;
        ">
            {commentary.get(indicator, "")}
        </div>
        """,
        unsafe_allow_html=True
    )


# --------- Global Analysis Functions ---------
@st.cache_data(ttl=1800)
def analyze_usa():
    """Compute latest value, slope, and relative position for all USA indicators."""
    usa_tickers = {
        # Monetary Policy
        "Federal Funds Rate": get_usa_interest_rate_data,
        "Fed Balance Sheet": get_usa_fed_balance_sheet_data,

        # Inflation
        "CPI YoY": get_usa_cpi_yoy_data,
        "Core CPI YoY": get_usa_core_cpi_yoy_data,
        "PCE YoY": get_usa_pce_yoy_data,
        "Core PCE YoY": get_usa_core_pce_yoy_data,
        "PPI YoY": get_usa_ppi_yoy_data,
        "Core PPI YoY": get_usa_core_ppi_yoy_data,
        "Import Prices YoY": get_usa_import_prices_yoy_data,
        "Export Prices YoY": get_usa_export_prices_yoy_data,

        # Labor Market
        "Unemployment Rate": get_usa_unemployment_rate_data,
        "Labor Force Participation Rate": get_usa_labor_force_participation_data,
        "Non Farm Payrolls": get_usa_nfp_data,
        "Average Hourly Earnings YoY": get_usa_average_hourly_earnings_yoy_data,
        "ECI Total Compensation YoY": get_usa_eci_total_compensation_yoy_data,
        "ECI Wages & Salaries YoY": get_usa_eci_wages_salaries_yoy_data,
        "JOLTS Job Openings": get_usa_jolts_job_openings_data,
        "Quits Rate": get_usa_quits_rate_data,
        "Initial Jobless Claims": get_usa_initial_jobless_claims_data,

        # Growth / Consumer / Activity
        "GDP Growth Rate": get_usa_gdp_qoq_data,
        "Personal Income MoM": get_usa_personal_income_mom_data,
        "Personal Consumption MoM": get_usa_personal_consumption_mom_data,
        "Retail Sales MoM": get_usa_retail_sales_mom_data,
        "Industrial Production MoM": get_usa_industrial_production_mom_data,
        "Capacity Utilization": get_usa_capacity_utilization_data,
        "Durable Goods Orders MoM": get_usa_durable_goods_orders_mom_data,
        "Trade Balance": get_usa_trade_balance_data,
        "Saving Rate": get_usa_saving_rate_data,

        # Housing
        "Housing Starts MoM": get_usa_housing_starts_mom_data,
        "Building Permits MoM": get_usa_building_permits_mom_data,
        "New Home Sales MoM": get_usa_new_home_sales_mom_data,

        # Productivity & Costs
        "Labor Productivity": get_usa_labor_productivity_data,
        "Unit Labor Costs": get_usa_unit_labor_costs_data,
        "Real Hourly Compensation": get_usa_real_hourly_compensation_data,

        # Sentiment & Conditions
        "Michigan Consumer Sentiment": get_usa_michigan_consumer_sentiment_data,
        "Chicago Fed NFCI": get_usa_chicago_fed_nfci_data,
        
        # Surveys
   ##     "ISM Manufacturing PMI": get_usa_ism_manufacturing_pmi_data,
   ##     "ISM Services PMI": get_usa_ism_services_pmi_data,
    }

    results = {}
    for name, func in usa_tickers.items():
        try:
            df = func().dropna()
            if len(df) < 12:
                continue
            df_1y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=1))]
            latest = df_1y["value"].iloc[-1]
            start = df_1y["value"].iloc[0]

            if latest > start:
                trend = "up"
            elif latest < start:
                trend = "down"
            else:
                trend = "flat"

            results[name] = {"latest": latest, "trend": trend}

        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")
    return results

@st.cache_data(ttl=1800)
def analyze_japan():
    """Compute latest value, slope, and relative position for all japan indicators."""
    japan_tickers = {
        "Interest Rate": get_japan_interest_rate_data,
        "CPI YoY": get_japan_cpi_yoy_data,
        "GDP Growth Rate": get_japan_gdp_qoq_data,
        "Unemployment Rate": get_japan_unemployment_rate_data
    }

    results = {}
    for name, func in japan_tickers.items():
        try:
            df = func().dropna()
            if len(df) < 12:
                continue
            df_1y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=1))]
            latest = df_1y["value"].iloc[-1]
            start = df_1y["value"].iloc[0]

            if latest > start:
                trend = "up"
            elif latest < start:
                trend = "down"
            else:
                trend = "flat"

            results[name] = {"latest": latest, "trend": trend}

        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")
    return results

@st.cache_data(ttl=1800)
def analyze_uk():
    """Compute latest value and 1-year trend for key UK indicators."""

    uk_tickers = {
        # Monetary Policy
        "Bank Rate": get_uk_interest_rate_data,

        # Inflation
        "CPI YoY": get_uk_cpi_yoy_data,
        "Core CPI YoY": get_uk_core_cpi_yoy_data,
        "House Prices YoY": get_uk_house_prices_yoy_data,

        # Growth / Activity
        "GDP QoQ": get_uk_gdp_qoq_data,
        "Retail Sales MoM": get_uk_retail_sales_mom_data,
        "Industrial Production MoM": get_uk_industrial_production_mom_data,

        # Labor Market
        "Unemployment Rate": get_uk_unemployment_rate_data,
        "Average Weekly Earnings YoY": get_uk_average_weekly_earnings_yoy_data,
        "Vacancies": get_uk_vacancies_data,

        # External Sector
        "Trade Balance": get_uk_trade_balance_data,
    }

    results = {}

    for name, func in uk_tickers.items():
        try:
            df = func().dropna()

            if len(df) < 4:
                continue

            df_1y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=1))]

            if len(df_1y) < 2:
                continue

            latest = df_1y["value"].iloc[-1]
            start = df_1y["value"].iloc[0]

            if latest > start:
                trend = "up"
            elif latest < start:
                trend = "down"
            else:
                trend = "flat"

            results[name] = {
                "latest": latest,
                "trend": trend,
            }

        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")

    return results

@st.cache_data(ttl=1800)
def analyze_euro():
    """Compute latest value and trend for Euro Area indicators."""
    euro_tickers = {
        "Interest Rate": get_euro_interest_rate_data,
        "HICP YoY": get_euro_hicp_yoy_data,
        "Core HICP YoY": get_euro_core_hicp_yoy_data,
        "GDP QoQ": get_euro_gdp_qoq_data,
        "GDP YoY": get_euro_gdp_yoy_data,
        "Unemployment Rate": get_euro_unemployment_rate_data,
        "Retail Sales MoM": get_euro_retail_sales_mom_data,
    }

    results = {}
    for name, func in euro_tickers.items():
        try:
            df = func().dropna()
            if len(df) < 12:
                continue

            df_1y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=1))]
            latest = df_1y["value"].iloc[-1]
            start = df_1y["value"].iloc[0]

            if latest > start:
                trend = "up"
            elif latest < start:
                trend = "down"
            else:
                trend = "flat"

            results[name] = {"latest": latest, "trend": trend}

        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")

    return results

    results = {}
    for name, func in euro_tickers.items():
        try:
            df = func().dropna()
            if len(df) < 12:
                continue
            df_1y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=1))]
            latest = df_1y["value"].iloc[-1]
            start = df_1y["value"].iloc[0]

            if latest > start:
                trend = "up"
            elif latest < start:
                trend = "down"
            else:
                trend = "flat"

            results[name] = {"latest": latest, "trend": trend}

        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")
    return results
    
# -----------------------------
# Asset Class Analysis Functions
# -----------------------------

def analyze_asset_class(tickers_dict):
    """
    Generic function to analyze tickers/asset class.
    tickers_dict: { "Name": ("ticker", "Friendly Name") } or { "Name": "code" }
    Returns: { Name: {latest, trend, position} }
    """
    results = {}
    for name, code_or_ticker in tickers_dict.items():
        try:
            if isinstance(code_or_ticker, tuple):
                # For equities / stocks / commodities / FX: tuple(ticker, friendly_name)
                df = get_fx_data_yahoo(code_or_ticker[0], start_date=dt.date(1980,1,1), end_date=dt.date.today())
            else:
                # For other codes (bonds, etc.)
                df = load_indicator_data(code_or_ticker)

            df = df.dropna()
            if len(df) < 12:
                continue

            df_1y = df[df['date'] >= (df['date'].max() - pd.DateOffset(years=1))]
            latest = df_1y['value'].iloc[-1]
            start = df_1y['value'].iloc[0]

            trend = "up" if latest > start else "down" if latest < start else "flat"
            min_val, max_val = df_1y['value'].min(), df_1y['value'].max()
            position = (latest - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

            results[name] = {
                "latest": latest,
                "trend": trend,
                "position": position
            }
        except Exception as e:
            if IS_PROD:
                st.warning(f"{name} data is temporarily unavailable.")
            else:
                st.warning(f"⚠️ Could not process {name}: {e}")
    return results


# Equities
@st.cache_data(ttl=1800)
def analyze_equities():
    tickers = {
        "S&P 500": ("^GSPC", "S&P 500"),
        "NASDAQ": ("^IXIC", "NASDAQ"),
        "Dow Jones": ("^DJI", "Dow Jones"),
        "FTSE 100": ("^FTSE", "FTSE 100"),
        "Nikkei 225": ("^N225", "Nikkei 225"),
        "DAX": ("^GDAXI", "DAX"),
        "MSCI Emerging Markets ETF": ("EEM", "MSCI Emerging Markets ETF"),
        "VIX": ("^VIX", "VIX")
    }
    return analyze_asset_class(tickers)


# Stocks
@st.cache_data(ttl=1800)
def analyze_stocks():
    tickers = {
        "Apple": "st_aapl",
        "Amazon": "st_amzn",
        "Meta": "st_meta",
        "Google": "st_googl",
        "Nvidia": "st_nvda",
        "Microsoft": "st_msft",
        "Tesla": "st_tsla"
    }
    return analyze_asset_class(tickers)


# Commodities
@st.cache_data(ttl=1800)
def analyze_commodities():
    tickers = {
        "Gold": "cmd_gold",
        "Silver": "cmd_silver",
        "WTI Crude": "cmd_wti",
        "Brent Crude": "cmd_brent",
        "Natural Gas": "cmd_ng",
        "Wheat": "cmd_wheat",
        "Copper": "cmd_copper",
        "Corn": "cmd_corn",
        "Soy": "cmd_soy"
    }
    return analyze_asset_class(tickers)


# FX
@st.cache_data(ttl=1800)
def analyze_fx():
    tickers = {
        "EUR/USD": "eurusd",
        "GBP/USD": "gbpusd",
        "USD/JPY": "usdjpy",
        "DXY": "dxy"
    }
    return analyze_asset_class(tickers)


# Crypto
@st.cache_data(ttl=1800)
def analyze_crypto():
    tickers = {
        "Bitcoin": "crypto_btc",
        "Ethereum": "crypto_eth"
    }
    return analyze_asset_class(tickers)


# Bonds (special handling: US yields via Yahoo, others via text)
@st.cache_data(ttl=1800)
def analyze_bonds():
    tickers = {
        "US 2Y": "usa_2y",
        "US 10Y": "usa_10y",
        "UK 2Y": "uk_2y",
        "UK 10Y": "uk_10y",
        "Japan 2Y": "jp_2y",
        "Japan 10Y": "jp_10y",
        "Euro 2Y": "eu_2y",
        "Euro 10Y": "eu_10y"
    }
    return analyze_asset_class(tickers)


# -------- Asset Map (Global Reference) --------
asset_map = {
    "USA": ["usa_rate","usa_cpi","usa_core_cpi","usa_gdp","usa_unemp","usa_ahe","usa_core_pce","usa_core_ppi","usa_housing","usa_ism_manu","usa_ism_serv","usa_jolts","usa_michigan","usa_nfp","usa_pce","usa_ppi","usa_retail","usa_trade"],
    "Yields": ["usa_1m","usa_3m","usa_6m","usa_1y","usa_2y","usa_3y","usa_5y","usa_7y","usa_10y","usa_20y","usa_30y"],
    "UK": ["uk_rate","uk_cpi","uk_gdp","uk_unemp","uk_10y","uk_2y"],
    "Japan": ["jp_rate","jp_cpi","jp_gdp","jp_unemp","jp_10y","jp_2y"],
    "Euro Area": ["eu_rate","eu_cpi","eu_gdp","eu_unemp","eu_10y","eu_2y"],
    "FX": ["eurusd","gbpusd","usdjpy","dxy"],
    "Equities": ["eq_sp500","eq_nasdaq","eq_dow","eq_ftse","eq_nikkei","eq_dax","eq_msci_em","eq_vix"],
    "Stocks": ["st_aapl","st_amzn","st_meta","st_googl","st_nvda","st_msft","st_tsla"],
    "Commodities": ["cmd_gold","cmd_silver","cmd_wti","cmd_brent","cmd_ng","cmd_wheat","cmd_copper","cmd_corn","cmd_soy"],
    "Crypto": ["crypto_btc","crypto_eth"]
}

# --- Asset display names ---
display_names = {
    # USA Economic Indicators
    "usa_rate": "USA Federal Funds Rate",
    "usa_cpi": "USA CPI YoY",
    "usa_core_cpi": "USA Core CPI YoY",
    "usa_gdp": "USA GDP QoQ",
    "usa_unemp": "USA Unemployment Rate",
    "usa_ahe": "USA Average Hourly Earnings YoY",
    "usa_core_pce": "USA Core PCE YoY",
    "usa_core_ppi": "USA Core PPI YoY",
    "usa_housing": "USA Housing Starts MoM",
 #   "usa_ism_manu": "USA ISM Manufacturing PMI",
 #   "usa_ism_serv": "USA ISM Services PMI",
    "usa_jolts": "USA JOLTS Job Openings",
    "usa_michigan": "USA Michigan Consumer Sentiment",
    "usa_nfp": "USA Non-Farm Payrolls",
    "usa_pce": "USA PCE YoY",
    "usa_ppi": "USA PPI YoY",
    "usa_retail": "USA Retail Sales MoM",
    "usa_trade": "USA Trade Balance",

    # US Yields
    "usa_1m": "USA 1M Yield",
    "usa_3m": "USA 3M Yield",
    "usa_6m": "USA 6M Yield",
    "usa_1y": "USA 1Y Yield",
    "usa_2y": "USA 2Y Yield",
    "usa_3y": "USA 3Y Yield",
    "usa_5y": "USA 5Y Yield",
    "usa_7y": "USA 7Y Yield",
    "usa_10y": "USA 10Y Yield",
    "usa_20y": "USA 20Y Yield",
    "usa_30y": "USA 30Y Yield",

    # UK
    "uk_rate": "UK Interest Rate",
    "uk_cpi": "UK CPI YoY",
    "uk_gdp": "UK GDP QoQ",
    "uk_unemp": "UK Unemployment Rate",
    "uk_10y": "UK 10Y Yield",
    "uk_2y": "UK 2Y Yield",

    # Japan
    "jp_rate": "Japan Interest Rate",
    "jp_cpi": "Japan CPI YoY",
    "jp_gdp": "Japan GDP QoQ",
    "jp_unemp": "Japan Unemployment Rate",
    "jp_10y": "Japan 10Y Yield",
    "jp_2y": "Japan 2Y Yield",

    # Euro Area
    "eu_rate": "Euro Interest Rate",
    "eu_cpi": "Euro CPI YoY",
    "eu_gdp": "Euro GDP QoQ",
    "eu_unemp": "Euro Unemployment Rate",
    "eu_10y": "Euro 10Y Yield",
    "eu_2y": "Euro 2Y Yield",

    # FX
    "eurusd": "EUR/USD",
    "gbpusd": "GBP/USD",
    "usdjpy": "USD/JPY",
    "dxy": "US Dollar Index (DXY)",

    # Equities / Indices
    "eq_sp500": "S&P 500",
    "eq_nasdaq": "Nasdaq 100",
    "eq_dow": "Dow Jones Industrial",
    "eq_ftse": "FTSE 100",
    "eq_nikkei": "Nikkei 225",
    "eq_dax": "DAX",
    "eq_msci_em": "MSCI Emerging Markets",
    "eq_vix": "VIX",

    # Stocks
    "st_aapl": "Apple",
    "st_amzn": "Amazon",
    "st_meta": "Meta",
    "st_googl": "Google",
    "st_nvda": "Nvidia",
    "st_msft": "Microsoft",
    "st_tsla": "Tesla",

    # Commodities
    "cmd_gold": "Gold",
    "cmd_silver": "Silver",
    "cmd_wti": "WTI Crude",
    "cmd_brent": "Brent Crude",
    "cmd_ng": "Natural Gas",
    "cmd_wheat": "Wheat",
    "cmd_copper": "Copper",
    "cmd_corn": "Corn",
    "cmd_soy": "Soy",

    # Crypto
    "crypto_btc": "Bitcoin",
    "crypto_eth": "Ethereum",
    
}

dropdown_map = {v: k for k, v in display_names.items()}

def load_indicator_data(code):
    loader_map = {
        # USA
        "usa_rate": get_usa_interest_rate_data,
        "usa_cpi": get_usa_cpi_yoy_data,
        "usa_core_cpi": get_usa_core_cpi_yoy_data,
        "usa_gdp": get_usa_gdp_qoq_data,
        "usa_unemp": get_usa_unemployment_rate_data,
        "usa_ahe": get_usa_average_hourly_earnings_yoy_data,
        "usa_core_pce": get_usa_core_pce_yoy_data,
        "usa_core_ppi": get_usa_core_ppi_yoy_data,
        "usa_housing": get_usa_housing_starts_mom_data,
   #     "usa_ism_manu": get_usa_ism_manufacturing_pmi_data,
   #     "usa_ism_serv": get_usa_ism_services_pmi_data,
        "usa_jolts": get_usa_jolts_job_openings_data,
        "usa_michigan": get_usa_michigan_consumer_sentiment_data,
        "usa_nfp": get_usa_nfp_data,
        "usa_pce": get_usa_pce_yoy_data,
        "usa_ppi": get_usa_ppi_yoy_data,
        "usa_retail": get_usa_retail_sales_mom_data,
        "usa_trade": get_usa_trade_balance_data,

        # US Yields
        "usa_1m": get_usa_1mo_yield_data,
        "usa_3m": get_usa_3mo_yield_data,
        "usa_6m": get_usa_6mo_yield_data,
        "usa_1y": get_usa_1yr_yield_data,
        "usa_2y": get_usa_2yr_yield_data,
        "usa_3y": get_usa_3yr_yield_data,
        "usa_5y": get_usa_5yr_yield_data,
        "usa_7y": get_usa_7yr_yield_data,
        "usa_10y": get_usa_10yr_yield_data,
        "usa_20y": get_usa_20yr_yield_data,
        "usa_30y": get_usa_30yr_yield_data,

        # UK
        "uk_rate": get_uk_interest_rate_data,
        "uk_cpi": get_uk_cpi_yoy_data,
        "uk_gdp": get_uk_gdp_qoq_data,
        "uk_unemp": get_uk_unemployment_rate_data,
        "uk_10y": get_uk_10yr_yield_data,
        "uk_2y": get_uk_2yr_yield_data,

        # Japan
        "jp_rate": get_japan_interest_rate_data,
        "jp_cpi": get_japan_cpi_yoy_data,
        "jp_gdp": get_japan_gdp_qoq_data,
        "jp_unemp": get_japan_unemployment_rate_data,
        "jp_10y": get_japan_10yr_yield_data,
        "jp_2y": get_japan_2yr_yield_data,

        # Euro
        "eu_rate": get_euro_interest_rate_data,
        "eu_cpi": get_euro_hicp_yoy_data,
        "eu_gdp": get_euro_gdp_qoq_data,
        "eu_unemp": get_euro_unemployment_rate_data,
        "eu_10y": get_euro_10yr_yield_data,
        "eu_2y": get_euro_2yr_yield_data,
    }

    yahoo_map = {
        # FX
        "eurusd": "EURUSD=X",
        "gbpusd": "GBPUSD=X",
        "usdjpy": "USDJPY=X",
        "dxy": "DX-Y.NYB",

        # Equities
        "eq_sp500": "^GSPC",
        "eq_nasdaq": "^IXIC",
        "eq_dow": "^DJI",
        "eq_ftse": "^FTSE",
        "eq_nikkei": "^N225",
        "eq_dax": "^GDAXI",
        "eq_msci_em": "EEM",
        "eq_vix": "^VIX",

        # Stocks
        "st_aapl": "AAPL",
        "st_amzn": "AMZN",
        "st_meta": "META",
        "st_googl": "GOOGL",
        "st_nvda": "NVDA",
        "st_msft": "MSFT",
        "st_tsla": "TSLA",

        # Commodities
        "cmd_gold": "GC=F",
        "cmd_silver": "SI=F",
        "cmd_wti": "CL=F",
        "cmd_brent": "BZ=F",
        "cmd_ng": "NG=F",
        "cmd_wheat": "ZW=F",
        "cmd_copper": "HG=F",
        "cmd_corn": "ZC=F",
        "cmd_soy": "ZS=F",

        # Crypto
        "crypto_btc": "BTC-USD",
        "crypto_eth": "ETH-USD",
    }

    if code in loader_map:
        return loader_map[code]()

    if code in yahoo_map:
        return get_fx_data_yahoo(
            yahoo_map[code],
            start_date=dt.date(1980, 1, 1),
            end_date=dt.date.today()
        )

    return pd.DataFrame()

def analyze_series(df: pd.DataFrame, window: int = 12):
    """
    Compute statistical, trend, and regime metrics for a macro series.

    Args:
        df (pd.DataFrame): Must contain 'date' and 'value'.
        window (int): Rolling window for slope/trend (default 12 for 1 year if monthly).

    Returns:
        dict: Dictionary of key metrics
    """
    if df.empty or "value" not in df.columns:
        return {}

    latest_value = df["value"].iloc[-1]
    hist_mean = df["value"].mean()
    hist_std = df["value"].std()
    z_score = (latest_value - hist_mean) / hist_std if hist_std != 0 else np.nan
    percentile = (df["value"] <= latest_value).mean() * 100  # percentile rank

    # Rolling slope (trend)
    if len(df) >= window:
        y = df["value"].iloc[-window:]
        x = np.arange(len(y))
        slope = np.polyfit(x, y, 1)[0]  # slope of linear regression
        rolling_vol = y.pct_change().rolling(window=window).std().iloc[-1] * 100  # % vol
    else:
        slope = np.nan
        rolling_vol = np.nan

    # YoY or MoM change (last period vs previous same period)
    if len(df) > 1:
        yoy_change = latest_value - df["value"].iloc[-2]
    else:
        yoy_change = np.nan

    # Regime classification based on z-score
    if abs(z_score) < 1:
        regime = "Normal"
    elif abs(z_score) < 2:
        regime = "Elevated"
    else:
        regime = "Extreme"

    return {
        "latest_value": latest_value,
        "hist_mean": hist_mean,
        "hist_std": hist_std,
        "z_score": z_score,
        "percentile": percentile,
        "trend_slope": slope,
        "yoy_change": yoy_change,
        "rolling_vol": rolling_vol,
        "regime": regime,
        "obs_count": len(df)
    }


    
@st.cache_data(ttl=1800)
def load_local_macro_data(file_name, freq="monthly", value_col="Rate"):
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "data", file_name)

    if freq == "daily":
        df = pd.read_csv(file_path, sep=r"\s+")
    else:
        df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    df.columns = df.columns.str.strip()

    if freq == "quarterly":
        df.rename(columns={"Date": "quarter", value_col: "value"}, inplace=True)

        def parse_quarter(q):
            q = str(q).strip()
            if "Q" not in q:
                return pd.NaT
            quarter, year = q.split()
            month_map = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
            month = month_map.get(quarter, 3)
            return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)

        df["date"] = df["quarter"].apply(parse_quarter)
        df = df[["date", "value"]]

    else:
        df.rename(columns={"Date": "date", value_col: "value"}, inplace=True)
        df["date"] = pd.to_datetime(
            df["date"],
            format="%B %Y" if freq == "monthly" else None,
            errors="coerce"
        )

    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"])
    df = df.sort_values("date").reset_index(drop=True)

    return df
    
    
# ---------------------------
# Generic USA Data Loader
# ---------------------------
@st.cache_data(ttl=1800)
def load_usa_data(file_name: str, freq: str = "monthly", date_format: str = "%B %Y"):
    """
    Generic function to load USA macro data from text files.
    
    Args:
        file_name (str): Name of the file inside project folder (e.g. 'USA_CPI_YoY.txt').
        freq (str): Frequency of the data ('daily', 'monthly', 'quarterly').
        date_format (str): Format to parse date column (default '%B %Y' for 'January 2008').
    """
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "data", file_name)

    # Detect delimiter type
    if freq == "daily":
        df = pd.read_csv(file_path, sep=r"\s+")
    else:
        df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    if "Rate" in df.columns:
        df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)
    else:
        df.rename(columns={"Date": "date"}, inplace=True)

    # Convert value column to float if present
    if "value" in df.columns:
        df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Handle date parsing
    if freq == "monthly":
        df["date"] = pd.to_datetime(df["date"], format=date_format, errors="coerce")
    elif freq == "quarterly":
        def parse_quarter(q):
            q = str(q).strip()
            if "Q" not in q:
                return pd.NaT
            quarter, year = q.split()
            month_map = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
            month = month_map.get(quarter, 3)
            return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)
        df["date"] = df["date"].apply(parse_quarter)
    else:  # daily
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid rows and sort
    df = df.dropna(subset=["date"])
    if "value" in df.columns:
        df = df.dropna(subset=["value"])
    df = df.sort_values("date").reset_index(drop=True)

    return df

    
@st.cache_data
def prepare_df(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Standardize DataFrame for Compare tab by ensuring 'Date' and 'Value_label'."""
    df = df.copy()

    # Detect date column
    date_col = None
    for candidate in ["Date", "date", "Quarter", "Time", "Datetime", "Index"]:
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col is None:
        raise ValueError(f"No date-like column found in dataset {label}")

    # Detect numeric column (first non-date)
    value_col = None
    for col in df.columns:
        if col != date_col and pd.api.types.is_numeric_dtype(df[col]):
            value_col = col
            break
    if value_col is None:
        raise ValueError(f"No numeric value column found in dataset {label}")

    # Rename for Compare
    df = df.rename(columns={date_col: "Date", value_col: f"Value_{label}"})
    return df[["Date", f"Value_{label}"]]

#####-----Streamlit App-----#####

# --- Streamlit page config (tab title + favicon + layout) ---
st.set_page_config(
    page_title="Macro Lens Research",      # Browser tab title
    page_icon="logo_favicon.png",                  # Your logo file (32x32px recommended)
    layout="wide",                         # Keeps your wide layout
    initial_sidebar_state="auto"           # Optional: auto expand/collapse sidebar
)

# --- Umami Analytics (add right here) ---
components.html("""
<script defer src="https://cloud.umami.is/script.js" data-website-id="4fd6c49f-bf1f-4823-870d-31e2ffe75961"></script>
""", height=0)

# --- Global Styles ---
st.markdown("""
<style>
/* Mobile responsiveness adjustments */
@media only screen and (max-width: 768px) {
    .block-container {
        padding: 0.5rem 0.5rem !important;
    }

    .custom-header {
        height: auto !important;
        min-height: 84px !important;
        padding: 8px 0 10px 0 !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
    }

    .custom-header .logo {
        position: static !important;
        left: auto !important;
        font-size: 1.05rem !important;
        margin-bottom: 8px !important;
        text-align: center !important;
    }

    .custom-header .menu {
        gap: 1.1rem !important;
        flex-wrap: nowrap !important;
        justify-content: center !important;
        width: 100% !important;
    }

    .dropdown-btn {
        font-size: 0.95rem !important;
    }

    .dropdown-content {
        left: 50% !important;
        transform: translateX(-50%) !important;
        max-width: 92vw !important;
        z-index: 10000 !important;
    }

    .dropdown-content a {
        font-size: 14px !important;
        padding: 10px 4px !important;
    }

    .main-content {
        margin-top: 108px !important;
        padding: 0 0.25rem !important;
    }

    .stSelectbox label, .stDateInput label {
        font-size: 0.9rem !important;
    }

    .stSelectbox div[data-baseweb="select"] {
        font-size: 0.9rem !important;
    }

    .stButton > button {
        width: 100% !important;
    }

    h1, h2, h3 {
        font-size: 1.2rem !important;
    }

    .stPlotlyChart {
        width: 100% !important;
        height: auto !important;
    }
}

/* Prevent horizontal scrollbars */
html, body {
    overflow-x: hidden;
    margin: 0;
    padding: 0;
}

/* Hide Streamlit chrome */
#MainMenu,
header,
footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stStatusWidget {
    visibility: hidden !important;
    display: none !important;
}
/* Remove top padding Streamlit leaves behind */
[data-testid="stHeader"] {
    height: 0px !important;
    display: none !important;
}

[data-testid="stToolbar"] {
    display: none !important;
}

button[kind="header"] {
    display: none !important;
}
.block-container {padding-top: 0rem !important;}

/* Fixed Top Bar */
.custom-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 9999;
    background-color: #F9F9F9;
    width: 100%;
    height: 64px;
    padding: 0;
    display: flex;
    justify-content: center;
    align-items: center;

    border-bottom: 2px solid #DCDCDC;

    transition: box-shadow 0.2s ease, border-bottom 0.2s ease;
}

/* When page is scrolled */
.custom-header.scrolled {
    border-bottom: none;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.custom-header .logo {
    position: absolute;
    left: 32px;
    font-weight: bold;
    font-size: 1.2rem;
}

.custom-header .menu {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 3rem;
}


.custom-header .menu a {
    text-decoration: none;
    font-size: 1rem;
    color: black;
    font-weight: 500;
}

.custom-header .menu a:hover {
    color: #007bff;
}

/* Dropdown menu for countries */
.dropdown {
    position: relative;
    display: inline-block;
}

.dropdown-btn {
    background: none;
    border: none;
    font-size: 1.15rem;
    font-weight: 600;
    cursor: pointer;
    color: black;

    display: flex;
    align-items: center;
    height: 100%;
    padding: 0;
    line-height: 1;
}

.dropdown-content {
    display: none;
    position: absolute;

    left: 50%;
    transform: translateX(-50%);

    background-color: #ffffff;

    width: max-content;
    min-width: 100%;

    border: 2.5px solid #d1d5db;
    border-radius: 10px;

    box-shadow: 0px 8px 16px rgba(0,0,0,0.08);
    z-index: 1;

    overflow: hidden;
}

.dropdown-content {
    padding: 0 16px;
}

.dropdown-content a {
    color: black;
    padding: 12px 4px;
    font-size: 17px !important;
    font-weight: 650 !important;
    white-space: nowrap;

    text-decoration: none;
    display: block;
    

    border-bottom: 1.5px solid #cbd5e1;
}

.dropdown-content a:last-child {
    border-bottom: none;
}

.dropdown-content a:hover {
    background-color: #f1f1f1;
}

.dropdown:hover .dropdown-content {display: block;}
.dropdown:hover .dropdown-btn {color: #007bff;}

/* Main content starts below fixed top bar */
.main-content {
    margin-top: 80px;  /* same height as .custom-header */
    padding: 0 1rem;
}

/* Hero section */
.hero {
    padding: 0;
    margin: 0 0 2rem 0;
    text-align: center;
}

.hero h1 {
    font-size: 2.5rem;
    font-weight: bold;
    margin: 0.2rem 0 0.5rem 0;
    color: #111;
    line-height: 1.2;
}

.hero p {
    font-size: 1.15rem;
    color: #444;
    margin-bottom: 1.8rem;
}
</style>
""", unsafe_allow_html=True)

# --- Fixed Top Bar (HTML block) ---
st.markdown("""
<div class="custom-header">
    <div class="logo">
        <a href="?page=Home" target="_self" style="text-decoration: none; color: inherit;">
            MACROLENS
        </a>
    </div>
    <div class="menu">
        <div class="dropdown">
            <button class="dropdown-btn">Economies ▾</button>
            <div class="dropdown-content">
                <a href="?page=UnitedStates" target="_self">United States</a>
                <a href="?page=EuroArea" target="_self">Euro Area</a>
                <a href="?page=UnitedKingdom" target="_self">United Kingdom</a>
                <a href="?page=Japan" target="_self">Japan</a>
            </div>
        </div>
        <div class="dropdown">
            <button class="dropdown-btn">Markets ▾</button>
            <div class="dropdown-content">                              
                <a href="?page=RatesBonds" target="_self">Rates & Bonds</a>
                <a href="?page=Equities" target="_self">Equities</a>
                <a href="?page=Commodities" target="_self">Commodities</a>
                <a href="?page=FX" target="_self">FX</a> 
                <a href="?page=Crypto" target="_self">Crypto</a>
            </div>
        </div>
        <div class="dropdown">
            <button class="dropdown-btn">Research ▾</button>
            <div class="dropdown-content">
                <a href="?page=GlobalMacroView" target="_self">Global Macro View</a>
                <a href="?page=CentralBankWatch" target="_self">Central Bank Watch</a>
                <a href="?page=RegimeMonitor" target="_self">Regime Monitor</a> 
                <a href="?page=ResearchNotes" target="_self">Research Notes</a>                
                <a href="?page=Calendar" target="_self">Calendar</a>               
            </div>    
        </div>
    </div>    
</div>
""", unsafe_allow_html=True)

# --- JS to toggle shadow on scroll ---
st.markdown("""
<script>
window.addEventListener('scroll', function() {
    const header = document.querySelector('.custom-header');
    if (window.scrollY > 10) {
        header.classList.add('scrolled');
    } else {
        header.classList.remove('scrolled');
    }
});
</script>
""", unsafe_allow_html=True)

query_params = st.query_params
page = query_params.get("page", "Home")  # default to Home if not specified

page_titles = {
    "Home": "Home",
    "UnitedStates": "United States",
    "EuroArea": "Euro Area",
    "UnitedKingdom": "United Kingdom",
    "Japan": "Japan",
    "RatesBonds": "Rates & Bonds",
    "Equities": "Equities",
    "Commodities": "Commodities",
    "FX": "FX",
    "Crypto": "Crypto",
    "GlobalMacroView": "Global Macro View",
    "CentralBankWatch": "Central Bank Watch",
    "RegimeMonitor": "Regime Monitor",
    "ResearchNotes": "Research Notes",
    "Calendar": "Calendar",
}

page_title = page_titles.get(page, page)

# --- Main content wrapper to start scroll below header ---
st.markdown('<div class="main-content">', unsafe_allow_html=True)

st.markdown("""
<style>
/* --------- Select Box Labels --------- */
label[data-baseweb="select"] {
    font-weight: 700 !important;   /* Bold */
    font-size: 18px !important;    /* Larger font */
    color: #1a1a1a !important;
}
label[data-baseweb="select"]::after {
    content: ":";   /* Colon stuck to word */
}

/* --------- Select Box --------- */
div[data-baseweb="select"] {
    border: 1.5px solid #000000 !important;  /* Black border */
    border-radius: 6px !important;
    font-size: 15px !important;
    background-color: #f5f5f5 !important;   /* Grey background */
}
div[data-baseweb="select"] > div {
    font-size: 15px !important;
    font-weight: 500 !important;
    color: #1a1a1a !important;
}
div[data-baseweb="select"]:hover {
    border-color: #000000 !important;       /* Black on hover */
}

/* --------- Date Input Labels --------- */
label[data-baseweb="input"] {
    font-weight: 700 !important;   /* Bold */
    font-size: 18px !important;    /* Larger font */
    color: #1a1a1a !important;
}
label[data-baseweb="input"]::after {
    content: ":";   /* Colon stuck to word */
}

/* --------- Date Input --------- */
div[data-baseweb="input"] {
    border: 1.5px solid #000000 !important;  /* Black border */
    border-radius: 6px !important;
    font-size: 15px !important;
    /* No background override → keeps Streamlit default */
}
div[data-baseweb="input"] input {
    font-size: 15px !important;
    font-weight: 500 !important;
    color: #1a1a1a !important;
}
div[data-baseweb="input"]:hover {
    border-color: #000000 !important;       /* Black on hover */
}
</style>
""", unsafe_allow_html=True)

# --- Main Content Below Header ---

if page == "Home":

    st.markdown("""
    <style>
    .hero {
        padding: 34px 38px;
        border-radius: 18px;
        background: linear-gradient(135deg, #0b1320 0%, #132238 55%, #0a9396 140%);
        color: white;
        margin-bottom: 22px;
    }
    .hero h1 {
        font-size: 44px;
        font-weight: 850;
        margin-bottom: 8px;
    }
    .hero p {
        font-size: 17px;
        color: #d6e2ea;
        max-width: 850px;
    }
    .section-label {
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #0a9396;
        margin-bottom: 8px;
    }
    .card {
        background: #ffffff;
        border: 1px solid #e6e8eb;
        border-radius: 15px;
        padding: 20px 22px;
        margin-bottom: 16px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.035);
        min-height: 150px;
    }
    .card h3 {
        font-size: 20px;
        font-weight: 800;
        margin: 0 0 12px 0;
        color: #111827;
    }
    .card p, .card li {
        font-size: 14.5px;
        line-height: 1.55;
        color: #374151;
    }
    .regime-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 12px;
        margin-bottom: 18px;
    }
    .regime-box {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 16px;
    }
    .regime-box span {
        display: block;
        font-size: 12px;
        color: #6b7280;
        font-weight: 700;
        text-transform: uppercase;
        margin-bottom: 6px;
    }
    .regime-box b {
        font-size: 18px;
        color: #111827;
    }
    .market-row {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 10px;
        margin-bottom: 18px;
    }
    .market-tile {
        background: #111827;
        color: white;
        border-radius: 12px;
        padding: 14px 16px;
    }
    .market-tile span {
        display: block;
        color: #9ca3af;
        font-size: 12px;
        margin-bottom: 5px;
    }
    .market-tile b {
        font-size: 16px;
    }
    .footer {
        margin-top: 22px;
        padding: 20px;
        border-top: 1px solid #e5e7eb;
        text-align: center;
        font-size: 13px;
        color: #6b7280;
    }
    @media (max-width: 900px) {
        .regime-grid, .market-row {
            grid-template-columns: repeat(2, 1fr);
        }
        .hero h1 {
            font-size: 34px;
        }
    }
    </style>

    <div class="hero">
        <div class="section-label">Independent Macro Research Platform</div>
        <h1>Macro Lens Research</h1>
        <p>
            A macro research dashboard built to track economic regimes, policy cycles,
            cross-asset market signals, and the data that drives global macro decisions.
        </p>
    </div>

    <div class="regime-grid">
        <div class="regime-box"><span>Growth</span><b>Slowing</b></div>
        <div class="regime-box"><span>Inflation</span><b>Sticky</b></div>
        <div class="regime-box"><span>Labor</span><b>Cooling</b></div>
        <div class="regime-box"><span>Policy</span><b>Restrictive</b></div>
    </div>

    <div class="market-row">
        <div class="market-tile"><span>DXY</span><b>In Progress</b></div>
        <div class="market-tile"><span>US 10Y</span><b>In Progress</b></div>
        <div class="market-tile"><span>S&P 500</span><b>In Progress</b></div>
        <div class="market-tile"><span>Gold</span><b>In Progress</b></div>
        <div class="market-tile"><span>WTI Crude</span><b>In Progress</b></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.2, 1, 1])

    with col1:
        st.markdown("""
        <div class="card">
            <h3>Macro Outlook</h3>
            <p>
                The global economy remains in a late-cycle environment. Growth momentum is
                moderating, inflation is no longer accelerating broadly, and central banks
                remain cautious as restrictive policy continues to weigh on activity.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="card">
            <h3>Key Developments</h3>
            <ul>
                <li>Growth momentum is softening.</li>
                <li>Labor markets are cooling.</li>
                <li>Inflation remains above target.</li>
                <li>Policy easing expectations are rising.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown("""
        <div class="card">
            <h3>Current Risks</h3>
            <p><b>Upside:</b> Growth reaccelerates while markets price easier policy.</p>
            <p><b>Downside:</b> Labor deterioration becomes more visible.</p>
            <p><b>Watch:</b> Core inflation, claims, curves, and credit.</p>
        </div>
        """, unsafe_allow_html=True)

    col4, col5 = st.columns([1, 1])

    with col4:
        st.markdown("""
        <div class="card">
            <h3>Research Focus</h3>
            <p>
                MacroLens focuses on growth, inflation, labor markets, central banks,
                fiscal policy, liquidity, currencies, rates, commodities, and equity-market
                implications.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown("""
        <div class="card">
            <h3>Latest Research</h3>
            <p>
                No published research note selected yet. This area can later feature your
                latest monthly macro review, market note, or country-specific regime update.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="footer">
        <p>Built by <b>Macro Lens Research</b> • Independent macro research dashboard</p>
        <p>
            <a href="https://www.linkedin.com/in/alex-ballinger-059919302/" target="_blank">LinkedIn</a> |
            <a href="https://youtube.com/@macrolensresearch" target="_blank">YouTube</a> |
            <a href="https://www.instagram.com/themacrolens_/" target="_blank">Instagram</a>
        </p>
        <p>&copy; 2026 Macro Lens Research. All rights reserved.</p>
    </div>
    """, unsafe_allow_html=True)


if page == "UnitedStates":
    safe_render(render_usa_page, "USA")         
        
if page == "Japan":
    safe_render(render_japan_page, "Japan")

if page == "UnitedKingdom":
    safe_render(render_uk_page, "UK")

if page == "EuroArea":
    safe_render(render_euro_page, "Euro Area")

if page == "FX":
    safe_render(render_fx_page, "FX")
 
if page == "Equities":
    safe_render(render_equities_page, "Equities")
        
if page == "Commodities":
    safe_render(render_commodities_page, "Commodities")
        
if page == "RatesBonds":
    safe_render(render_rates_bonds_page, "Rates & Bonds")
     
if page == "Crypto":
    safe_render(render_crypto_page, "Crypto")
    
if page == "GlobalMacroView":
    render_global_macro_view()