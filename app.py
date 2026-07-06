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

st.set_page_config(
    page_title="MacroLens Research",
    layout="wide",
    initial_sidebar_state="collapsed"
)

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

from app_pages.regime_monitor import render_regime_monitor_page

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
    get_japan_retail_sales_mom_data,
)

from models.country_analysis import (
    analyze_usa,
    analyze_uk,
    analyze_euro,
    analyze_japan,
)

from app_pages.under_construction import render_under_construction_page

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





# -------- Asset Map (Global Reference) --------
asset_map = {

    "FX": ["eurusd","gbpusd","usdjpy","dxy"],
    "Equities": ["eq_sp500","eq_nasdaq","eq_dow","eq_ftse","eq_nikkei","eq_dax","eq_msci_em","eq_vix"],
    "Stocks": ["st_aapl","st_amzn","st_meta","st_googl","st_nvda","st_msft","st_tsla"],
    "Commodities": ["cmd_gold","cmd_silver","cmd_wti","cmd_brent","cmd_ng","cmd_wheat","cmd_copper","cmd_corn","cmd_soy"],
    "Crypto": ["crypto_btc","crypto_eth"]
}

# --- Asset display names ---
display_names = {
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


def load_indicator_data(code):

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

from styles.theme import inject_global_css
from components.layout import (
    render_sidebar,
    render_top_strip,
)
from app_pages.home import render_home_page

st.set_page_config(
    page_title="MacroLens Research",
    page_icon="logo_favicon.png",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={}
)

components.html("""
<script defer src="https://cloud.umami.is/script.js" data-website-id="4fd6c49f-bf1f-4823-870d-31e2ffe75961"></script>
""", height=0)

inject_global_css()

page = st.query_params.get("page", "Home")

page_titles = {
    "Home": "Overview",
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

render_sidebar(active_page=page)
if page != "Home":
    render_top_strip(page_titles.get(page, page))

if page == "Home":
    render_home_page()

elif page == "UnitedStates":
    safe_render(render_usa_page, "USA")

elif page == "Japan":
    safe_render(render_japan_page, "Japan")

elif page == "UnitedKingdom":
    safe_render(render_uk_page, "UK")

elif page == "EuroArea":
    safe_render(render_euro_page, "Euro Area")

elif page == "FX":
    safe_render(render_fx_page, "FX")

elif page == "Equities":
    safe_render(render_equities_page, "Equities")

elif page == "Commodities":
    safe_render(render_commodities_page, "Commodities")

elif page == "RatesBonds":
    safe_render(render_rates_bonds_page, "Rates & Bonds")

elif page == "Crypto":
    safe_render(render_crypto_page, "Crypto")

elif page == "GlobalMacroView":
    safe_render(render_global_macro_view, "Global Macro View")

elif page == "CentralBankWatch":
    render_under_construction_page("Central Bank Watch")

elif page == "RegimeMonitor":
    safe_render(render_regime_monitor_page, "Regime Monitor")

elif page == "ResearchNotes":
    render_under_construction_page("Research Notes")

elif page == "Calendar":
    render_under_construction_page("Calendar")
