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

load_dotenv()  # loads .env file

FRED_API_KEY = os.getenv("FRED_API_KEY")
ESTAT_API_KEY = os.getenv("ESTAT_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # fallback if not using Streamlit secrets

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

client = OpenAI(api_key=OPENAI_API_KEY)

# --------- Global Analysis Functions ---------
@st.cache_data(ttl=1800)
def analyze_usa():
    """Compute latest value, slope, and relative position for all USA indicators."""
    usa_tickers = {
        "Interest Rate": get_usa_interest_rate_data,
        "CPI YoY": get_usa_cpi_yoy_data,
        "GDP Growth Rate": get_usa_gdp_qoq_data,
        "Unemployment Rate": get_usa_unemployment_rate_data,
        "Core CPI YoY": get_usa_core_cpi_yoy_data,
        "Average Hourly Earnings YoY": get_usa_average_hourly_earnings_yoy_data,
        "Core PCE YoY": get_usa_core_pce_yoy_data,
        "Core PPI YoY": get_usa_core_ppi_yoy_data,
        "Housing Starts MoM": get_usa_housing_starts_mom_data,
        "ISM Manufacturing PMI": get_usa_ism_manufacturing_pmi_data,
        "ISM Services PMI": get_usa_ism_services_pmi_data,
        "Jolts Job Openings": get_usa_jolts_job_openings_data,
        "Michigan Consumer Sentiment": get_usa_michigan_consumer_sentiment_data,
        "Non Farm Payrolls": get_usa_nfp_data,
        "PCE YoY": get_usa_pce_yoy_data,
        "PPI YoY": get_usa_ppi_yoy_data,
        "Retail Sales MoM": get_usa_retail_sales_mom_data,
        "Trade Balance": get_usa_trade_balance_data
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
            st.warning(f"⚠️ Could not process {name}: {e}")
    return results

@st.cache_data(ttl=1800)
def analyze_uk():
    """Compute latest value, slope, and relative position for all uk indicators."""
    uk_tickers = {
        "Interest Rate": get_uk_interest_rate_data,
        "CPI YoY": get_uk_cpi_yoy_data,
        "GDP Growth Rate": get_uk_gdp_qoq_data,
        "Unemployment Rate": get_uk_unemployment_rate_data
    }

    results = {}
    for name, func in uk_tickers.items():
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
            st.warning(f"⚠️ Could not process {name}: {e}")
    return results

@st.cache_data(ttl=1800)
def analyze_euro():
    """Compute latest value, slope, and relative position for all euro indicators."""
    euro_tickers = {
        "Interest Rate": get_euro_interest_rate_data,
        "CPI YoY": get_euro_cpi_yoy_data,
        "GDP Growth Rate": get_euro_gdp_qoq_data,
        "Unemployment Rate": get_euro_unemployment_rate_data
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
    "usa_rate": "USA Interest Rate",
    "usa_cpi": "USA CPI YoY",
    "usa_core_cpi": "USA Core CPI YoY",
    "usa_gdp": "USA GDP QoQ",
    "usa_unemp": "USA Unemployment Rate",
    "usa_ahe": "USA Average Hourly Earnings YoY",
    "usa_core_pce": "USA Core PCE YoY",
    "usa_core_ppi": "USA Core PPI YoY",
    "usa_housing": "USA Housing Starts MoM",
    "usa_ism_manu": "USA ISM Manufacturing PMI",
    "usa_ism_serv": "USA ISM Services PMI",
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
            # USA
            if code == "usa_rate": return get_usa_interest_rate_data()
            if code == "usa_cpi": return get_usa_cpi_yoy_data()
            if code == "usa_core_cpi": return get_usa_core_cpi_yoy_data()
            if code == "usa_gdp": return get_usa_gdp_qoq_data()
            if code == "usa_unemp": return get_usa_unemployment_rate_data()
            if code == "usa_ahe": return get_usa_average_hourly_earnings_yoy_data()
            if code == "usa_core_pce": return get_usa_core_pce_yoy_data()
            if code == "usa_core_ppi": return get_usa_core_ppi_yoy_data()
            if code == "usa_housing": return get_usa_housing_starts_mom_data()
            if code == "usa_ism_manu": return get_usa_ism_manufacturing_pmi_data()
            if code == "usa_ism_serv": return get_usa_ism_services_pmi_data()
            if code == "usa_jolts": return get_usa_jolts_job_openings_data()
            if code == "usa_michigan": return get_usa_michigan_consumer_sentiment_data()
            if code == "usa_nfp": return get_usa_nfp_data()
            if code == "usa_pce": return get_usa_pce_yoy_data()
            if code == "usa_ppi": return get_usa_ppi_yoy_data()
            if code == "usa_retail": return get_usa_retail_sales_mom_data()
            if code == "usa_trade": return get_usa_trade_balance_data()

            # Yields
            if code == "usa_1m": return get_usa_1mo_yield_data()
            if code == "usa_3m": return get_usa_3mo_yield_data()
            if code == "usa_6m": return get_usa_6mo_yield_data()
            if code == "usa_1y": return get_usa_1yr_yield_data()
            if code == "usa_2y": return get_usa_2yr_yield_data()
            if code == "usa_3y": return get_usa_3yr_yield_data()
            if code == "usa_5y": return get_usa_5yr_yield_data()
            if code == "usa_7y": return get_usa_7yr_yield_data()
            if code == "usa_10y": return get_usa_10yr_yield_data()
            if code == "usa_20y": return get_usa_20yr_yield_data()
            if code == "usa_30y": return get_usa_30yr_yield_data()


            # UK
            if code == "uk_rate": return get_uk_interest_rate_data()
            if code == "uk_cpi": return get_uk_cpi_yoy_data()
            if code == "uk_gdp": return get_uk_gdp_qoq_data()
            if code == "uk_unemp": return get_uk_unemployment_rate_data()
            if code == "uk_10y": return get_uk_10yr_yield_data()
            if code == "uk_2y": return get_uk_2yr_yield_data()

            # Japan
            if code == "jp_rate": return get_japan_interest_rate_data()
            if code == "jp_cpi": return get_japan_cpi_yoy_data()
            if code == "jp_gdp": return get_japan_gdp_qoq_data()
            if code == "jp_unemp": return get_japan_unemployment_rate_data()
            if code == "jp_10y": return get_japan_10yr_yield_data()
            if code == "jp_2y": return get_japan_2yr_yield_data()

            # Euro
            if code == "eu_rate": return get_euro_interest_rate_data()
            if code == "eu_cpi": return get_euro_cpi_yoy_data()
            if code == "eu_gdp": return get_euro_gdp_qoq_data()
            if code == "eu_unemp": return get_euro_unemployment_rate_data()
            if code == "eu_10y": return get_euro_10yr_yield_data()
            if code == "eu_2y": return get_euro_2yr_yield_data()

            # FX
            if code == "eurusd": return get_fx_data_yahoo("EURUSD=X", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "gbpusd": return get_fx_data_yahoo("GBPUSD=X", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "usdjpy": return get_fx_data_yahoo("USDJPY=X", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "dxy": return get_fx_data_yahoo("DX-Y.NYB", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            
            # Equities
            if code == "eq_sp500": return get_fx_data_yahoo("^GSPC", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_nasdaq": return get_fx_data_yahoo("^IXIC", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_dow": return get_fx_data_yahoo("^DJI", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_ftse": return get_fx_data_yahoo("^FTSE", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_nikkei": return get_fx_data_yahoo("^N225", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_dax": return get_fx_data_yahoo("^GDAXI", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_msci_em": return get_fx_data_yahoo("EEM", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_vix": return get_fx_data_yahoo("^VIX", start_date=dt.date(1980,1,1), end_date=dt.date.today())

            # Stocks
            if code == "st_aapl": return get_fx_data_yahoo("AAPL", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_amzn": return get_fx_data_yahoo("AMZN", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_meta": return get_fx_data_yahoo("META", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_googl": return get_fx_data_yahoo("GOOGL", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_nvda": return get_fx_data_yahoo("NVDA", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_msft": return get_fx_data_yahoo("MSFT", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_tsla": return get_fx_data_yahoo("TSLA", start_date=dt.date(1980,1,1), end_date=dt.date.today())

            # Commodities
            if code == "cmd_gold": return get_fx_data_yahoo("GC=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_silver": return get_fx_data_yahoo("SI=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_wti": return get_fx_data_yahoo("CL=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_brent": return get_fx_data_yahoo("BZ=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_ng": return get_fx_data_yahoo("NG=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_wheat": return get_fx_data_yahoo("ZW=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_copper": return get_fx_data_yahoo("HG=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_corn": return get_fx_data_yahoo("ZC=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_soy": return get_fx_data_yahoo("ZS=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            
            # Crypto
            if code == "crypto_btc": return get_fx_data_yahoo("BTC-USD", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "crypto_eth": return get_fx_data_yahoo("ETH-USD", start_date=dt.date(1980,1,1), end_date=dt.date.today())


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

def simulate_scenario(df: pd.DataFrame, shock_value: float, shock_type: str = "absolute", periods: int = 12):
    """
    Simulate a macro scenario by applying a shock to the last value of a series
    and projecting it forward.

    Args:
        df (pd.DataFrame): Must contain 'date' and 'value' columns.
        shock_value (float): Amount of shock (absolute or percent).
        shock_type (str): "absolute" or "percent".
        periods (int): Number of periods to project forward.

    Returns:
        pd.DataFrame: Projected series with dates extended.
    """
    if df.empty or "value" not in df.columns:
        return pd.DataFrame(columns=["date", "value"])

    last_value = df["value"].iloc[-1]

    # Determine projected values
    proj_values = []
    for i in range(periods):
        if shock_type == "absolute":
            last_value = last_value + shock_value
        elif shock_type == "percent":
            last_value = last_value * (1 + shock_value / 100)
        proj_values.append(last_value)

    # Create projected dates
    last_date = df["date"].iloc[-1]
    # Determine frequency (monthly or quarterly)
    if df["date"].diff().median().days >= 80:  # approx quarterly
        freq = 'Q'
    else:
        freq = 'M'
    proj_dates = pd.date_range(start=last_date + pd.offsets.MonthBegin(1), periods=periods, freq=freq)

    df_proj = pd.DataFrame({"date": proj_dates, "value": proj_values})
    return df_proj


# -------- Helper Functions --------
def plot_chart(df, title, chart_type, height=450, date_format="daily",
               yaxis_suffix='', reference_lines=None, shaded_regions=None,
               tickformat_override=None, hover_style="delta", delta_type="cumulative", show_markers=False):

    df = df.copy()
    chart_color = '#1f77b4'

    # -------------------- Hover Formatting --------------------
    if date_format == "daily":
        hover_date_format = "%d %B %Y"
    elif date_format == "monthly":
        hover_date_format = "%B %Y"
    elif date_format == "quarterly":
        # handled separately inside hover_style
        hover_date_format = None
    else:
        hover_date_format = "%Y-%m-%d"

    # -------------------- Chart Type --------------------
    mode = 'lines+markers' if show_markers else 'lines'
    if chart_type == "Line":
        fig = px.line(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(line=dict(width=2, color=chart_color), mode=mode)
    elif chart_type == "Step":
        fig = px.line(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(line_shape='hv', line=dict(width=2, color=chart_color), mode=mode)
    elif chart_type == "Area":
        fig = px.area(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(line_color=chart_color, fillcolor='rgba(31,119,180,0.3)')
    elif chart_type == "Bar":
        fig = px.bar(df, x='date', y='value', title=title, labels={'date': '', 'value': ''}, height=height)
        fig.update_traces(marker_color=chart_color, marker_line_color='black', marker_line_width=1)
    else:
        raise ValueError(f"Unsupported chart_type: {chart_type}")

    # -------------------- Layout --------------------
    fig.update_layout(
        margin=dict(l=40, r=30, t=60, b=20),
        hovermode='closest',
        dragmode=False,
        title=dict(font=dict(size=20, family="Arial Bold"), x=0.5, xanchor='center'),
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor='black',
            linewidth=2,
            ticks='outside',
            ticklen=10,
            tickwidth=2,
            tickfont=dict(size=14, family="Arial Bold", color="black")
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='LightGrey',
            gridwidth=0.3,
            showline=True,
            linecolor='black',
            linewidth=2,
            ticks='outside',
            tickfont=dict(size=14, family="Arial Bold", color="black"),
            tickformat=f',.2f{yaxis_suffix}'
        ),
        hoverlabel=dict(
            font_size=16,
            bgcolor="#F9F9F9",  # Updated hover box color
            bordercolor="black",
            align="left",
            namelength=0
        )
    )

    # -------------------- Reference Lines --------------------
    if reference_lines:
        for ref in reference_lines:
            fig.add_hline(y=ref['value'], line_dash='dash', line_color='red',
                          annotation_text=ref.get('label', ''),
                          annotation_position="top left",
                          annotation_font=dict(size=12, color='red'))

    # -------------------- Shaded Regions --------------------
    if shaded_regions:
        for region in shaded_regions:
            fig.add_vrect(x0=region['start'], x1=region['end'],
                          fillcolor=region.get('color', 'LightGrey'),
                          opacity=region.get('opacity', 0.3),
                          layer="below",
                          line_width=0)

    # -------------------- Hover Styles --------------------
    if hover_style == "delta":
        if delta_type == "daily":
            df['delta'] = df['value'].pct_change() * 100
        else:  # cumulative
            df['delta'] = (df['value'] / df['value'].iloc[0] - 1) * 100

        df['delta_str'] = df['delta'].apply(
            lambda x: f"▲ {x:.2f}%" if x > 0 else (
                f"▼ {abs(x):.2f}%" if pd.notnull(x) and x < 0 else "— 0.00%"
            )
        )
        df['delta_color'] = df['delta'].apply(
            lambda x: "green" if x > 0 else ("red" if x < 0 else "gray")
        )

        if date_format == "quarterly":
            # Quarterly: use custom Q labels
            df['hover_label'] = df['date'].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_traces(
                customdata=df[['hover_label', 'delta_str', 'delta_color']],
                hovertemplate=(
                    "<span style='color:black'><b>%{customdata[0]}</b></span><br>"   # Quarter
                    "<span style='color:black'>%{y:,.2f}" + yaxis_suffix + "</span><br>"  # Value
                    "<span style='color:%{customdata[2]}; font-weight:bold'>%{customdata[1]}</span>"
                    "<extra></extra>"
                )
            )
        else:
            # Daily/Monthly/Yearly
            fig.update_traces(
                customdata=df[['delta_str', 'delta_color']],
                hovertemplate=(
                    "<span style='color:black'><b>%{x|" + hover_date_format + "}</b></span><br>"
                    "<span style='color:black'>%{y:,.2f}" + yaxis_suffix + "</span><br>"
                    "<span style='color:%{customdata[1]}; font-weight:bold'>%{customdata[0]}</span>"
                    "<extra></extra>"
                )
            )

    else:
        if date_format == "quarterly":
            df['hover_label'] = df['date'].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_traces(
                customdata=df['hover_label'],
                hovertemplate="<b>%{customdata}</b><br>%{y:,.2f}" + yaxis_suffix + "<extra></extra>"
            )
            tickvals = df[df['date'].dt.quarter == 4]['date']
            ticktext = df[df['date'].dt.quarter == 4]['hover_label']
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)
        else:
            hovertemplate = (
                "<span style='color:black'><b>%{x|" + hover_date_format + "}</b></span><br>"
                "<span style='color:black'>%{y:,.2f}" + yaxis_suffix + "</span><extra></extra>"
            )

            fig.update_traces(hovertemplate=hovertemplate)

            if tickformat_override:
                df['tick_label'] = df['date'].dt.strftime(tickformat_override)
                fig.update_xaxes(
                    tickmode='array',
                    tickvals=df['date'],
                    ticktext=df['tick_label']
                )

    return fig
    
import pandas as pd
import plotly.graph_objects as go

def plot_scenario_chart(df, threshold_pct=4.0, window=30, window_unit='days',
                        yaxis_suffix='', start_date=None, end_date=None):
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    df.sort_values('date', inplace=True)
    df = df.reset_index(drop=True)

    # ---- Clamp to valid date range ----
    today = pd.Timestamp.today().normalize()
    df = df[df['date'] <= today]
    if start_date:
        df = df[df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['date'] <= pd.to_datetime(end_date)]

    # ---- Calculate daily % change ----
    df['daily_return'] = df['value'].pct_change() * 100
    df['trigger'] = df['daily_return'].abs() >= threshold_pct

    # ---- Determine window length ----
    if window_unit == 'days':
        delta = pd.Timedelta(days=window)
    elif window_unit == 'weeks':
        delta = pd.Timedelta(weeks=window)
    elif window_unit == 'months':
        delta = pd.DateOffset(months=window)
    elif window_unit == 'years':
        delta = pd.DateOffset(years=window)
    else:
        delta = pd.Timedelta(days=window)

    # ---- Build highlighted segments ----
    segments = []
    n = len(df)
    base_color = '#1f77b4'  # default blue
    trigger_color = 'orange'

    i = 0
    trigger_rows = []

    while i < n - 1:
        if df.loc[i, 'trigger']:
            start_idx = i
            end_date = df.loc[i, 'date'] + delta
            after_idx = df[df['date'] <= end_date].index.max() if any(df['date'] <= end_date) else i

            # Highlight trigger day
            segments.append({
                'x': df.loc[start_idx:start_idx + 1, 'date'],
                'y': df.loc[start_idx:start_idx + 1, 'value'],
                'color': trigger_color
            })

            # Record stats for table
            start_price = df.loc[start_idx, 'value']
            end_price = df.loc[after_idx, 'value']
            total_return = (end_price / start_price - 1) * 100
            trigger_rows.append({
                'Trigger Date': df.loc[start_idx, 'date'].strftime("%Y-%m-%d"),
                'Move %': round(df.loc[start_idx, 'daily_return'], 2),
                f'{window} {window_unit} Return %': round(total_return, 2)
            })

            i = after_idx
        else:
            next_trigger = df.index[(df.index > i) & (df['trigger'])].min() if any(df['trigger'][i+1:]) else n - 1
            segments.append({
                'x': df.loc[i:next_trigger, 'date'],
                'y': df.loc[i:next_trigger, 'value'],
                'color': base_color
            })
            i = next_trigger

    # ---- Create the figure ----
    fig = go.Figure()
    for seg in segments:
        fig.add_trace(go.Scatter(
            x=seg['x'], y=seg['y'],
            mode='lines',
            line=dict(color=seg['color'], width=3),
            hovertemplate="<b>%{x|%d %B %Y}</b><br>%{y:,.2f}" + yaxis_suffix + "<extra></extra>"
        ))

    fig.update_layout(
        title=f"{threshold_pct}% Daily Move (Highlighted in Orange)",
        margin=dict(l=40, r=30, t=60, b=20),
        hovermode='x unified',
        xaxis=dict(showgrid=False, showline=True, linecolor='black', linewidth=2),
        yaxis=dict(showgrid=True, gridcolor='LightGrey', gridwidth=0.3,
                   showline=True, linecolor='black', linewidth=2,
                   tickformat=f',.2f{yaxis_suffix}'),
    )

    # ---- Summary Table ----
    if trigger_rows:
        table_df = pd.DataFrame(trigger_rows)
    else:
        table_df = pd.DataFrame(columns=['Trigger Date', 'Move %', f'{window} {window_unit} Return %'])

    return fig, table_df



    
@st.cache_data
def get_japan_interest_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_Interest_Rate.txt")
    
    # Use whitespace delimiter for space/tab-separated file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names to remove hidden spaces
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Drop any rows where date could not be parsed
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_japan_cpi_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_CPI_YoY.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df
    
@st.cache_data    
def get_japan_gdp_qoq_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_GDP_Growth_Rate_QoQ.txt")
    
    # Read the file (split on 2+ spaces, so "Q1 2008" stays together)
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean up column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "quarter", "Rate": "value"}, inplace=True)

    # Function to convert "Q1 2008" -> datetime (end of quarter)
    def parse_quarter(q):
        q = str(q).strip()
        if "Q" not in q:
            return pd.NaT
        quarter, year = q.split()
        month_map = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
        month = month_map.get(quarter, 3)
        return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)

    df["date"] = df["quarter"].apply(parse_quarter)

    # Keep only relevant columns
    df = df[["date", "value"]]

    # Convert value to numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)

    return df
    
@st.cache_data    
def get_japan_unemployment_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_Unemployment_Rate.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_japan_10yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_10_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_japan_2yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "Japan_2_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data
def get_uk_interest_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_Interest_Rate.txt")
    
    # Use whitespace delimiter for space/tab-separated file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names to remove hidden spaces
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Drop any rows where date could not be parsed
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_uk_cpi_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_CPI_YoY.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_uk_gdp_qoq_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_GDP_Growth_Rate_QoQ.txt")
    
    # Read the file (split on 2+ spaces, so "Q1 2008" stays together)
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean up column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "quarter", "Rate": "value"}, inplace=True)

    # Function to convert "Q1 2008" -> datetime (end of quarter)
    def parse_quarter(q):
        q = str(q).strip()
        if "Q" not in q:
            return pd.NaT
        quarter, year = q.split()
        month_map = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
        month = month_map.get(quarter, 3)
        return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)

    df["date"] = df["quarter"].apply(parse_quarter)

    # Keep only relevant columns
    df = df[["date", "value"]]

    # Convert value to numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_uk_unemployment_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_Unemployment_Rate.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_uk_10yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_10_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_uk_2yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "UK_2_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_euro_interest_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_Interest_Rate.txt")
    
    # Use whitespace delimiter for space/tab-separated file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names to remove hidden spaces
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert date column to datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # Drop any rows where date could not be parsed
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_euro_cpi_yoy_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_CPI_YoY.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_euro_gdp_qoq_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_GDP_Growth_Rate_QoQ.txt")
    
    # Read the file (split on 2+ spaces, so "Q1 2008" stays together)
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean up column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "quarter", "Rate": "value"}, inplace=True)

    # Function to convert "Q1 2008" -> datetime (end of quarter)
    def parse_quarter(q):
        q = str(q).strip()
        if "Q" not in q:
            return pd.NaT
        quarter, year = q.split()
        month_map = {"Q1": 3, "Q2": 6, "Q3": 9, "Q4": 12}
        month = month_map.get(quarter, 3)
        return pd.Timestamp(year=int(year), month=month, day=1) + pd.offsets.MonthEnd(0)

    df["date"] = df["quarter"].apply(parse_quarter)

    # Keep only relevant columns
    df = df[["date", "value"]]

    # Convert value to numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop invalid rows
    df = df.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_euro_unemployment_rate_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_Unemployment_Rate.txt")
    
    # Read using regex for 2+ spaces
    df = pd.read_csv(file_path, sep=r"\s{2,}", engine="python")

    # Clean column names
    df.columns = df.columns.str.strip()

    # Rename columns for consistency
    df.rename(columns={"Date": "date", "Rate": "value"}, inplace=True)

    # Convert value to float
    df['value'] = pd.to_numeric(df['value'], errors='coerce')

    # Drop invalid rows
    df = df.dropna(subset=['value'])

    # Convert Month Year to datetime
    df['date'] = pd.to_datetime(df['date'], format="%B %Y", errors='coerce')

    # Drop rows with invalid dates
    df = df.dropna(subset=['date'])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data   
def get_euro_10yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_10_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df

@st.cache_data    
def get_euro_2yr_yield_data():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "EURO_2_Year_Yield.txt")
        
    # Read tab or whitespace-delimited file
    df = pd.read_csv(file_path, delim_whitespace=True)

    # Strip column names
    df.columns = df.columns.str.strip()

    # Rename for consistency
    df.rename(columns={"Date": "date", "Price": "value"}, inplace=True)

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop invalid dates
    df = df.dropna(subset=["date"])

    # Ensure value is numeric
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    # Drop rows with missing values
    df = df.dropna(subset=["value"])

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    return df
    
# ---------------------------
# Generic USA Data Loader
# ---------------------------
@st.cache_data
def load_usa_data(file_name: str, freq: str = "monthly", date_format: str = "%B %Y"):
    """
    Generic function to load USA macro data from text files.
    
    Args:
        file_name (str): Name of the file inside project folder (e.g. 'USA_CPI_YoY.txt').
        freq (str): Frequency of the data ('daily', 'monthly', 'quarterly').
        date_format (str): Format to parse date column (default '%B %Y' for 'January 2008').
    """
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, file_name)

    # Detect delimiter type
    if freq == "daily":
        df = pd.read_csv(file_path, delim_whitespace=True)
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


# ---------------------------
# Indicator-Specific Wrappers
# ---------------------------
@st.cache_data
def get_usa_interest_rate_data():
    return load_usa_data("USA_Interest_Rate.txt", freq="daily")
@st.cache_data
def get_usa_cpi_yoy_data():
    return load_usa_data("USA_CPI_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_gdp_qoq_data():
    return load_usa_data("USA_GDP_Growth_Rate_QoQ.txt", freq="quarterly")
@st.cache_data
def get_usa_unemployment_rate_data():
    return load_usa_data("USA_Unemployment_Rate.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_core_cpi_yoy_data():
    return load_usa_data("USA_Core_CPI_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_average_hourly_earnings_yoy_data():
    return load_usa_data("USA_Average_Hourly_Earnings_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_core_pce_yoy_data():
    return load_usa_data("USA_Core_PCE_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_core_ppi_yoy_data():
    return load_usa_data("USA_Core_PPI_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_housing_starts_mom_data():
    return load_usa_data("USA_Housing_Starts_MoM.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_ism_manufacturing_pmi_data():
    return load_usa_data("USA_ISM_Manufacturing_PMI.txt", freq="monthly", date_format="%B %Y")
@st.cache_data    
def get_usa_ism_services_pmi_data():
    return load_usa_data("USA_ISM_Services_PMI.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_jolts_job_openings_data():
    return load_usa_data("USA_JOLTS_Job_Openings.txt", freq="monthly", date_format="%B %Y")
@st.cache_data
def get_usa_michigan_consumer_sentiment_data():
    return load_usa_data("USA_Michigan_Consumer_Sentiment_Index.txt", freq="monthly", date_format="%B %Y")
@st.cache_data    
def get_usa_nfp_data():
    return load_usa_data("USA_NFP.txt", freq="monthly", date_format="%B %Y")
@st.cache_data    
def get_usa_pce_yoy_data():
    return load_usa_data("USA_PCE_YoY.txt", freq="monthly", date_format="%B %Y")
@st.cache_data    
def get_usa_ppi_yoy_data():
    return load_usa_data("USA_PPI_YoY.txt", freq="monthly", date_format="%B %Y")    
@st.cache_data   
def get_usa_retail_sales_mom_data():
    return load_usa_data("USA_Retail_Sales_MoM.txt", freq="monthly", date_format="%B %Y")
@st.cache_data   
def get_usa_trade_balance_data():
    return load_usa_data("USA_Trade_Balance.txt", freq="monthly", date_format="%B %Y")
    
# ---------------------------
# FRED API Setup
# ---------------------------
FRED_API_KEY = "3be1b836ee6f78badf0f0a5a4905ab73"   # <- put your key here once

# ---------------------------
# Yield Data Functions
# ---------------------------

@st.cache_data
def get_usa_yield_data(series_id: str):
    """Generic function to fetch US Treasury yields from FRED by series_id."""
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    data = r.json()

    df = pd.DataFrame(data["observations"])
    df = df[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().sort_values("date").reset_index(drop=True)
    return df

# ---------------------------
# Specific US Treasury Yields
# ---------------------------
@st.cache_data
def get_usa_1mo_yield_data():
    return get_usa_yield_data("DGS1MO")
@st.cache_data
def get_usa_3mo_yield_data():
    return get_usa_yield_data("DGS3MO")
@st.cache_data
def get_usa_6mo_yield_data():
    return get_usa_yield_data("DGS6MO")
@st.cache_data
def get_usa_1yr_yield_data():
    return get_usa_yield_data("DGS1")
@st.cache_data
def get_usa_2yr_yield_data():
    return get_usa_yield_data("DGS2")
@st.cache_data
def get_usa_3yr_yield_data():
    return get_usa_yield_data("DGS3")
@st.cache_data
def get_usa_5yr_yield_data():
    return get_usa_yield_data("DGS5")
@st.cache_data
def get_usa_7yr_yield_data():
    return get_usa_yield_data("DGS7")
@st.cache_data
def get_usa_10yr_yield_data():
    return get_usa_yield_data("DGS10")
@st.cache_data
def get_usa_20yr_yield_data():
    return get_usa_yield_data("DGS20")
@st.cache_data
def get_usa_30yr_yield_data():
    return get_usa_yield_data("DGS30")

@st.cache_data
def get_fx_data_yahoo(ticker="GBPUSD=X", start_date=None, end_date=None):
    # Download historical daily data from yfinance
    data = yf.download(ticker, start=start_date, end=end_date, interval="1d", auto_adjust=False)

    if data.empty:
        return pd.DataFrame()  # Return empty DF on failure

    # If multi-index columns, select 'Close' price properly
    if isinstance(data.columns, pd.MultiIndex):
        close_data = data['Close'][ticker]
    else:
        close_data = data['Close']

    # Prepare dataframe with date and close price
    df = pd.DataFrame({
        'date': close_data.index,
        'value': close_data.values
    })

    df = df.sort_values('date').reset_index(drop=True)
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


# --- Global Styles ---
st.markdown("""
<style>
/* Mobile responsiveness adjustments */
@media only screen and (max-width: 768px) {
    .block-container {
        padding: 0.5rem 0.5rem !important;
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

/* Hide default Streamlit UI */
#MainMenu, header, footer {visibility: hidden;}
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
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;

    /* Default = thin border */
    border-bottom: 1px solid #e5e5e5;
    transition: box-shadow 0.2s ease, border-bottom 0.2s ease;
}

/* When page is scrolled */
.custom-header.scrolled {
    border-bottom: none;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.custom-header .logo {
    font-weight: bold;
    font-size: 1.2rem;
}

.custom-header .menu {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 2rem;
    flex: 1;              /* evenly spaces between logo and edges */
    margin: 0 auto;       /* centers horizontally */
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
    font-size: 1rem;
    font-weight: 500;
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
    background-color: #f9f9f9;
    min-width: 160px;
    box-shadow: 0px 8px 16px rgba(0,0,0,0.2);
    z-index: 1;
}

.dropdown-content a {
    color: black;
    padding: 10px 14px;
    text-decoration: none;
    display: block;
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
            <button class="dropdown-btn">Countries ▾</button>
            <div class="dropdown-content">
                <a href="?page=USA" target="_self">USA</a>
                <a href="?page=Japan" target="_self">Japan</a>
                <a href="?page=UK" target="_self">UK</a>
                <a href="?page=EURO" target="_self">Euro Area</a>
            </div>
        </div>
        <div class="dropdown">
            <button class="dropdown-btn">Asset Classes ▾</button>
            <div class="dropdown-content">
                <a href="?page=Equities" target="_self">Equities</a>
                <a href="?page=Stocks" target="_self">Stocks</a>
                <a href="?page=Commodities" target="_self">Commodities</a>
                <a href="?page=Bonds" target="_self">Bonds</a>
                <a href="?page=FX%20Rates" target="_self">FX Rates</a>
                <a href="?page=Crypto" target="_self">Crypto</a>
            </div>
        </div>
        <div class="dropdown">
            <button class="dropdown-btn">Tools + Features ▾</button>
            <div class="dropdown-content">
                <a href="?page=Compare" target="_self">Compare</a>
                <a href="?page=Calendar" target="_self">Calendar</a>
                <a href="?page=Cycle" target="_self">Cycle</a>
                <a href="?page=Reports" target="_self">Reports</a>
                <a href="?page=Scenarios" target="_self">Scenarios</a>
                <a href="?page=Yield Curve" target="_self">Yield Curve</a>
                <a href="?page=Curve Regimes" target="_self">Curve Regimes</a>
                <a href="?page=Seasonality" target="_self">Seasonality</a>
                <a href="?page=Summary" target="_self">Summary</a>
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
                /* Reset page spacing */
        html, body {
            margin: 0;
            padding: 0;
        }

        /* Sticky top navigation bar */
        .navbar {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 1000;
            margin: 0;
            padding: 0.75rem 1rem;  /* adjust to taste */
            background-color: #fff; /* or your theme color */
            border-bottom: 1px solid #eee;
        }

        /* Push content down so it doesn’t overlap navbar */
        .main-content {
            margin-top: 4rem;  /* same height as navbar */
        }

        /* Hero section (dashboard title) */
        .hero {
            padding: 0;
            border: none;
            border-radius: 0;
            box-shadow: none;
            background: none;
            text-align: center;
            margin: 0 0 2rem 0; /* remove top margin */
        }

        .hero h1 {
            font-size: 2.5rem;
            font-weight: bold;
            margin: 0.2rem 0 0.5rem 0;  /* kill default top gap */
            color: #111;
            line-height: 1.2;
        }


        .hero p {
            font-size: 1.15rem;
            color: #444;
            margin-bottom: 1.8rem;
        }

        .section {
            margin-top: 3rem;
        }

        .section h2 {
            font-size: 1.6rem;
            border-bottom: 2px solid #eee;
            padding-bottom: 0.4rem;
            margin-bottom: 1.2rem;
            color: #222;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 1.5rem;
        }

        .feature-box {
            background-color: #ffffff;
            border: 1px solid #ddd;
            padding: 1.2rem 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 1px 5px rgba(0,0,0,0.03);
        }

        .feature-box h3 {
            margin-top: 0;
            margin-bottom: 0.5rem;
            font-size: 1.1rem;
            color: #000;
        }

        .feature-box p {
            font-size: 0.95rem;
            color: #555;
        }

        .hr-separator {
            margin: 3rem 0;
            border: none;
            border-top: 2px solid #eee;
        }

        .chart-title {
            font-size: 1.25rem;
            font-weight: 600;
            text-align: center;
            margin: 1rem 0 0.5rem;
        }

        .footer {
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid #eee;
            font-size: 0.9rem;
            color: #666;
            text-align: center;
        }

        .footer a {
            color: #007bff;
            text-decoration: none;
        }

        .footer a:hover {
            text-decoration: underline;
        }

        .calendar-snippet-container {
            max-width: 700px;
            margin: 0 auto 2rem auto;
            background: none;
            border: none;
            border-radius: 0;
        padding: 0;
            box-shadow: none;
            text-align: center;
        }


        .calendar-snippet-container h3 {
            font-weight: 700;
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: #222;
            border-bottom: 2px solid #ddd;
            padding-bottom: 0.5rem;
        }

        .calendar-event {
            display: inline-block;
            white-space: nowrap;
            font-size: 1rem;
            margin: 0.25rem 0;
            padding: 6px 12px;
            border-radius: 6px;
            background-color: transparent;
            ##border: 1px solid #ccc;
            ##box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .calendar-event > span {
            margin: 0 6px;
        }

        .impact-high {
            color: #ff4d4d;
            font-weight: 700;
        }

        .impact-medium {
            color: #ffa500;
            font-weight: 700;
        }

        .impact-low {
            color: #32cd32;
            font-weight: 700;
        }
        </style>
        
        <div class="hero">
            <h1>Macro Lens Research</h1>
            <p>Monitor global economic and market dynamics — updated daily with interactive data and professional-grade insights.</p>
        </div>
        <hr class="hr-separator"/>
    """, unsafe_allow_html=True)

    # Load and show today's economic events
    try:
        cal_df = pd.read_csv("economic_calendar.csv", parse_dates=["Date"])
    except Exception as e:
        st.error(f"Error loading economic calendar data: {e}")
        cal_df = pd.DataFrame()

    if not cal_df.empty:
        today = pd.to_datetime(dt.date.today())
        todays_events = cal_df[cal_df['Date'] == today]

        if not todays_events.empty:
            calendar_html = (
                '<div class="calendar-snippet-container">'
                '<h3>📅 Today\'s Economic Events</h3>'
            )

            for _, row in todays_events.iterrows():
                impact_class = {
                    "🔴 High": "impact-high",
                    "🟠 Medium": "impact-medium",
                    "🟢 Low": "impact-low"
                }.get(row['Impact'], "")

                calendar_html += (
                    f'<div class="calendar-event">'
                    f'<b>Date:</b> {row["Date"].strftime("%A %d %B")}'
                    f'<span>|</span><b>Time:</b> {row["Time"]}'
                    f'<span>|</span><b>Country:</b> {row["Country"]}'
                    f'<span>|</span><b>Event:</b> {row["Event"]}'
                    f'<span>|</span><span class="{impact_class}">{row["Impact"]}</span>'
                    f'</div>'
                )

            calendar_html += '</div>'
            st.markdown(calendar_html, unsafe_allow_html=True)
        else:
            st.info("No economic events scheduled for today.")

    # Show DXY chart below the calendar snippet
    dxy_df = get_fx_data_yahoo("DX-Y.NYB", start_date=dt.date.today() - dt.timedelta(days=365), end_date=dt.date.today())
    dxy_chart = plot_chart(dxy_df, "DXY (US Dollar Index)", chart_type="Line")

    
    st.plotly_chart(dxy_chart, use_container_width=True)

    # Features and footer
    st.markdown("""
        <div class="section">
            <h2>🔍 What You Can Explore</h2>
            <div class="grid">
                <div class="feature-box">
                    <h3>🌍 Countries</h3>
                    <p>Dive into economic data for the USA, Japan, UK, and Euro Area — interest rates, GDP, inflation, jobs, and more.</p>
                </div>
                <div class="feature-box">
                    <h3>💹 Asset Classes</h3>
                    <p>Track Equities, Bonds, Commodities, FX Rates, and Crypto — all in one place, with charts and comparisons.</p>
                </div>
                <div class="feature-box">
                    <h3>📈 Yield Curve & Regimes</h3>
                    <p>Visualize yield curves across countries, spot steepening/inverting regimes, and analyze market signals.</p>
                </div>
                <div class="feature-box">
                    <h3>⚖️ Compare</h3>
                    <p>Overlay any two indicators (e.g., U.S. CPI vs EUR/USD, 10Y yields vs GDP) with dual axes for deeper analysis.</p>
                </div>
                <div class="feature-box">
                    <h3>📅 Calendar</h3>
                    <p>Stay on top of daily global economic events — with impact levels clearly highlighted.</p>
                </div>
                <div class="feature-box">
                    <h3>🔄 Cycle</h3>
                    <p>Assess the U.S. economic cycle using real-time indicators. View the current macro “season”, scoring table and cycle wave</p>
                </div>
            </div>
        </div>


        <div class="section">
            <h2>🚀 How to Use This Dashboard</h2>
            <ul>
                <li><b>Navigate using the top bar</b> — choose a <b>Country</b> (USA, Japan, UK, Euro Area) or an <b>Asset Class</b> (Equities, Bonds, Commodities, FX, Crypto).</li>
                <li><b>Explore Yield Curves & Regimes</b> to track steepening, flattening, or inversion phases across global markets.</li>
                <li><b>Use Compare</b> to overlay any two indicators with dual y-axes for deeper macro insights.</li>
                <li><b>Check the Calendar</b> daily for upcoming economic events, highlighted by impact level.</li>
                <li><b>Visit the Cycle page</b> to assess the current <b>U.S. economic phase</b>, view cycle scores, and read AI-generated summaries.</li>
                <li><b>Adjust chart types and timeframes</b> as needed — everything updates instantly and interactively.</li>
            </ul>
        </div>



        <div class="section">
            <h2>📡 Data Sources</h2>
            <ul>
                <li><b>Asset Classes (Equities, Bonds, Commodities, FX, Crypto):</b> Yahoo Finance</li>
                <li><b>U.S. Yield Curve Data:</b> Federal Reserve Economic Data (FRED)</li>
                <li><b>Economic Indicators (USA, Japan, UK, Euro Area):</b> FXStreet + manually maintained datasets (updated daily)</li>
            </ul>
            <p style="font-size:0.9rem; color:#555; margin-top:0.5rem;">
                <i>Note: All data is updated daily. Some indicators are manually curated for accuracy and completeness.</i>
            </p>
        </div>


        <div class="footer">
            <p>Built by <b>Macro Lens Research</b> • All data updates daily</p>
            <p>
                Contact: <a href="https://www.linkedin.com/in/alex-ballinger-059919302/" target="_blank">LinkedIn</a> |
                <a href="https://youtube.com/@macrolensresearch" target="_blank">YouTube</a> |
                <a href="https://www.instagram.com/themacrolens_/" target="_blank">Instagram</a>
            </p>
            <p>&copy; 2025 Macro Lens Research. All rights reserved.</p>
        </div>
    """, unsafe_allow_html=True)
    
def get_country_summary(key_name, country_prompt, data_text):
    """
    Checks if a summary exists for a country, otherwise generates one using your AI summarizer.
    """
    if key_name in st.session_state:
        return st.session_state[key_name]
    else:
        prompt = f"""
        Summarize the macroeconomic situation for {country_prompt} based on the following data and analysis.
        Focus on growth trends, inflation, labor markets, and financial conditions.
        Keep it concise, professional, and under 150 words.

        --- Data & Context ---
        {data_text}
        """
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=250,
            temperature=0
        )
        summary = response.choices[0].message.content.strip()
        st.session_state[key_name] = summary
        return summary


# Global AI Summary Collector (used across all pages)
if "ai_summaries" not in st.session_state:
    st.session_state["ai_summaries"] = []


# -------- USA Tab --------
if page == "USA":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Labor Market": [
                "Unemployment Rate",
                "Average Hourly Earnings YoY",
                "Jolts Job Openings",
                "Non Farm Payrolls"
            ],
            "Growth": [
                "GDP Growth Rate",
                "Retail Sales MoM",
                "Housing Starts MoM",
                "Trade Balance"
            ],
            "Inflation": [
                "CPI YoY",
                "Core CPI YoY",
                "PCE YoY",
                "Core PCE YoY",
                "PPI YoY",
                "Core PPI YoY"
            ],
            "Surveys": [
                "ISM Manufacturing PMI",
                "ISM Services PMI",
                "Michigan Consumer Sentiment"
            ],
            "Monetary Policy": [
                "Interest Rate"
            ]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        indicator_map = {
            "Interest Rate": (get_usa_interest_rate_data, "daily", "%b %Y"),
            "CPI YoY": (get_usa_cpi_yoy_data, "monthly", None),
            "GDP Growth Rate": (get_usa_gdp_qoq_data, "quarterly", None),
            "Unemployment Rate": (get_usa_unemployment_rate_data, "monthly", None),
            "Core CPI YoY": (get_usa_core_cpi_yoy_data, "monthly", None),
            "Average Hourly Earnings YoY": (get_usa_average_hourly_earnings_yoy_data, "monthly", None),
            "Core PCE YoY": (get_usa_core_pce_yoy_data, "monthly", None),
            "Core PPI YoY": (get_usa_core_ppi_yoy_data, "monthly", None),
            "Housing Starts MoM": (get_usa_housing_starts_mom_data, "monthly", None),
            "ISM Manufacturing PMI": (get_usa_ism_manufacturing_pmi_data, "monthly", None),
            "ISM Services PMI": (get_usa_ism_services_pmi_data, "monthly", None),
            "Jolts Job Openings": (get_usa_jolts_job_openings_data, "monthly", None),
            "Michigan Consumer Sentiment": (get_usa_michigan_consumer_sentiment_data, "monthly", None),
            "Non Farm Payrolls": (get_usa_nfp_data, "monthly", None),
            "PCE YoY": (get_usa_pce_yoy_data, "monthly", None),
            "PPI YoY": (get_usa_ppi_yoy_data, "monthly", None),
            "Retail Sales MoM": (get_usa_retail_sales_mom_data, "monthly", None),
            "Trade Balance": (get_usa_trade_balance_data, "monthly", None),
        }

        # Load data dynamically
        func, date_format, tickformat_override = indicator_map[indicator]
        df = func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Monetary Policy
            "Interest Rate": (
                "The Federal Funds Rate is the benchmark interest rate set by the Federal Reserve. "
                "It directly influences short-term borrowing costs for banks, which affects mortgages, loans, and business investment. "
                "Changes in the Fed’s rate are closely watched by global markets as signals of monetary tightening or easing."
            ),

            # Inflation
            "CPI YoY": (
                "The Consumer Price Index (CPI YoY) tracks the annual percentage change in the cost of a basket of goods and services. "
                "It is a key measure of inflation and influences interest rate decisions, wages, and investment strategies."
            ),
            "Core CPI YoY": (
                "Core CPI excludes volatile food and energy prices, providing a clearer view of underlying inflation trends. "
                "Policymakers use it to assess persistent price pressures in the economy."
            ),
            "PCE YoY": (
                "The Personal Consumption Expenditures Price Index (PCE YoY) measures the annual change in consumer prices based on actual spending patterns. "
                "It is the Fed’s preferred inflation gauge, reflecting household consumption costs more accurately than CPI."
            ),
            "Core PCE YoY": (
                "Core PCE excludes food and energy prices to highlight underlying inflation trends. "
                "It is closely monitored by the Fed when making monetary policy decisions."
            ),
            "PPI YoY": (
                "The Producer Price Index (PPI YoY) measures annual changes in prices received by producers of goods and services. "
                "Rising producer prices can indicate future increases in consumer prices."
            ),
            "Core PPI YoY": (
                "Core PPI excludes food and energy prices to focus on underlying producer price trends. "
                "It helps identify inflationary pressures before they reach consumers."
            ),

            # Growth
            "GDP Growth Rate": (
                "The GDP Growth Rate measures the pace at which the U.S. economy is expanding or contracting. "
                "It reflects trends in production, investment, government spending, and trade."
            ),
            "Retail Sales MoM": (
                "Retail Sales MoM tracks monthly changes in consumer spending. "
                "It is a key driver of economic growth, as consumer spending accounts for roughly two-thirds of U.S. GDP."
            ),
            "Housing Starts MoM": (
                "Housing Starts measure the number of new residential construction projects that have begun during the month, reported as a seasonally adjusted annual rate (SAAR) in millions. "
                "It includes single-family homes and multi-unit buildings, providing insight into housing demand, construction employment, and overall economic momentum."
            ),
            "Trade Balance": (
                "The U.S. Trade Balance shows the difference between exports and imports of goods and services. "
                "A deficit occurs when imports exceed exports, and a surplus when exports exceed imports, reflecting global demand and competitiveness."
            ),

            # Labor Market
            "Unemployment Rate": (
                "The unemployment rate measures the percentage of the labor force that is actively seeking work but is jobless. "
                "It is a primary indicator of labor market health, influencing consumer spending and economic policy."
            ),
            "Average Hourly Earnings YoY": (
                "Average Hourly Earnings YoY tracks annual growth in workers’ wages. "
                "Rising wages support consumer spending but may contribute to inflation if growth exceeds productivity."
            ),
            "Jolts Job Openings": (
                "The JOLTS Job Openings report measures the number of unfilled positions across the economy. "
                "High job openings relative to unemployed workers signal a tight labor market and potential upward pressure on wages."
            ),
            "Non Farm Payrolls": (
                "Non-Farm Payrolls measure the monthly change in employment across most sectors, excluding farming. "
                "It is closely watched as a timely indicator of labor market strength and economic activity."
            ),

            # Surveys
            "ISM Manufacturing PMI": (
                "The ISM Manufacturing PMI surveys purchasing managers in the manufacturing sector. "
                "A reading above 50 signals expansion, while below 50 signals contraction, offering insight into economic trends."
            ),
            "ISM Services PMI": (
                "The ISM Services PMI tracks activity in the services sector, the largest component of the U.S. economy. "
                "Values above 50 indicate growth, and below 50 indicate contraction."
            ),
            "Michigan Consumer Sentiment": (
                "The Michigan Consumer Sentiment Index measures household confidence in the economy, financial conditions, and expectations. "
                "Shifts in sentiment can foreshadow changes in consumer spending and economic activity."
            )
        }

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
        
        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)

        if n_obs == 0:
            raise ValueError("df_filtered is empty")

        values = df_filtered['value']
        mean_val = values.mean()
        latest_val = values.iloc[-1]
        start_val = values.iloc[0]
        min_val = values.min()
        max_val = values.max()

        # Absolute and percentage change
        change_since_start = latest_val - start_val
        pct_change_since_start = ((latest_val - start_val) / start_val * 100) if start_val != 0 else np.nan

        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (First-to-last, intuitive)
        if change_since_start > 0:
            trend = "🔺 Upward"
        elif change_since_start < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Optional: regression slope trend (for additional insight)
        if n_obs > 1:
            slope, _, _, _, _ = linregress(range(n_obs), values)
            if slope > 0:
                trend_reg = "🔺 Upward"
            elif slope < 0:
                trend_reg = "🔻 Downward"
            else:
                trend_reg = "⏸ Flat"
        else:
            slope = 0
            trend_reg = trend

        # Volatility: standard deviation as % of mean
        volatility = (values.std() / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)

                         
        # -------- Dynamic Titles --------
        titles = {
            # Monetary Policy
            "Interest Rate": "Federal Funds Rate (%)",

            # Inflation
            "CPI YoY": "Consumer Price Index (CPI YoY, %)",
            "Core CPI YoY": "Core Consumer Price Index (YoY, %)",
            "PCE YoY": "Personal Consumption Expenditures (PCE YoY, %)",
            "Core PCE YoY": "Core Personal Consumption Expenditures (YoY, %)",
            "PPI YoY": "Producer Price Index (PPI YoY, %)",
            "Core PPI YoY": "Core Producer Price Index (YoY, %)",

            # Growth
            "GDP Growth Rate": "GDP Growth Rate (%)",
            "Retail Sales MoM": "Retail Sales (MoM, %)",
            "Housing Starts MoM": "Housing Starts (Millions)",
            "Trade Balance": "Trade Balance (Billions USD)",

            # Labor Market
            "Unemployment Rate": "Unemployment Rate (%)",
            "Average Hourly Earnings YoY": "Average Hourly Earnings (YoY, %)",
            "Jolts Job Openings": "Job Openings (JOLTS, Millions)",
            "Non Farm Payrolls": "Non-Farm Payrolls (Change, Thousands)",

            # Surveys
            "ISM Manufacturing PMI": "ISM Manufacturing PMI (Index)",
            "ISM Services PMI": "ISM Services PMI (Index)",
            "Michigan Consumer Sentiment": "Michigan Consumer Sentiment (Index)"
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        # Convert "Off" to None for plot_chart
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()

        # If delta_type is Off, disable hover delta
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style=hover_style,   # conditional hover
            delta_type=delta_type_arg,  # None if Off
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )



        # For quarterly, show only Q4 labels
        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)
            
        fig.update_layout(
            hoverlabel=dict(
                font_size=13,       # optional
                font_color="black", # change text color to black
                font_family="Arial" # optional
            )
        )
        
        # -------- Fix Crowded X-Axis for Fed Funds Rate --------
        if indicator == "Interest Rate":
            max_ticks = 8  # show ~8 evenly spaced date labels
            if len(df_filtered) > max_ticks:
                step = max(1, len(df_filtered) // max_ticks)
                tickvals = df_filtered['date'].iloc[::step]
                ticktext = [d.strftime('%b %Y') for d in tickvals]
                fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)


        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )
        
        # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=indicator
        )
        
        # ==============================
        # 🧠 USA Economy Macro Summary (LLM-enhanced)
        # ==============================

        import openai
        from openai import OpenAI

        # Set API key
        openai.api_key = st.secrets["openai"]["api_key"]
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        
        st.markdown("### USA Economy Summary (Based on the last 12 Months)")

        @st.cache_data(ttl=1800)
        def analyze_usa():
            """Compute latest value, slope, and relative position for all usa indicators."""
            usa_tickers = {
                "Interest Rate": get_usa_interest_rate_data,
                "CPI YoY":get_usa_cpi_yoy_data,
                "GDP Growth Rate": get_usa_gdp_qoq_data,
                "Unemployment Rate": get_usa_unemployment_rate_data,
                "Core CPI YoY": get_usa_core_cpi_yoy_data,
                "Average Hourly Earnings YoY": get_usa_average_hourly_earnings_yoy_data,
                "Core PCE YoY": get_usa_core_pce_yoy_data,
                "Core PPI YoY": get_usa_core_ppi_yoy_data,
                "Housing Starts MoM": get_usa_housing_starts_mom_data,
                "ISM Manufacturing PMI": get_usa_ism_manufacturing_pmi_data,
                "ISM Services PMI": get_usa_ism_services_pmi_data,
                "Jolts Job Openings": get_usa_jolts_job_openings_data,
                "Michigan Consumer Sentiment": get_usa_michigan_consumer_sentiment_data,
                "Non Farm Payrolls": get_usa_nfp_data,
                "PCE YoY": get_usa_pce_yoy_data,
                "PPI YoY": get_usa_ppi_yoy_data,
                "Retail Sales MoM": get_usa_retail_sales_mom_data,
                "Trade Balance": get_usa_trade_balance_data
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
                    st.warning(f"⚠️ Could not process {name}: {e}")
            return results

        def generate_usa_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}%, trend={data['trend']}"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of the US economy summary**.
            You are given the latest 1-year snapshot for the US economy of various economic indicators.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of the US economy** based on these numbers.

            Guidelines:
            - Focus on patterns, contrasts, and relative positioning across indicators.
            - Mention current trends where relevant.
            - Make sure to use the right units for each indicator, for example jolts job openings is in millions etc.
            - Do NOT add information not in the data.
            - Use a neutral, analytical tone (no adjectives like “strong” or “weak”), but clear and concise English.
            - Output only one paragraph.
            - Keep the paragraph natural and varied, like a professional commentary.
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-5-mini" if available
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=250,
                    temperature=0
                )
                summary_text = response.choices[0].message.content.strip()
                if not summary_text:
                    summary_text = "⚠️ LLM returned an empty response."
            except Exception as e:
                summary_text = f"⚠️ LLM generation failed: {e}"

            return summary_text

        @st.cache_data
        def generate_usa_llm_summary_cached(results: dict):
            return generate_usa_llm_summary(results)

        # ---- Run analysis ----
        if "usa_macro_summary" not in st.session_state:
            with st.spinner("Generating usa market summary..."):
                results = analyze_usa()
                st.session_state.usa_macro_summary = generate_usa_llm_summary_cached(results)

        # Use cached summary
        usa_macro_summary = st.session_state.usa_macro_summary

        # Add USA summary to global collector
        summary_label = f"🇺🇸 USA Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{usa_macro_summary}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)

        # ---- Display Narrative Card ----
        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #4a4e69;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
        ">
        {usa_macro_summary}
        </div>
        """, unsafe_allow_html=True)
        
        
        
# -------- Japan Tab --------
if page == "Japan":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Labor Market": ["Unemployment Rate"],
            "Growth": ["GDP Growth Rate"],
            "Inflation": ["CPI YoY"],
            "Monetary Policy": ["Interest Rate"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        indicator_map = {
            "Interest Rate": (get_japan_interest_rate_data, "daily", "%b %Y"),
            "CPI YoY": (get_japan_cpi_yoy_data, "monthly", None),
            "GDP Growth Rate": (get_japan_gdp_qoq_data, "quarterly", None),
            "Unemployment Rate": (get_japan_unemployment_rate_data, "monthly", None)
        }

        # Load data dynamically
        func, date_format, tickformat_override = indicator_map[indicator]
        df = func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Monetary Policy
            "Interest Rate": (
                "The Bank of Japan (BoJ) policy rate is the benchmark interest rate set by the BoJ. "
                "It directly influences short-term borrowing costs for banks, which affects mortgages, loans, and business investment. "
                "Changes in the BoJ’s rate are closely watched by global markets as signals of monetary tightening or easing."
            ),

            # Inflation
            "CPI YoY": (
                "The Consumer Price Index (CPI YoY) tracks the annual percentage change in the cost of a basket of goods and services in Japan. "
                "It is a key measure of inflation and influences BoJ interest rate decisions, wages, and investment strategies."
            ),

            # Growth
            "GDP Growth Rate": (
                "The GDP Growth Rate measures the pace at which the Japanese economy is expanding or contracting. "
                "It reflects trends in production, investment, government spending, and trade."
            ),

            # Labor Market
            "Unemployment Rate": (
                "The unemployment rate measures the percentage of the labor force that is actively seeking work but is jobless. "
                "It is a primary indicator of labor market health, influencing consumer spending and economic policy."
            )
        }


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

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)

        if n_obs == 0:
            raise ValueError("df_filtered is empty")

        values = df_filtered['value']
        mean_val = values.mean()
        latest_val = values.iloc[-1]
        start_val = values.iloc[0]
        min_val = values.min()
        max_val = values.max()

        # Absolute and percentage change
        change_since_start = latest_val - start_val
        pct_change_since_start = ((latest_val - start_val) / start_val * 100) if start_val != 0 else np.nan

        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (First-to-last, intuitive)
        if change_since_start > 0:
            trend = "🔺 Upward"
        elif change_since_start < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Optional: regression slope trend (for additional insight)
        if n_obs > 1:
            slope, _, _, _, _ = linregress(range(n_obs), values)
            if slope > 0:
                trend_reg = "🔺 Upward"
            elif slope < 0:
                trend_reg = "🔻 Downward"
            else:
                trend_reg = "⏸ Flat"
        else:
            slope = 0
            trend_reg = trend

        # Volatility: standard deviation as % of mean
        volatility = (values.std() / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)


        # -------- Dynamic Titles --------
        titles = {
            "Interest Rate": "Bank of Japan Policy Rate (%)",
            "CPI YoY": "Consumer Price Index (YoY, %)",
            "GDP Growth Rate": "GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)"
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

                # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=indicator
        )

        # ==============================
        # 🧠 Japanese Economy Macro Summary (LLM-enhanced)
        # ==============================

        import openai
        from openai import OpenAI

        # Set API key
        openai.api_key = st.secrets["openai"]["api_key"]
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        
        st.markdown("### Japanese Economy Summary (Based on the last 12 Months)")

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
                    st.warning(f"⚠️ Could not process {name}: {e}")
            return results

        def generate_japan_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}%, trend={data['trend']}"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of the Japanese economy summary**.
            You are given the latest 1-year snapshot for the Japanese economy of various economic indicators.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of the Japanese economy** based on these numbers.

            Guidelines:
            - Focus on patterns, contrasts, and relative positioning across indicators.
            - Mention current trends where relevant.
            - Make sure to use the right units for each indicator.
            - Do NOT add information not in the data.
            - Use a neutral, analytical tone (no adjectives like “strong” or “weak”), but clear and concise English.
            - Output only one paragraph.
            - Keep the paragraph natural and varied, like a professional commentary.
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-5-mini" if available
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=250,
                    temperature=0
                )
                summary_text = response.choices[0].message.content.strip()
                if not summary_text:
                    summary_text = "⚠️ LLM returned an empty response."
            except Exception as e:
                summary_text = f"⚠️ LLM generation failed: {e}"

            return summary_text

        @st.cache_data
        def generate_japan_llm_summary_cached(results: dict):
            return generate_japan_llm_summary(results)

        # ---- Run analysis ----
        if "japan_macro_summary" not in st.session_state:
            with st.spinner("Generating japan market summary..."):
                results = analyze_japan()
                st.session_state.japan_macro_summary = generate_japan_llm_summary_cached(results)

        # Use cached summary
        japan_macro_summary = st.session_state.japan_macro_summary
        
        # Add Japan summary to global collector
        summary_label = f"Japan Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{japan_macro_summary}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)


        # ---- Display Narrative Card ----
        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #4a4e69;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
        ">
        {japan_macro_summary}
        </div>
        """, unsafe_allow_html=True)
       
# -------- UK Tab --------
if page == "UK":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Labor Market": ["Unemployment Rate"],
            "Growth": ["GDP Growth Rate"],
            "Inflation": ["CPI YoY"],
            "Monetary Policy": ["Interest Rate"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        indicator_map = {
            "Interest Rate": (get_uk_interest_rate_data, "daily", "%b %Y"),
            "CPI YoY": (get_uk_cpi_yoy_data, "monthly", None),
            "GDP Growth Rate": (get_uk_gdp_qoq_data, "quarterly", None),
            "Unemployment Rate": (get_uk_unemployment_rate_data, "monthly", None)
        }

        # Load data dynamically
        func, date_format, tickformat_override = indicator_map[indicator]
        df = func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Monetary Policy
            "Interest Rate": (
                "The Bank of England (BoE) policy rate is the benchmark interest rate set by the BoE. "
                "It directly affects short-term borrowing costs for banks, which in turn influence mortgages, loans, and business investment. "
                "Changes in the BoE rate are closely monitored by global markets as signals of monetary tightening or easing."
            ),

            # Inflation
            "CPI YoY": (
                "The Consumer Price Index (CPI YoY) measures the annual percentage change in the cost of a typical basket of goods and services in the UK. "
                "It is a key gauge of inflation and informs BoE interest rate decisions, wage adjustments, and investment strategies."
            ),

            # Growth
            "GDP Growth Rate": (
                "The GDP Growth Rate captures the pace at which the UK economy is expanding or contracting. "
                "It reflects trends in consumption, investment, government spending, and trade, providing insight into overall economic health."
            ),

            # Labor Market
            "Unemployment Rate": (
                "The unemployment rate measures the percentage of the UK labor force that is actively seeking work but is currently jobless. "
                "It is a primary indicator of labor market conditions and has implications for consumer spending and economic policy."
            )
        }


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

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)

        if n_obs == 0:
            raise ValueError("df_filtered is empty")

        values = df_filtered['value']
        mean_val = values.mean()
        latest_val = values.iloc[-1]
        start_val = values.iloc[0]
        min_val = values.min()
        max_val = values.max()

        # Absolute and percentage change
        change_since_start = latest_val - start_val
        pct_change_since_start = ((latest_val - start_val) / start_val * 100) if start_val != 0 else np.nan

        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (First-to-last, intuitive)
        if change_since_start > 0:
            trend = "🔺 Upward"
        elif change_since_start < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Optional: regression slope trend (for additional insight)
        if n_obs > 1:
            slope, _, _, _, _ = linregress(range(n_obs), values)
            if slope > 0:
                trend_reg = "🔺 Upward"
            elif slope < 0:
                trend_reg = "🔻 Downward"
            else:
                trend_reg = "⏸ Flat"
        else:
            slope = 0
            trend_reg = trend

        # Volatility: standard deviation as % of mean
        volatility = (values.std() / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)


        # -------- Dynamic Titles --------
        titles = {
            "Interest Rate": "Bank of England Policy Rate (%)",
            "CPI YoY": "Consumer Price Index (YoY, %)",
            "GDP Growth Rate": "GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)"
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

                # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=indicator
        )
        
        # ==============================
        # 🧠 UK Economy Macro Summary (LLM-enhanced)
        # ==============================

        import openai
        from openai import OpenAI

        # Set API key
        openai.api_key = st.secrets["openai"]["api_key"]
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        
        st.markdown("### UK Economy Summary (Based on the last 12 Months)")

        @st.cache_data(ttl=1800)
        def analyze_uk():
            """Compute latest value, slope, and relative position for all uk indicators."""
            uk_tickers = {
                "Interest Rate": get_uk_interest_rate_data,
                "CPI YoY": get_uk_cpi_yoy_data,
                "GDP Growth Rate": get_uk_gdp_qoq_data,
                "Unemployment Rate": get_uk_unemployment_rate_data
            }

            results = {}
            for name, func in uk_tickers.items():
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
                    st.warning(f"⚠️ Could not process {name}: {e}")
            return results

        def generate_uk_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}%, trend={data['trend']}"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of the uk economy summary**.
            You are given the latest 1-year snapshot for the uk economy of various economic indicators.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of the uk economy** based on these numbers.

            Guidelines:
            - Focus on patterns, contrasts, and relative positioning across indicators.
            - Mention current trends where relevant.
            - Make sure to use the right units for each indicator.
            - Do NOT add information not in the data.
            - Use a neutral, analytical tone (no adjectives like “strong” or “weak”), but clear and concise English.
            - Output only one paragraph.
            - Keep the paragraph natural and varied, like a professional commentary.
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-5-mini" if available
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=250,
                    temperature=0
                )
                summary_text = response.choices[0].message.content.strip()
                if not summary_text:
                    summary_text = "⚠️ LLM returned an empty response."
            except Exception as e:
                summary_text = f"⚠️ LLM generation failed: {e}"

            return summary_text

        @st.cache_data
        def generate_uk_llm_summary_cached(results: dict):
            return generate_uk_llm_summary(results)

        # ---- Run analysis ----
        if "uk_macro_summary" not in st.session_state:
            with st.spinner("Generating uk market summary..."):
                results = analyze_uk()
                st.session_state.uk_macro_summary = generate_uk_llm_summary_cached(results)

        # Use cached summary
        uk_macro_summary = st.session_state.uk_macro_summary
        
        # Add UK summary to global collector
        summary_label = f"UK Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{uk_macro_summary}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)


        # ---- Display Narrative Card ----
        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #4a4e69;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
        ">
        {uk_macro_summary}
        </div>
        """, unsafe_allow_html=True)

              
# -------- EURO Tab --------
if page == "EURO":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Labor Market": ["Unemployment Rate"],
            "Growth": ["GDP Growth Rate"],
            "Inflation": ["CPI YoY"],
            "Monetary Policy": ["Interest Rate"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        indicator_map = {
            "Interest Rate": (get_euro_interest_rate_data, "daily", "%b %Y"),
            "CPI YoY": (get_euro_cpi_yoy_data, "monthly", None),
            "GDP Growth Rate": (get_euro_gdp_qoq_data, "quarterly", None),
            "Unemployment Rate": (get_euro_unemployment_rate_data, "monthly", None)
        }

        # Load data dynamically
        func, date_format, tickformat_override = indicator_map[indicator]
        df = func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Monetary Policy
            "Interest Rate": (
                "The European Central Bank (ECB) policy rate is the benchmark interest rate set by the ECB. "
                "It directly affects short-term borrowing costs for banks, which influences loans, mortgages, and business investment across the Eurozone. "
                "Changes in the ECB rate are closely watched by global markets as signals of monetary tightening or easing."
            ),

            # Inflation
            "CPI YoY": (
                "The Consumer Price Index (CPI YoY) tracks the annual percentage change in the cost of a representative basket of goods and services in the Euro area. "
                "It is a primary measure of inflation and informs ECB monetary policy, wage negotiations, and investment strategies."
            ),

            # Growth
            "GDP Growth Rate": (
                "The GDP Growth Rate measures how fast the Eurozone economy is expanding or contracting. "
                "It reflects trends in consumption, investment, government spending, and trade among member countries."
            ),

            # Labor Market
            "Unemployment Rate": (
                "The unemployment rate represents the percentage of the labor force in the Eurozone actively seeking work but currently without a job. "
                "It is a key indicator of labor market health, affecting consumer spending, social policies, and economic planning."
            )
        }

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

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)

        if n_obs == 0:
            raise ValueError("df_filtered is empty")

        values = df_filtered['value']
        mean_val = values.mean()
        latest_val = values.iloc[-1]
        start_val = values.iloc[0]
        min_val = values.min()
        max_val = values.max()

        # Absolute and percentage change
        change_since_start = latest_val - start_val
        pct_change_since_start = ((latest_val - start_val) / start_val * 100) if start_val != 0 else np.nan

        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (First-to-last, intuitive)
        if change_since_start > 0:
            trend = "🔺 Upward"
        elif change_since_start < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Optional: regression slope trend (for additional insight)
        if n_obs > 1:
            slope, _, _, _, _ = linregress(range(n_obs), values)
            if slope > 0:
                trend_reg = "🔺 Upward"
            elif slope < 0:
                trend_reg = "🔻 Downward"
            else:
                trend_reg = "⏸ Flat"
        else:
            slope = 0
            trend_reg = trend

        # Volatility: standard deviation as % of mean
        volatility = (values.std() / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)


        # -------- Dynamic Titles --------
        titles = {
            "Interest Rate": "ECB Policy Rate (%)",
            "CPI YoY": "Consumer Price Index (YoY, %)",
            "GDP Growth Rate": "GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)"
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

                # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=indicator
        )
        
        # ==============================
        # 🧠 EURO Economy Macro Summary (LLM-enhanced)
        # ==============================

        import openai
        from openai import OpenAI

        # Set API key
        openai.api_key = st.secrets["openai"]["api_key"]
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        
        st.markdown("### EURO Economy Summary (Based on the last 12 Months)")

        @st.cache_data(ttl=1800)
        def analyze_euro():
            """Compute latest value, slope, and relative position for all euro indicators."""
            euro_tickers = {
                "Interest Rate": get_euro_interest_rate_data,
                "CPI YoY": get_euro_cpi_yoy_data,
                "GDP Growth Rate": get_euro_gdp_qoq_data,
                "Unemployment Rate": get_euro_unemployment_rate_data
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
                    st.warning(f"⚠️ Could not process {name}: {e}")
            return results

        def generate_euro_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}%, trend={data['trend']}"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of the EURO economy summary**.
            You are given the latest 1-year snapshot for the EURO economy of various economic indicators.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of the EURO economy** based on these numbers.

            Guidelines:
            - Focus on patterns, contrasts, and relative positioning across indicators.
            - Mention current trends where relevant.
            - Make sure to use the right units for each indicator.
            - Do NOT add information not in the data.
            - Use a neutral, analytical tone (no adjectives like “strong” or “weak”), but clear and concise English.
            - Output only one paragraph.
            - Keep the paragraph natural and varied, like a professional commentary.
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-5-mini" if available
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=250,
                    temperature=0
                )
                summary_text = response.choices[0].message.content.strip()
                if not summary_text:
                    summary_text = "⚠️ LLM returned an empty response."
            except Exception as e:
                summary_text = f"⚠️ LLM generation failed: {e}"

            return summary_text

        @st.cache_data
        def generate_euro_llm_summary_cached(results: dict):
            return generate_euro_llm_summary(results)

        # ---- Run analysis ----
        if "euro_macro_summary" not in st.session_state:
            with st.spinner("Generating euro market summary..."):
                results = analyze_euro()
                st.session_state.euro_macro_summary = generate_euro_llm_summary_cached(results)

        # Use cached summary
        euro_macro_summary = st.session_state.euro_macro_summary
        
        # Add EURO summary to global collector
        summary_label = f"EURO Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{euro_macro_summary}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)


        # ---- Display Narrative Card ----
        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #4a4e69;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
        ">
        {euro_macro_summary}
        </div>
        """, unsafe_allow_html=True)

                
# -------- FX Rates Tab --------
if page == "FX Rates":

    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups (Major vs Minor FX) --------
        indicator_groups = {
            "Major Pairs": ["EUR/USD", "GBP/USD", "USD/JPY", "DXY"],
            "Cross Pairs": ["EUR/GBP", "EUR/JPY", "GBP/JPY"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Currency Pair", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- FX Mapping --------
        fx_tickers = {
            "EUR/USD": "EURUSD=X",
            "GBP/USD": "GBPUSD=X",
            "USD/JPY": "USDJPY=X",
            "EUR/GBP": "EURGBP=X",
            "EUR/JPY": "EURJPY=X",
            "GBP/JPY": "GBPJPY=X",
            "DXY": "DX-Y.NYB"
        }
        title_map = {
            "EUR/USD": "EUR/USD",
            "GBP/USD": "GBP/USD",
            "USD/JPY": "USD/JPY",
            "EUR/GBP": "EUR/GBP",
            "EUR/JPY": "EUR/JPY",
            "GBP/JPY": "GBP/JPY",
            "DXY": "DXY"
        }

        ticker = fx_tickers[indicator]
        title = title_map[indicator]

        # Load FX data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # Start & End Dates side by side
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Major FX Pairs
            "EUR/USD": (
                "The EUR/USD currency pair reflects the relative economic performance, interest rate expectations, and monetary policy outlooks of the Eurozone versus the U.S. "
                "Movements are influenced by ECB and Federal Reserve decisions, economic data releases, and global risk sentiment."
            ),

            "GBP/USD": (
                "The GBP/USD pair is influenced by UK economic indicators, Bank of England policy decisions, and U.S. economic conditions. "
                "It often reacts to interest rate differentials, inflation data, and political developments in both regions."
            ),

            "USD/JPY": (
                "The USD/JPY pair is sensitive to U.S. Treasury yields, Bank of Japan policy, and global risk sentiment. "
                "It is often used as a proxy for risk appetite, with the yen typically strengthening in periods of market uncertainty."
            ),

            "EUR/GBP": (
                "The EUR/GBP reflects diverging economic conditions and monetary policy outlooks between the Eurozone and the UK. "
                "It is influenced by interest rate expectations, trade developments, and relative growth trends."
            ),

            "EUR/JPY": (
                "The EUR/JPY pair is driven by differences in ECB and BoJ monetary policy, as well as global risk appetite. "
                "It tends to rise when the euro strengthens or global risk sentiment improves, and fall during market uncertainty."
            ),

            "GBP/JPY": (
                "The GBP/JPY is highly sensitive to global risk sentiment and monetary policy differences between the UK and Japan. "
                "It is often used as a barometer for risk-on or risk-off market conditions."
            ),

            "DXY": (
                "The DXY (U.S. Dollar Index) measures the overall strength of the USD against a basket of major currencies. "
                "It reacts to U.S. interest rate expectations, economic data, geopolitical developments, and global risk sentiment."
            )
        }


        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -10px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Arial Bold';
                font-weight:normal;
                color:#333';
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)
        mean_val = df_filtered['value'].mean()
        latest_val = df_filtered['value'].iloc[-1]
        min_val = df_filtered['value'].min()
        max_val = df_filtered['value'].max()
        start_val = df_filtered['value'].iloc[0]
        change_since_start = latest_val - start_val

        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (using regression slope)
        slope, _, _, _, _ = linregress(range(n_obs), df_filtered['value'])
        if slope > 0:
            trend = "🔺 Upward"
        elif slope < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Volatility (range as % of mean)
        volatility = ((max_val - min_val) / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)

        # Detect quarterly data
        quarterly = False
        if df_filtered.shape[0] > 1:
            avg_days = (df_filtered['date'].diff().dropna().dt.days.mean())
            if avg_days >= 80:
                quarterly = True

        # Plot chart
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            title,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else "daily",
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered[df_filtered['date'].dt.quarter == 4]['date']
            ticktext = df_filtered[df_filtered['date'].dt.quarter == 4].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

                # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=indicator
        )
        
        # ==============================
        # 🧠 FX Market Macro Summary (LLM-enhanced)
        # ==============================

        import streamlit as st
        import pandas as pd
        import numpy as np
        import datetime as dt
        from scipy.stats import linregress
        import openai  # pip install openai

        # ✅ Set your OpenAI API key in Streamlit secrets or environment variable
        # e.g., in .streamlit/secrets.toml -> [openai] api_key="sk-XXXX"
        openai.api_key = st.secrets["openai"]["api_key"]

        # ---- Streamlit Section Header ----
        st.markdown("### FX Market Summary (Based on the last 3 Years)")

        @st.cache_data(ttl=3600)
        def get_fx_data(ticker: str):
            """Wrapper for your existing get_fx_data_yahoo function."""
            # Replace this with your actual data loader
            df = get_fx_data_yahoo(ticker, start_date=dt.date(2018, 1, 1), end_date=dt.date.today())
            return df.dropna()

        @st.cache_data(ttl=1800)
        def analyze_fx():
            """Compute normalized position and slope-based trend for major tickers."""
            fx_tickers = {
                "EUR/USD": "EURUSD=X",
                "GBP/USD": "GBPUSD=X",
                "USD/JPY": "USDJPY=X",
                "EUR/GBP": "EURGBP=X",
                "EUR/JPY": "EURJPY=X",
                "GBP/JPY": "GBPJPY=X",
                "DXY": "DX-Y.NYB"
            }

            results = {}
            for name, ticker in fx_tickers.items():
                try:
                    df = get_fx_data(ticker)
                    if len(df) < 12:
                        continue
                    df_3y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=3))]
                    latest = df_3y["value"].iloc[-1]
                    min_val, max_val = df_3y["value"].min(), df_3y["value"].max()
                    slope, _, _, _, _ = linregress(range(len(df_3y)), df_3y["value"])
                    pos = (latest - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50
                    trend = "up" if slope > 0 else "down" if slope < 0 else "flat"
                    results[name] = {"latest": latest, "pos": pos, "trend": trend}
                except Exception as e:
                    st.warning(f"⚠️ Could not process {name}: {e}")
            return results
        
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        def generate_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}, trend={data['trend']}, position={data['pos']:.1f}%"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of fx summary**.
            You are given the latest 3-year data snapshot for several major fx.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of fx** based on these numbers.

            Guidelines:
            - Focus on patterns and contrasts across the fx — e.g., which are leading, lagging, or showing extreme positions.
            - Do NOT add information not in the data.
            - Use a neutral, analytical tone (no adjectives like “impressive” or “strong”), but use clear concise english.
            - Output only one paragraph.
            - Keep it natural and varied in structure — not repetitive, like a normal person is saying it.
            - Mention the key data points selectively to illustrate your points.
            """


            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-5-mini" if available
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=250,
                    temperature=0
                )

                summary_text = response.choices[0].message.content.strip()
                if not summary_text:
                    summary_text = "⚠️ LLM returned an empty response."

            except Exception as e:
                summary_text = f"⚠️ LLM generation failed: {e}"

            return summary_text

        # ---- Cached LLM Summary Function ----
        @st.cache_data
        def generate_llm_summary_cached(results: dict):
            return generate_llm_summary(results)


        # ---- Run analysis ----
        if "fx_macro_summary" not in st.session_state:
            with st.spinner("Generating summary..."):
                results = analyze_fx()
                # ✅ use the cached version here
                st.session_state.fx_macro_summary = generate_llm_summary_cached(results)

        # Use cached summary
        fx_macro_summary = st.session_state.fx_macro_summary
        
        # Add FX summary to global collector
        summary_label = f"FX Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{fx_macro_summary}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)


        # ---- Display Narrative Card ----
        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #4a4e69;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
        ">
        {fx_macro_summary}
        </div>
        """, unsafe_allow_html=True)
        
        
        
        
# ==============================
# 📊 COMPARE TAB (Enhanced Hover + Delta Type + Bold Axis + Black Lines)
# ==============================
if page == "Compare":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # --------------------------
        # Indicator selection
        # --------------------------
        indicator_groups = {
            "USA": {
                "Interest Rate": "usa_rate",
                "CPI YoY %": "usa_cpi",
                "Core CPI YoY": "usa_core_cpi",
                "GDP QoQ %": "usa_gdp",
                "Unemployment Rate": "usa_unemp",
                "Average Hourly Earnings YoY": "usa_ahe",
                "Core PCE YoY": "usa_core_pce",
                "Core PPI YoY": "usa_core_ppi",
                "Housing Starts MoM": "usa_housing",
                "ISM Manufacturing PMI": "usa_ism_manu",
                "ISM Services PMI": "usa_ism_serv",
                "JOLTS Job Openings": "usa_jolts",
                "Michigan Consumer Sentiment": "usa_michigan",
                "Non Farm Payrolls": "usa_nfp",
                "PCE YoY": "usa_pce",
                "PPI YoY": "usa_ppi",
                "Retail Sales MoM": "usa_retail",
                "Trade Balance": "usa_trade"
            },
            "UK": {
                "Interest Rate": "uk_rate",
                "CPI YoY %": "uk_cpi",
                "GDP QoQ %": "uk_gdp",
                "Unemployment Rate": "uk_unemp"
                
            },
            "Japan": {
                "Interest Rate": "jp_rate",
                "CPI YoY %": "jp_cpi",
                "GDP QoQ %": "jp_gdp",
                "Unemployment Rate": "jp_unemp"
                
            },
            "Euro": {
                "Interest Rate": "eu_rate",
                "CPI YoY %": "eu_cpi",
                "GDP QoQ %": "eu_gdp",
                "Unemployment Rate": "eu_unemp"
                
            },

            "FX": {"EUR/USD": "eurusd", "GBP/USD": "gbpusd", "USD/JPY": "usdjpy", "DXY": "dxy"},
            
            "Equities": {
                "S&P 500": "eq_sp500",
                "NASDAQ": "eq_nasdaq",
                "Dow Jones": "eq_dow",
                "FTSE 100": "eq_ftse",
                "Nikkei 225": "eq_nikkei",
                "DAX": "eq_dax",
                "MSCI Emerging Markets ETF": "eq_msci_em",
                "VIX": "eq_vix"
            },
            "Stocks": {
                "Apple": "st_aapl",
                "Amazon": "st_amzn",
                "Meta": "st_meta",
                "Alphabet (Google)": "st_googl",
                "Nvidia": "st_nvda",
                "Microsoft": "st_msft",
                "Tesla": "st_tsla"
            },
            "Commodities": {
                "Gold": "cmd_gold",
                "Silver": "cmd_silver",
                "Crude Oil (WTI)": "cmd_wti",
                "Brent Oil": "cmd_brent",
                "Natural Gas": "cmd_ng",
                "Wheat": "cmd_wheat",
                "Copper": "cmd_copper",
                "Corn": "cmd_corn",
                "Soybeans": "cmd_soy"
            },
            "Bonds": {
                # U.S. Treasuries
                "US 1M Yield": "usa_1m",
                "US 3M Yield": "usa_3m",
                "US 6M Yield": "usa_6m",
                "US 1Y Yield": "usa_1y",
                "US 2Y Yield": "usa_2y",
                "US 3Y Yield": "usa_3y",
                "US 5Y Yield": "usa_5y",
                "US 7Y Yield": "usa_7y",
                "US 10Y Yield": "usa_10y",
                "US 20Y Yield": "usa_20y",
                "US 30Y Yield": "usa_30y",

                # UK Gilts
                "UK 2Y Gilt Yield": "uk_2y",
                "UK 10Y Gilt Yield": "uk_10y",

                # Japan JGBs
                "Japan 2Y JGB Yield": "jp_2y",
                "Japan 10Y JGB Yield": "jp_10y",

                # Euro Area Bonds
                "Euro 2Y Bond Yield": "eu_2y",
                "Euro 10Y Bond Yield": "eu_10y"
            },
            "Crypto": {
                "Bitcoin": "crypto_btc",
                "Ethereum": "crypto_eth"
            }
        }

        # --------------------------
        # Group selection side by side
        # --------------------------
        group_col1, group_col2 = st.columns(2)

        with group_col1:
            group1 = st.selectbox("Indicator 1 Group", list(indicator_groups.keys()), key="group1")
            indicator1_label = st.selectbox("Indicator 1", list(indicator_groups[group1].keys()), key="indicator1")
            indicator1_code = indicator_groups[group1][indicator1_label]

        with group_col2:
            group2 = st.selectbox("Indicator 2 Group", list(indicator_groups.keys()), key="group2")
            indicator2_options = list(indicator_groups[group2].keys())
            if group1 == group2:
                indicator2_options = [opt for opt in indicator2_options if opt != indicator1_label]
            indicator2_label = st.selectbox("Indicator 2", indicator2_options, key="indicator2")
            indicator2_code = indicator_groups[group2][indicator2_label]


        # --------------------------
        # Delta Type + Timeframe side by side
        # --------------------------
        dt_col, tf_col = st.columns(2)
        with dt_col:
            delta_type_option = st.selectbox(
                "Delta Type",
                ["Off", "Daily % Change", "Cumulative % Change"],
                index=0
            )
        with tf_col:
            timeframe = st.selectbox(
                "Time Frame",
                ["1Y", "3Y", "5Y", "10Y", "Max"],
                index=2
            )

        # --------------------------
        # Load & clean data
        # --------------------------
        def load_indicator_data(code):
            # USA
            if code == "usa_rate": return get_usa_interest_rate_data()
            if code == "usa_cpi": return get_usa_cpi_yoy_data()
            if code == "usa_core_cpi": return get_usa_core_cpi_yoy_data()
            if code == "usa_gdp": return get_usa_gdp_qoq_data()
            if code == "usa_unemp": return get_usa_unemployment_rate_data()
            if code == "usa_ahe": return get_usa_average_hourly_earnings_yoy_data()
            if code == "usa_core_pce": return get_usa_core_pce_yoy_data()
            if code == "usa_core_ppi": return get_usa_core_ppi_yoy_data()
            if code == "usa_housing": return get_usa_housing_starts_mom_data()
            if code == "usa_ism_manu": return get_usa_ism_manufacturing_pmi_data()
            if code == "usa_ism_serv": return get_usa_ism_services_pmi_data()
            if code == "usa_jolts": return get_usa_jolts_job_openings_data()
            if code == "usa_michigan": return get_usa_michigan_consumer_sentiment_data()
            if code == "usa_nfp": return get_usa_nfp_data()
            if code == "usa_pce": return get_usa_pce_yoy_data()
            if code == "usa_ppi": return get_usa_ppi_yoy_data()
            if code == "usa_retail": return get_usa_retail_sales_mom_data()
            if code == "usa_trade": return get_usa_trade_balance_data()

            # Yields
            if code == "usa_1m": return get_usa_1mo_yield_data()
            if code == "usa_3m": return get_usa_3mo_yield_data()
            if code == "usa_6m": return get_usa_6mo_yield_data()
            if code == "usa_1y": return get_usa_1yr_yield_data()
            if code == "usa_2y": return get_usa_2yr_yield_data()
            if code == "usa_3y": return get_usa_3yr_yield_data()
            if code == "usa_5y": return get_usa_5yr_yield_data()
            if code == "usa_7y": return get_usa_7yr_yield_data()
            if code == "usa_10y": return get_usa_10yr_yield_data()
            if code == "usa_20y": return get_usa_20yr_yield_data()
            if code == "usa_30y": return get_usa_30yr_yield_data()


            # UK
            if code == "uk_rate": return get_uk_interest_rate_data()
            if code == "uk_cpi": return get_uk_cpi_yoy_data()
            if code == "uk_gdp": return get_uk_gdp_qoq_data()
            if code == "uk_unemp": return get_uk_unemployment_rate_data()
            if code == "uk_10y": return get_uk_10yr_yield_data()
            if code == "uk_2y": return get_uk_2yr_yield_data()

            # Japan
            if code == "jp_rate": return get_japan_interest_rate_data()
            if code == "jp_cpi": return get_japan_cpi_yoy_data()
            if code == "jp_gdp": return get_japan_gdp_qoq_data()
            if code == "jp_unemp": return get_japan_unemployment_rate_data()
            if code == "jp_10y": return get_japan_10yr_yield_data()
            if code == "jp_2y": return get_japan_2yr_yield_data()

            # Euro
            if code == "eu_rate": return get_euro_interest_rate_data()
            if code == "eu_cpi": return get_euro_cpi_yoy_data()
            if code == "eu_gdp": return get_euro_gdp_qoq_data()
            if code == "eu_unemp": return get_euro_unemployment_rate_data()
            if code == "eu_10y": return get_euro_10yr_yield_data()
            if code == "eu_2y": return get_euro_2yr_yield_data()

            # FX
            if code == "eurusd": return get_fx_data_yahoo("EURUSD=X", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "gbpusd": return get_fx_data_yahoo("GBPUSD=X", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "usdjpy": return get_fx_data_yahoo("USDJPY=X", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "dxy": return get_fx_data_yahoo("DX-Y.NYB", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            
            # Equities
            if code == "eq_sp500": return get_fx_data_yahoo("^GSPC", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_nasdaq": return get_fx_data_yahoo("^IXIC", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_dow": return get_fx_data_yahoo("^DJI", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_ftse": return get_fx_data_yahoo("^FTSE", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_nikkei": return get_fx_data_yahoo("^N225", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_dax": return get_fx_data_yahoo("^GDAXI", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_msci_em": return get_fx_data_yahoo("EEM", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "eq_vix": return get_fx_data_yahoo("^VIX", start_date=dt.date(1980,1,1), end_date=dt.date.today())

            # Stocks
            if code == "st_aapl": return get_fx_data_yahoo("AAPL", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_amzn": return get_fx_data_yahoo("AMZN", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_meta": return get_fx_data_yahoo("META", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_googl": return get_fx_data_yahoo("GOOGL", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_nvda": return get_fx_data_yahoo("NVDA", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_msft": return get_fx_data_yahoo("MSFT", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "st_tsla": return get_fx_data_yahoo("TSLA", start_date=dt.date(1980,1,1), end_date=dt.date.today())

            # Commodities
            if code == "cmd_gold": return get_fx_data_yahoo("GC=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_silver": return get_fx_data_yahoo("SI=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_wti": return get_fx_data_yahoo("CL=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_brent": return get_fx_data_yahoo("BZ=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_ng": return get_fx_data_yahoo("NG=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_wheat": return get_fx_data_yahoo("ZW=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_copper": return get_fx_data_yahoo("HG=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_corn": return get_fx_data_yahoo("ZC=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "cmd_soy": return get_fx_data_yahoo("ZS=F", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            
            # Crypto
            if code == "crypto_btc": return get_fx_data_yahoo("BTC-USD", start_date=dt.date(1980,1,1), end_date=dt.date.today())
            if code == "crypto_eth": return get_fx_data_yahoo("ETH-USD", start_date=dt.date(1980,1,1), end_date=dt.date.today())


            return pd.DataFrame()

        df1 = load_indicator_data(indicator1_code).dropna()
        df2 = load_indicator_data(indicator2_code).dropna()
        df1 = df1.rename(columns={df1.columns[0]: "date", df1.columns[1]: "value"})
        df2 = df2.rename(columns={df2.columns[0]: "date", df2.columns[1]: "value"})
        df1['date'] = pd.to_datetime(df1['date'], errors='coerce')
        df2['date'] = pd.to_datetime(df2['date'], errors='coerce')
        df1 = df1.dropna(subset=['date'])
        df2 = df2.dropna(subset=['date'])

        # --------------------------
        # Timeframe & Start/End Dates side by side
        # --------------------------
        df1_min, df1_max = df1['date'].min().date(), df1['date'].max().date()
        df2_min, df2_max = df2['date'].min().date(), df2['date'].max().date()
        latest_date = max(df1_max, df2_max)
        earliest_start = min(df1_min, df2_min)

        if timeframe == "1Y": default_start_date = latest_date - dt.timedelta(days=365)
        elif timeframe == "3Y": default_start_date = latest_date - dt.timedelta(days=365*3)
        elif timeframe == "5Y": default_start_date = latest_date - dt.timedelta(days=365*5)
        elif timeframe == "10Y": default_start_date = latest_date - dt.timedelta(days=365*10)
        else: default_start_date = earliest_start
        default_start_date = max(earliest_start, default_start_date)

        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_start, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_start, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)


    with col2:
        # --------------------------
        # Filter by date
        # --------------------------
        df1_filtered = df1[(df1['date'] >= pd.to_datetime(start_date)) & (df1['date'] <= pd.to_datetime(end_date))]
        df2_filtered = df2[(df2['date'] >= pd.to_datetime(start_date)) & (df2['date'] <= pd.to_datetime(end_date))]
        if df1_filtered.empty or df2_filtered.empty:
            st.warning("Not enough data for this date range.")
            st.stop()
        # ---- Align zero baselines when both data sets cross 0 ----
        if not df1_filtered.empty and not df2_filtered.empty:
            y1_min, y1_max = df1_filtered["value"].min(), df1_filtered["value"].max()
            y2_min, y2_max = df2_filtered["value"].min(), df2_filtered["value"].max()

            # Only apply common-zero alignment if both series cross or center around 0
            crosses_zero = (y1_min < 0 < y1_max) and (y2_min < 0 < y2_max)
            if crosses_zero:
                # Expand both ranges so that 0 is at the same relative position
                max_abs = max(abs(y1_min), abs(y1_max), abs(y2_min), abs(y2_max))
                y1_range = [-max_abs, max_abs]
                y2_range = [-max_abs, max_abs]
            else:
                y1_range, y2_range = None, None
        else:
            y1_range, y2_range = None, None


        latest_val_1 = df1_filtered.iloc[-1]['value']
        latest_val_2 = df2_filtered.iloc[-1]['value']
        def format_val(v): return f"{v:.4f}" if isinstance(v, float) else str(v)
        title_str = (f"{group1}: {indicator1_label} (Latest: {format_val(latest_val_1)}) "
                     f"vs {group2}: {indicator2_label} (Latest: {format_val(latest_val_2)})")

        # --------------------------
        # Detect quarterly/monthly/daily
        # --------------------------
        def is_quarterly(df):
            if df.shape[0] > 1:
                avg_days = df['date'].diff().dropna().dt.days.mean()
                return avg_days >= 80
            return False
        quarterly = is_quarterly(df1_filtered) or is_quarterly(df2_filtered)

        def is_monthly(df):
            if df.shape[0] > 1:
                avg_days = df['date'].diff().dropna().dt.days.mean()
                return 27 <= avg_days <= 32
            return False
        monthly = is_monthly(df1_filtered) or is_monthly(df2_filtered)

        # --------------------------
        # Detect if indicators are same type
        # --------------------------
        def same_type(ind1, ind2): return ind1.split()[1:] == ind2.split()[1:]
        same_group = group1 == group2
        unify_axis = False


        # --------------------------
        # Calculate delta safely
        # --------------------------

        if delta_type_option == "Daily % Change":
            for df_ in [df1_filtered, df2_filtered]:
                df_['delta'] = df_['value'].pct_change() * 100
                df_['delta_str'] = df_['delta'].apply(lambda x: f"▲ {x:.2f}%" if x > 0 else (f"▼ {abs(x):.2f}%" if pd.notnull(x) and x < 0 else "— 0.00%"))
                df_['delta_color'] = df_['delta'].apply(lambda x: "green" if x > 0 else ("red" if x < 0 else "gray"))
        elif delta_type_option == "Cumulative % Change":
            for df_ in [df1_filtered, df2_filtered]:
                df_['delta'] = np.where(df_['value'].iloc[0] == 0, 0, (df_['value'] / df_['value'].iloc[0] - 1) * 100)
                df_['delta_str'] = df_['delta'].apply(lambda x: f"▲ {x:.2f}%" if x > 0 else (f"▼ {abs(x):.2f}%" if pd.notnull(x) and x < 0 else "— 0.00%"))
                df_['delta_color'] = df_['delta'].apply(lambda x: "green" if x > 0 else ("red" if x < 0 else "gray"))
        elif delta_type_option == "Off":
            for df_ in [df1_filtered, df2_filtered]:
                df_['delta'] = None
                df_['delta_str'] = ""
                df_['delta_color'] = "gray"


        # --------------------------
        # Hover label formatting
        # --------------------------
        for df_ in [df1_filtered, df2_filtered]:
            if 'hover_label' not in df_:
                df_['hover_label'] = df_['date'].dt.strftime("%d %b %Y")

        # --------------------------
        # Plotting
        # --------------------------
        

        fig = go.Figure()

        # Decide if dual-axis needed
        #same_group = group1 == group2
        #unify_axis = same_group and group1 not in ["FX", "Equities", "Stocks", "Commodities", "Crypto"]

        # Plot traces
        if delta_type_option == "Daily Delta Spread":
            # Only one trace needed
            fig.add_trace(go.Scatter(
                x=df1_filtered['date'],
                y=df1_filtered['value'],
                mode="lines",
                name=f"{group1}: {indicator1_label} - {group2}: {indicator2_label} (Spread)",
                customdata=df1_filtered[['hover_label', 'delta_str', 'delta_color']],
                hovertemplate=(
                    "<span style='color:black; font-size:16px'><b>%{customdata[0]}</b></span><br>"
                    "<span style='color:black; font-size:16px'>%{y:.2f}</span><br>"
                    "<span style='color:%{customdata[2]}; font-weight:bold; font-size:16px'>%{customdata[1]}</span>"
                    "<extra></extra>"
                )
            ))
        else:
            # Two normal traces
            for idx, (df_, name, axis) in enumerate([
                (df1_filtered, f"{group1}: {indicator1_label}", "y1"),
                (df2_filtered, f"{group2}: {indicator2_label}", "y1" if unify_axis else "y2")
            ]):
                fig.add_trace(go.Scatter(
                    x=df_['date'],
                    y=df_['value'],
                    mode="lines",
                    name=name,
                    yaxis=axis,
                    customdata=df_[['hover_label', 'delta_str', 'delta_color']],
                    hovertemplate=(
                        "<span style='color:black; font-size:16px'><b>%{customdata[0]}</b></span><br>"
                        "<span style='color:black; font-size:16px'>%{y:.2f}</span><br>"
                        "<span style='color:%{customdata[2]}; font-weight:bold; font-size:16px'>%{customdata[1]}</span>"
                        "<extra></extra>"
                    )
                ))

        # --------------------------
        # Layout
        # --------------------------
        axis_tickfont = dict(size=14, family="Arial Bold", color="black")
        axis_title_font = dict(size=16, family="Arial Bold", color="black")

        if unify_axis or delta_type_option == "Daily Delta Spread":
            fig.update_layout(
                title=dict(
                    text=f"{group1}: {indicator1_label} vs {group2}: {indicator2_label}",
                    x=0.5,
                    xanchor='center',
                    y=0.90,           # lower it slightly from the very top
                    yanchor='top',     # aligns top of title at y
                    font=dict(size=20, family="Arial Bold", color="black")
                ),
                margin=dict(t=150, l=20, r=80, b=80),
                xaxis=dict(
                    title="",
                    tickfont=axis_tickfont,
                    linecolor='black',
                    linewidth=2,
                    showline=True,
                    ticks="outside",
                    ticklen=8,
                    tickson="labels",
                    title_font=axis_title_font,
                    showgrid=False,
                    gridcolor="lightgray",
                    gridwidth=1.2
                ),
                yaxis=dict(
                    title=f"{group1}: {indicator1_label}",
                    side="left",
                    tickfont=axis_tickfont,
                    title_font=axis_title_font,
                    range=y1_range if crosses_zero else None,
                    zeroline=False,
                    showgrid=True,
                    gridcolor="lightgray",
                    gridwidth=1.2,
                    linecolor='black',
                    linewidth=2,
                    showline=True
                ),
                yaxis2=dict(
                    title=f"{group2}: {indicator2_label}",
                    overlaying="y",
                    side="right",
                    tickfont=axis_tickfont,
                    title_font=axis_title_font,
                    range=y2_range if crosses_zero else None,
                    zeroline=False,
                    showgrid=False,
                    linecolor='black',   # makes right axis line visible like left
                    linewidth=2,
                    showline=True
                ),
                template="plotly_white",
                font=dict(color="black"),
                legend=dict(x=0.01, y=1.1, orientation="h"),
                height=525
            )

        else:
            fig.update_layout(
                title=dict(
                    text=f"{group1}: {indicator1_label} vs {group2}: {indicator2_label}",
                    x=0.5,
                    xanchor='center',
                    y=0.90,           # lower it slightly from the very top
                    yanchor='top',     # aligns top of title at y
                    font=dict(size=20, family="Arial Bold", color="black")
                ),
                margin=dict(t=150, l=20, r=80, b=80),
                xaxis=dict(
                    title="",
                    tickfont=axis_tickfont,
                    linecolor='black',
                    linewidth=2,
                    showline=True,
                    ticks="outside",
                    ticklen=8,
                    tickson="labels",
                    title_font=axis_title_font,
                    showgrid=False,
                    gridcolor="lightgray",
                    gridwidth=1.2
                ),
                yaxis=dict(
                    title=f"{group1}: {indicator1_label}",
                    side="left",
                    tickfont=axis_tickfont,
                    title_font=axis_title_font,
                    range=y1_range if crosses_zero else None,
                    zeroline=False,
                    showgrid=True,
                    gridcolor="lightgray",
                    gridwidth=1.2,
                    linecolor='black',
                    linewidth=2,
                    showline=True
                ),
                yaxis2=dict(
                    title=f"{group2}: {indicator2_label}",
                    overlaying="y",
                    side="right",
                    tickfont=axis_tickfont,
                    title_font=axis_title_font,
                    range=y2_range if crosses_zero else None,
                    zeroline=False,
                    showgrid=False,
                    linecolor='black',   # makes right axis line visible like left
                    linewidth=2,
                    showline=True
                ),
                template="plotly_white",
                font=dict(color="black"),
                legend=dict(x=0.01, y=1.1, orientation="h"),
                height=525
            )



        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )


# -------- Economic Calendar Tab --------
if page == "Calendar":

    st.header("📅 Economic Calendar")

    # Load CSV
    df = pd.read_csv("economic_calendar.csv", parse_dates=["Date"])

    # Convert Country and Impact to string if not already
    df['Country'] = df['Country'].astype(str)
    df['Impact'] = df['Impact'].astype(str)

    # Extract months available for filtering
    df['Month'] = df['Date'].dt.strftime("%B %Y")
    months = df['Month'].unique().tolist()

    # Filter widgets
    selected_month = st.selectbox("Select Month", options=["All"] + months, index=0)
    selected_country = st.multiselect("Filter by Country", options=sorted(df['Country'].unique()), default=sorted(df['Country'].unique()))
    selected_impact = st.multiselect("Filter by Impact Level", options=sorted(df['Impact'].unique()), default=sorted(df['Impact'].unique()))
    view_mode = st.selectbox("View Mode", ["Daily", "Weekly", "Monthly"])

    # Filter dataframe based on selections
    filtered_df = df.copy()
    if selected_month != "All":
        filtered_df = filtered_df[filtered_df['Month'] == selected_month]

    filtered_df = filtered_df[
        (filtered_df['Country'].isin(selected_country)) &
        (filtered_df['Impact'].isin(selected_impact))
    ]

    if filtered_df.empty:
        st.warning("No events found for the selected filters.")
        st.stop()

    # Function to render event card
    def render_event_card(row):
        date_str = row['Date'].strftime("%A %d %B")
        time_str = row['Time']
        country_str = row['Country']
        event_str = row['Event']
        impact_str = row['Impact']
        forecast = row['Forecast']
        previous = row['Previous']
        notes = row['Notes']

        impact_color = {
            "🔴 High": "#ff4d4d",
            "🟠 Medium": "#ffa500",
            "🟢 Low": "#32cd32"
        }.get(impact_str, "#888")

        card_html = f"""
        <div style="
            border: 1px solid #ddd;
            border-left: 6px solid {impact_color};
            padding: 15px 20px;
            margin-bottom: 15px;
            border-radius: 6px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.1);
            background-color: #fafafa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            ">
            <div style="font-weight: 600; font-size: 1.05rem; margin-bottom: 10px; color: #222; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                <span style="margin-right: 12px;"><b>Date:</b> {date_str}</span> |
                <span style="margin: 0 12px;"><b>Time:</b> {time_str}</span> |
                <span style="margin: 0 12px;"><b>Country:</b> {country_str}</span> |
                <span style="margin: 0 12px; max-width: 300px; display: inline-block; vertical-align: middle; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{event_str}"><b>Event:</b> {event_str}</span> |
                <span style="margin-left: 12px; color:{impact_color}; font-weight:bold;"><b>Impact:</b> {impact_str}</span>
            </div>
            <div style="font-size: 0.9rem; color: #444; margin-bottom: 4px;">
                <b>Forecast:</b> {forecast} &nbsp;&nbsp; <b>Previous:</b> {previous}
            </div>
            <div style="font-size: 0.9rem; color: #555;">
                <b>Notes:</b> {notes}
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    # Group and display by view mode
    if view_mode == "Daily":
        grouped = filtered_df.sort_values("Date").groupby("Date")

        for date, group in grouped:
            st.subheader(date.strftime("%A, %d %B %Y"))
            for _, row in group.iterrows():
                render_event_card(row)

    elif view_mode == "Weekly":
        filtered_df['YearWeek'] = filtered_df['Date'].dt.strftime('%Y-%U')
        grouped = filtered_df.sort_values("Date").groupby("YearWeek")

        for yearweek, group in grouped:
            year, week_num = map(int, yearweek.split('-'))
            first_day = pd.to_datetime(f'{year}-W{week_num}-1', format='%Y-W%U-%w')
            last_day = first_day + pd.Timedelta(days=6)
            st.subheader(f"Week {week_num}, {year} ({first_day.strftime('%d %b')} - {last_day.strftime('%d %b')})")
            for _, row in group.iterrows():
                render_event_card(row)

    elif view_mode == "Monthly":
        grouped = filtered_df.sort_values("Date").groupby("Month")

        for month, group in grouped:
            st.subheader(month)
            for _, row in group.iterrows():
                render_event_card(row)
 
# -------- Equities Tab --------
if page == "Equities":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "US": ["S&P 500", "NASDAQ", "Dow Jones", "VIX"],
            "Europe": ["FTSE 100", "DAX"],
            "Asia": ["Nikkei 225"],
            "ETFs": ["MSCI Emerging Markets ETF"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Mapping --------
        equities_tickers = {
            "S&P 500": ("^GSPC", "S&P 500"),
            "NASDAQ": ("^IXIC", "NASDAQ"),
            "Dow Jones": ("^DJI", "Dow Jones"),
            "FTSE 100": ("^FTSE", "FTSE 100"),
            "Nikkei 225": ("^N225", "Nikkei 225"),
            "DAX": ("^GDAXI", "DAX"),
            "MSCI Emerging Markets ETF": ("EEM", "MSCI Emerging Markets ETF"),
            "VIX": ("^VIX", "VIX")
        }
        ticker, title = equities_tickers[indicator]

        # Load data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)
        if start_date > end_date:
            st.warning("Start date must be before end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # U.S. Equities
            "S&P 500": (
                "The S&P 500 tracks the performance of 500 large-cap U.S. companies across various sectors. "
                "It is a key benchmark for the overall health of the U.S. equity market and is widely used for portfolio performance comparison."
            ),

            "NASDAQ": (
                "The NASDAQ Composite is a tech-heavy index representing stocks listed on the NASDAQ exchange. "
                "It is sensitive to technology sector trends, innovation cycles, and growth-oriented investor sentiment."
            ),

            "Dow Jones": (
                "The Dow Jones Industrial Average tracks 30 large U.S. industrial and blue-chip companies. "
                "It is often used as a barometer of U.S. corporate and economic performance, particularly for established firms."
            ),

            # UK Equities
            "FTSE 100": (
                "The FTSE 100 represents the 100 largest UK companies by market capitalization. "
                "It provides insight into the performance of the UK’s blue-chip sector and is influenced by domestic economic data and global market trends."
            ),

            # Japan & Europe Equities
            "Nikkei 225": (
                "The Nikkei 225 tracks 225 leading Japanese companies listed on the Tokyo Stock Exchange. "
                "It reflects Japan’s equity market performance and is influenced by domestic economic conditions, corporate earnings, and global trade."
            ),

            "DAX": (
                "The DAX tracks 40 major German companies listed on the Frankfurt Stock Exchange. "
                "It serves as a key indicator of German corporate and economic health and is sensitive to Eurozone economic developments."
            ),

            # Emerging Markets
            "MSCI Emerging Markets ETF": (
                "This ETF tracks equities in emerging market countries, providing broad exposure to developing economies. "
                "Performance is influenced by global growth trends, commodity prices, and investor risk appetite."
            ),

            # Volatility
            "VIX": (
                "The VIX, or Volatility Index, measures the market’s expectations of near-term volatility in the S&P 500. "
                "It is often referred to as the 'fear gauge,' rising during periods of uncertainty or market stress."
            )
        }


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

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)
        mean_val = df_filtered['value'].mean()
        latest_val = df_filtered['value'].iloc[-1]
        min_val = df_filtered['value'].min()
        max_val = df_filtered['value'].max()
        start_val = df_filtered['value'].iloc[0]
        change_since_start = latest_val - start_val

        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (using regression slope)
        slope, _, _, _, _ = linregress(range(n_obs), df_filtered['value'])
        if slope > 0:
            trend = "🔺 Upward"
        elif slope < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Volatility (range as % of mean)
        volatility = ((max_val - min_val) / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)

        # Detect quarterly data
        quarterly = False
        if df_filtered.shape[0] > 1:
            avg_days = (df_filtered['date'].diff().dropna().dt.days.mean())
            if avg_days >= 80:  # ~quarter
                quarterly = True

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            title,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else "daily",
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered[df_filtered['date'].dt.quarter == 4]['date']
            ticktext = df_filtered[df_filtered['date'].dt.quarter == 4].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

                # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=indicator
        )
        
        # ==============================
        # 🧠 Equities Market Macro Summary (LLM-enhanced)
        # ==============================

        import streamlit as st
        import pandas as pd
        import numpy as np
        import datetime as dt
        from scipy.stats import linregress
        import openai  # pip install openai

        # ✅ Set your OpenAI API key in Streamlit secrets or environment variable
        # e.g., in .streamlit/secrets.toml -> [openai] api_key="sk-XXXX"
        openai.api_key = st.secrets["openai"]["api_key"]

        # ---- Streamlit Section Header ----
        st.markdown("### Equities Market Summary (Based on the last 3 Years)")

        @st.cache_data(ttl=3600)
        def get_equities_data(ticker: str):
            """Wrapper for your existing get_fx_data_yahoo function."""
            # Replace this with your actual data loader
            df = get_fx_data_yahoo(ticker, start_date=dt.date(2018, 1, 1), end_date=dt.date.today())
            return df.dropna()

        @st.cache_data(ttl=1800)
        def analyze_equities():
            """Compute normalized position and slope-based trend for major tickers."""
            equities_tickers = {
                "S&P 500": ("^GSPC"),
                "NASDAQ": ("^IXIC"),
                "Dow Jones": ("^DJI"),
                "FTSE 100": ("^FTSE"),
                "Nikkei 225": ("^N225"),
                "DAX": ("^GDAXI"),
                "MSCI Emerging Markets ETF": ("EEM"),
                "VIX": ("^VIX")
            }

            results = {}
            for name, ticker in equities_tickers.items():
                try:
                    df = get_equities_data(ticker)
                    if len(df) < 12:
                        continue
                    df_3y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=3))]
                    latest = df_3y["value"].iloc[-1]
                    min_val, max_val = df_3y["value"].min(), df_3y["value"].max()
                    slope, _, _, _, _ = linregress(range(len(df_3y)), df_3y["value"])
                    pos = (latest - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50
                    trend = "up" if slope > 0 else "down" if slope < 0 else "flat"
                    results[name] = {"latest": latest, "pos": pos, "trend": trend}
                except Exception as e:
                    st.warning(f"⚠️ Could not process {name}: {e}")
            return results
        
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        def generate_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}, trend={data['trend']}, position={data['pos']:.1f}%"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of equities summary**.
            You are given the latest 3-year data snapshot for several major equities.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of equities** based on these numbers.

            Guidelines:
            - Focus on patterns and contrasts across the equities — e.g., which are leading, lagging, or showing extreme positions.
            - Do NOT add information not in the data.
            - Use a neutral, analytical tone (no adjectives like “impressive” or “strong”), but use clear concise english.
            - Output only one paragraph.
            - Keep it natural and varied in structure — not repetitive, like a normal person is saying it.
            - Mention the key data points selectively to illustrate your points.
            """


            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-5-mini" if available
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=250,
                    temperature=0
                )

                summary_text = response.choices[0].message.content.strip()
                if not summary_text:
                    summary_text = "⚠️ LLM returned an empty response."

            except Exception as e:
                summary_text = f"⚠️ LLM generation failed: {e}"

            return summary_text

        # ---- Cached LLM Summary Function ----
        @st.cache_data
        def generate_llm_summary_cached(results: dict):
            return generate_llm_summary(results)


        # ---- Run analysis ----
        if "equities_macro_summary" not in st.session_state:
            with st.spinner("Generating summary..."):
                results = analyze_equities()
                # ✅ use the cached version here
                st.session_state.equities_macro_summary = generate_llm_summary_cached(results)

        # Use cached summary
        equities_macro_summary = st.session_state.equities_macro_summary
        
        # Add Equities summary to global collector
        summary_label = f"Equities Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{equities_macro_summary}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)

        # ---- Display Narrative Card ----
        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #4a4e69;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
        ">
        {equities_macro_summary}
        </div>
        """, unsafe_allow_html=True)

        
# -------- Stocks Tab --------
if page == "Stocks":
    
    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:110px;'>", unsafe_allow_html=True)

        # Select indicator and chart type
        indicator = st.selectbox("Select Indicator", [
            "Apple", "Amazon", "Meta", "Alphabet (Google)", "Nvidia", "Microsoft", "Tesla"
        ])
        chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        # Toggle for delta type
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # Map indicator to Yahoo ticker and chart title
        stock_tickers = {
            "Apple": ("AAPL", "Apple"),
            "Amazon": ("AMZN", "Amazon"),
            "Meta": ("META", "Meta"),
            "Alphabet (Google)": ("GOOGL", "Alphabet (Google)"),
            "Nvidia": ("NVDA", "Nvidia"),
            "Microsoft": ("MSFT", "Microsoft"),
            "Tesla":     ("TSLA", "Tesla")    
        }
        ticker, title = stock_tickers[indicator]

        # Load FX data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1980, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # Time frame selector
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # Date inputs
        # Date inputs side-by-side
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input(
                "Start Date", 
                default_start_date, 
                min_value=earliest_date, 
                max_value=latest_date
            )
        with col_end:
            end_date = st.date_input(
                "End Date", 
                latest_date, 
                min_value=earliest_date, 
                max_value=latest_date
            )

        # Validation
        if start_date > end_date:
            st.warning("Start date must be before end date.")
            st.stop()

        if start_date > end_date:
            st.warning("Start date must be before end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # Commentary for each indicator
        commentary = {
            "Apple": (
                "Apple Inc. is a leading technology company known for its consumer electronics, software, and services, including the iPhone, Mac, and App Store. "
                "Its stock performance is influenced by product launches, innovation cycles, global consumer demand, and supply chain dynamics."
            ),

            "Amazon": (
                "Amazon.com Inc. is a global e-commerce and cloud computing leader. "
                "Its equity is sensitive to online retail trends, Amazon Web Services growth, consumer spending, and regulatory developments."
            ),

            "Meta": (
                "Meta Platforms Inc. (formerly Facebook) operates leading social media platforms, including Facebook, Instagram, and WhatsApp. "
                "Its performance is driven by advertising revenue, user engagement metrics, and developments in virtual/augmented reality."
            ),

            "Alphabet (Google)": (
                "Alphabet Inc., the parent company of Google, dominates global online search, digital advertising, and cloud computing. "
                "Its stock reacts to ad revenue trends, regulatory scrutiny, innovation in AI and cloud services, and overall internet usage growth."
            ),

            "Nvidia": (
                "Nvidia Corporation specializes in graphics processing units (GPUs) and AI computing technologies. "
                "Its stock is highly influenced by demand in gaming, AI, data centers, and broader semiconductor industry trends."
            ),

            "Microsoft": (
                "Microsoft Corporation is a leading technology company offering software, cloud computing, and hardware products. "
                "Key drivers include Windows and Office adoption, Azure cloud growth, enterprise demand, and AI integration."
            ),

            "Tesla": (
                "Tesla Inc. is a leading electric vehicle and clean energy company. "
                "Its stock performance is influenced by EV production and deliveries, technological innovation, regulatory incentives, and global adoption of sustainable energy solutions."
            )
        }

        # Display commentary above chart
        st.markdown(
            f"""
            <div style="
                position: relative;
                top: -20px;
                margin-left: 30px;
                font-size:19px;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                font-weight:normal;
                color:#333;
            ">
                {commentary.get(indicator, "")}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)
        mean_val = df_filtered['value'].mean()
        latest_val = df_filtered['value'].iloc[-1]
        min_val = df_filtered['value'].min()
        max_val = df_filtered['value'].max()
        start_val = df_filtered['value'].iloc[0]
        change_since_start = latest_val - start_val

        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (using regression slope)
        slope, _, _, _, _ = linregress(range(n_obs), df_filtered['value'])
        if slope > 0:
            trend = "🔺 Upward"
        elif slope < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Volatility (range as % of mean)
        volatility = ((max_val - min_val) / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)

        # Detect if quarterly data
        quarterly = False
        if df_filtered.shape[0] > 1:
            avg_days = (df_filtered['date'].diff().dropna().dt.days.mean())
            if avg_days >= 80:  # ~quarter
                quarterly = True

        # Handle delta type
        if delta_type == "Off":
            hover_style = "none"
            delta_type_arg = None
        else:
            hover_style = "delta"
            delta_type_arg = delta_type.lower()

        # Plot chart with dynamic delta and hover
        fig = plot_chart(
            df_filtered,
            title,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else "daily",
            show_markers=False
        )


        # For quarterly charts, show only Q4 labels
        if quarterly:
            tickvals = df_filtered[df_filtered['date'].dt.quarter == 4]['date']
            ticktext = df_filtered[df_filtered['date'].dt.quarter == 4].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        # Display chart with clean modebar
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

                # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=indicator
        )

        # ==============================
        # 🧠 Stock Market Macro Summary (LLM-enhanced)
        # ==============================

        import streamlit as st
        import pandas as pd
        import numpy as np
        import datetime as dt
        from scipy.stats import linregress
        import openai  # pip install openai

        # ✅ Set your OpenAI API key in Streamlit secrets or environment variable
        # e.g., in .streamlit/secrets.toml -> [openai] api_key="sk-XXXX"
        openai.api_key = st.secrets["openai"]["api_key"]

        # ---- Streamlit Section Header ----
        st.markdown("### Stock Market Summary (Based on the last 3 Years)")

        @st.cache_data(ttl=3600)
        def get_stock_data(ticker: str):
            """Wrapper for your existing get_fx_data_yahoo function."""
            # Replace this with your actual data loader
            df = get_fx_data_yahoo(ticker, start_date=dt.date(2018, 1, 1), end_date=dt.date.today())
            return df.dropna()

        @st.cache_data(ttl=1800)
        def analyze_stocks():
            """Compute normalized position and slope-based trend for major tickers."""
            stock_tickers = {
                "Apple": "AAPL",
                "Amazon": "AMZN",
                "Meta": "META",
                "Alphabet": "GOOGL",
                "Nvidia": "NVDA",
                "Microsoft": "MSFT",
                "Tesla": "TSLA"
            }

            results = {}
            for name, ticker in stock_tickers.items():
                try:
                    df = get_stock_data(ticker)
                    if len(df) < 12:
                        continue
                    df_3y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=3))]
                    latest = df_3y["value"].iloc[-1]
                    min_val, max_val = df_3y["value"].min(), df_3y["value"].max()
                    slope, _, _, _, _ = linregress(range(len(df_3y)), df_3y["value"])
                    pos = (latest - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50
                    trend = "up" if slope > 0 else "down" if slope < 0 else "flat"
                    results[name] = {"latest": latest, "pos": pos, "trend": trend}
                except Exception as e:
                    st.warning(f"⚠️ Could not process {name}: {e}")
            return results

        from openai import OpenAI
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        def generate_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}, trend={data['trend']}, position={data['pos']:.1f}%"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of stocks summary**.
            You are given the latest 3-year data snapshot for several major stocks.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of stocks** based on these numbers.

            Guidelines:
            - Focus on patterns and contrasts across the stocks — e.g., which are leading, lagging, or showing extreme positions.
            - Do NOT add information not in the data.
            - Use a neutral, analytical tone (no adjectives like “impressive” or “strong”), but use clear concise english.
            - Output only one paragraph.
            - Keep it natural and varied in structure — not repetitive, like a normal person is saying it.
            - Mention the key data points selectively to illustrate your points.
            """


            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-5-mini" if available
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=250,
                    temperature=0
                )

                summary_text = response.choices[0].message.content.strip()
                if not summary_text:
                    summary_text = "⚠️ LLM returned an empty response."

            except Exception as e:
                summary_text = f"⚠️ LLM generation failed: {e}"

            return summary_text

        # ---- Cached LLM Summary Function ----
        @st.cache_data
        def generate_llm_summary_cached(results: dict):
            return generate_llm_summary(results)


        # ---- Run analysis ----
        if "stock_macro_summary" not in st.session_state:
            with st.spinner("Generating summary..."):
                results = analyze_stocks()
                # ✅ use the cached version here
                st.session_state.stock_macro_summary = generate_llm_summary_cached(results)

        # Use cached summary
        stock_macro_summary = st.session_state.stock_macro_summary
        
        # Add Stocks summary to global collector
        summary_label = f"Stocks Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{stock_macro_summary}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)


        # ---- Display Narrative Card ----
        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #4a4e69;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
        ">
        {stock_macro_summary}
        </div>
        """, unsafe_allow_html=True)

        
# -------- Commodities Tab --------
if page == "Commodities":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Energy": ["Crude Oil", "Natural Gas", "Brent Oil"],
            "Metals": ["Gold", "Silver", "Copper"],
            "Agriculture": ["Wheat", "Corn", "Soybeans"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
      
        indicator_map = {
            "Crude Oil": ("CL=F", "daily", None),
            "Natural Gas": ("NG=F", "daily", None),
            "Brent Oil": ("BZ=F", "daily", None),
            "Gold": ("GC=F", "daily", None),
            "Silver": ("SI=F", "daily", None),
            "Copper": ("HG=F", "daily", None),
            "Wheat": ("ZW=F", "daily", None),
            "Corn": ("ZC=F", "daily", None),
            "Soybeans": ("ZS=F", "daily", None)
        }

        ticker, date_format, tickformat_override = indicator_map[indicator]
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1990, 1, 1), end_date=dt.date.today())

        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # Energy Commodities
            "Crude Oil": (
                "Crude oil prices reflect global supply and demand dynamics, OPEC production decisions, and geopolitical risks. "
                "They are influenced by global economic growth, inventory levels, and disruptions in major producing regions."
            ),

            "Natural Gas": (
                "Natural gas prices are sensitive to weather patterns, seasonal heating/cooling demand, storage levels, and energy consumption trends. "
                "They are also influenced by pipeline infrastructure, liquefied natural gas (LNG) exports, and policy regulations."
            ),

            "Brent Oil": (
                "Brent crude oil is a major international benchmark, reflecting global oil market trends. "
                "It is influenced by production in Europe, Africa, and the Middle East, as well as global demand forecasts."
            ),

            # Precious Metals
            "Gold": (
                "Gold is a safe-haven asset that reacts to inflation expectations, USD strength, interest rates, and geopolitical uncertainty. "
                "It is widely used for portfolio hedging and wealth preservation."
            ),

            "Silver": (
                "Silver serves both as an industrial metal and a store of value. "
                "Its price is influenced by industrial demand, investor sentiment, and monetary policy conditions."
            ),

            # Industrial Metals
            "Copper": (
                "Copper is a key industrial metal whose price reflects global manufacturing activity and economic growth. "
                "It is sensitive to construction, infrastructure demand, and supply disruptions in major producing countries."
            ),

            # Agricultural Commodities
            "Wheat": (
                "Wheat prices respond to global crop yields, weather conditions, planting and harvesting cycles, and international demand. "
                "They are also affected by export policies and geopolitical events impacting major wheat-producing countries."
            ),

            "Corn": (
                "Corn prices are influenced by planting and harvest cycles, ethanol production demand, livestock feed requirements, and weather conditions. "
                "Global trade policies and U.S. crop reports play a key role in price fluctuations."
            ),

            "Soybeans": (
                "Soybean prices track agricultural supply, global consumption, and trade policies. "
                "They are impacted by crop yields, weather events, biofuel demand, and geopolitical developments affecting major exporters."
            )
        }


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

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)
        mean_val = df_filtered['value'].mean()
        latest_val = df_filtered['value'].iloc[-1]
        min_val = df_filtered['value'].min()
        max_val = df_filtered['value'].max()
        start_val = df_filtered['value'].iloc[0]
        change_since_start = latest_val - start_val

        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (using regression slope)
        slope, _, _, _, _ = linregress(range(n_obs), df_filtered['value'])
        if slope > 0:
            trend = "🔺 Upward"
        elif slope < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Volatility (range as % of mean)
        volatility = ((max_val - min_val) / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)

        # Detect if quarterly data (rare for commodities)
        quarterly = False
        if df_filtered.shape[0] > 1:
            avg_days = (df_filtered['date'].diff().dropna().dt.days.mean())
            if avg_days >= 80:
                quarterly = True

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            indicator,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered[df_filtered['date'].dt.quarter == 4]['date']
            ticktext = df_filtered[df_filtered['date'].dt.quarter == 4].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

                # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=indicator
        )

        # ==============================
        # 🧠 Commodities Market Macro Summary (LLM-enhanced)
        # ==============================

        import streamlit as st
        import pandas as pd
        import numpy as np
        import datetime as dt
        from scipy.stats import linregress
        import openai  # pip install openai

        # ✅ Set your OpenAI API key in Streamlit secrets or environment variable
        # e.g., in .streamlit/secrets.toml -> [openai] api_key="sk-XXXX"
        openai.api_key = st.secrets["openai"]["api_key"]

        # ---- Streamlit Section Header ----
        st.markdown("### Commodities Market Summary (Based on the last 3 Years)")

        @st.cache_data(ttl=3600)
        def get_commodities_data(ticker: str):
            """Wrapper for your existing get_fx_data_yahoo function."""
            # Replace this with your actual data loader
            df = get_fx_data_yahoo(ticker, start_date=dt.date(2018, 1, 1), end_date=dt.date.today())
            return df.dropna()

        @st.cache_data(ttl=1800)
        def analyze_commodities():
            """Compute normalized position and slope-based trend for major tickers."""
            commodities_tickers = {
                 "Crude Oil": ("CL=F"),
                "Natural Gas": ("NG=F"),
                "Brent Oil": ("BZ=F"),
                "Gold": ("GC=F"),
                "Silver": ("SI=F"),
                "Copper": ("HG=F"),
                "Wheat": ("ZW=F"),
                "Corn": ("ZC=F"),
                "Soybeans": ("ZS=F")
            }

            results = {}
            for name, ticker in commodities_tickers.items():
                try:
                    df = get_commodities_data(ticker)
                    if len(df) < 12:
                        continue
                    df_3y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=3))]
                    latest = df_3y["value"].iloc[-1]
                    min_val, max_val = df_3y["value"].min(), df_3y["value"].max()
                    slope, _, _, _, _ = linregress(range(len(df_3y)), df_3y["value"])
                    pos = (latest - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50
                    trend = "up" if slope > 0 else "down" if slope < 0 else "flat"
                    results[name] = {"latest": latest, "pos": pos, "trend": trend}
                except Exception as e:
                    st.warning(f"⚠️ Could not process {name}: {e}")
            return results
        
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        def generate_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}, trend={data['trend']}, position={data['pos']:.1f}%"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of commodities summary**.
            You are given the latest 3-year data snapshot for several major commodities.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of commodities** based on these numbers.

            Guidelines:
            - Focus on patterns and contrasts across the commodities — e.g., which are leading, lagging, or showing extreme positions.
            - Do NOT add information not in the data.
            - Use a neutral, analytical tone (no adjectives like “impressive” or “strong”), but use clear concise english.
            - Output only one paragraph.
            - Keep it natural and varied in structure — not repetitive, like a normal person is saying it.
            - Mention the key data points selectively to illustrate your points.
            """


            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-5-mini" if available
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=250,
                    temperature=0
                )

                summary_text = response.choices[0].message.content.strip()
                if not summary_text:
                    summary_text = "⚠️ LLM returned an empty response."

            except Exception as e:
                summary_text = f"⚠️ LLM generation failed: {e}"

            return summary_text

        # ---- Cached LLM Summary Function ----
        @st.cache_data
        def generate_llm_summary_cached(results: dict):
            return generate_llm_summary(results)


        # ---- Run analysis ----
        if "commodities_macro_summary" not in st.session_state:
            with st.spinner("Generating summary..."):
                results = analyze_commodities()
                # ✅ use the cached version here
                st.session_state.commodities_macro_summary = generate_llm_summary_cached(results)

        # Use cached summary
        commodities_macro_summary = st.session_state.commodities_macro_summary
        
        # Add commodities summary to global collector
        summary_label = f"Commodities Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{commodities_macro_summary}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)

        # ---- Display Narrative Card ----
        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #4a4e69;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
        ">
        {commodities_macro_summary}
        </div>
        """, unsafe_allow_html=True)

        
# -------- Bonds Tab --------
if page == "Bonds":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Bond Categories --------
        bond_groups = {
            "US Treasuries": ["US 2Y", "US 10Y"],
            "UK Gilts": ["UK 2Y", "UK 10Y"],
            "Japan JGBs": ["Japan 2Y", "Japan 10Y"],
            "Euro Bonds": ["Euro 2Y", "Euro 10Y"]
        }

        # Category dropdown
        category = st.selectbox("Select Country/Group", list(bond_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Bond", bond_groups[category])

        # -------- Chart Type + Time Frame side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Bond Indicator Mapping --------
        bond_map = {
            "US 2Y": (get_usa_2yr_yield_data, "US 2-Year Treasury Yield"),
            "US 10Y": (get_usa_10yr_yield_data, "US 10-Year Treasury Yield"),
            "UK 2Y": (get_uk_2yr_yield_data, "UK 2-Year Gilt Yield"),
            "UK 10Y": (get_uk_10yr_yield_data, "UK 10-Year Gilt Yield"),
            "Japan 2Y": (get_japan_2yr_yield_data, "Japan 2-Year JGB Yield"),
            "Japan 10Y": (get_japan_10yr_yield_data, "Japan 10-Year JGB Yield"),
            "Euro 2Y": (get_euro_2yr_yield_data, "Euro 2-Year Yield"),
            "Euro 10Y": (get_euro_10yr_yield_data, "Euro 10-Year Yield")
        }

        data_func, title = bond_map[indicator]

        # Load bond data
        df = data_func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date must be before end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # U.S. Treasuries
            "US 2Y": (
                "The US 2-Year Treasury yield reflects short-term interest rate expectations and Federal Reserve policy guidance. "
                "It is highly sensitive to Fed rate changes, inflation data, and economic forecasts, serving as a barometer for near-term monetary policy."
            ),

            "US 10Y": (
                "The US 10-Year Treasury yield signals long-term growth and inflation expectations in the U.S. economy. "
                "It is influenced by economic data, Federal Reserve policy, and investor sentiment regarding future inflation and fiscal policy."
            ),

            # UK Gilts
            "UK 2Y": (
                "The UK 2-Year Gilt yield responds primarily to Bank of England policy guidance and short-term rate expectations. "
                "It reflects market sentiment on near-term monetary policy and economic conditions in the UK."
            ),

            "UK 10Y": (
                "The UK 10-Year Gilt yield indicates long-term expectations for inflation, growth, and fiscal stability. "
                "It is influenced by government borrowing, economic data, and Bank of England policy signals."
            ),

            # Japan Government Bonds
            "Japan 2Y": (
                "The Japan 2-Year JGB yield tracks short-term expectations for Bank of Japan policy. "
                "It is closely tied to BoJ rate guidance, domestic economic conditions, and market sentiment."
            ),

            "Japan 10Y": (
                "The Japan 10-Year JGB yield reflects long-term growth and inflation expectations in Japan. "
                "It is influenced by BoJ policy, government debt issuance, and global economic trends."
            ),

            # Eurozone Bonds
            "Euro 2Y": (
                "The Euro 2-Year government bond yield reflects ECB policy signals and short-term interest rate expectations across the Eurozone. "
                "It is sensitive to ECB guidance, inflation data, and economic activity."
            ),

            "Euro 10Y": (
                "The Euro 10-Year government bond yield signals long-term growth and inflation expectations in the Eurozone. "
                "It is influenced by fiscal policies, ECB strategy, and investor demand for euro-denominated debt."
            )
        }


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

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)
        mean_val = df_filtered['value'].mean()
        latest_val = df_filtered['value'].iloc[-1]
        min_val = df_filtered['value'].min()
        max_val = df_filtered['value'].max()
        start_val = df_filtered['value'].iloc[0]
        change_since_start = latest_val - start_val

        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (using regression slope)
        slope, _, _, _, _ = linregress(range(n_obs), df_filtered['value'])
        if slope > 0:
            trend = "🔺 Upward"
        elif slope < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Volatility (range as % of mean)
        volatility = ((max_val - min_val) / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)

        # Detect quarterly data
        quarterly = False
        if df_filtered.shape[0] > 1:
            avg_days = df_filtered['date'].diff().dropna().dt.days.mean()
            if avg_days >= 80:  # ~quarter
                quarterly = True

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            title,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else "daily",
            show_markers=False
        )

        if quarterly:
            tickvals = df_filtered[df_filtered['date'].dt.quarter == 4]['date']
            ticktext = df_filtered[df_filtered['date'].dt.quarter == 4].dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

                # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=indicator
        )

        # ==============================
        # 🧠 Bonds Market Macro Summary (LLM-enhanced)
        # ==============================

        import openai
        from openai import OpenAI

        # Set API key
        openai.api_key = st.secrets["openai"]["api_key"]
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        
        st.markdown("### Bond Market Summary (Based on the last 3 Years)")

        @st.cache_data(ttl=1800)
        def analyze_bonds():
            """Compute latest value, slope, and relative position for all bond indicators."""
            bond_tickers = {
                "US 2Y": get_usa_2yr_yield_data,
                "US 10Y": get_usa_10yr_yield_data,
                "UK 2Y": get_uk_2yr_yield_data,
                "UK 10Y": get_uk_10yr_yield_data,
                "Japan 2Y": get_japan_2yr_yield_data,
                "Japan 10Y": get_japan_10yr_yield_data,
                "Euro 2Y": get_euro_2yr_yield_data,
                "Euro 10Y": get_euro_10yr_yield_data
            }

            results = {}
            for name, func in bond_tickers.items():
                try:
                    df = func().dropna()
                    if len(df) < 12:
                        continue
                    df_3y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=3))]
                    latest = df_3y["value"].iloc[-1]
                    min_val, max_val = df_3y["value"].min(), df_3y["value"].max()
                    slope, _, _, _, _ = linregress(range(len(df_3y)), df_3y["value"])
                    pos = (latest - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50
                    trend = "up" if slope > 0 else "down" if slope < 0 else "flat"
                    results[name] = {"latest": latest, "pos": pos, "trend": trend}
                except Exception as e:
                    st.warning(f"⚠️ Could not process {name}: {e}")
            return results

        def generate_bonds_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}%, trend={data['trend']}, position={data['pos']:.1f}%"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of global bond markets summary**.
            You are given the latest 3-year snapshot for yields of various government bonds.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of bond markets** based on these numbers.

            Guidelines:
            - Focus on patterns, contrasts, and relative positioning across countries and maturities.
            - Mention short-term vs long-term yield trends where relevant.
            - Do NOT add information not in the data.
            - Use a neutral, analytical tone (no adjectives like “strong” or “weak”), but clear and concise English.
            - Output only one paragraph.
            - Keep the paragraph natural and varied, like a professional commentary.
            """

            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-5-mini" if available
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=250,
                    temperature=0
                )
                summary_text = response.choices[0].message.content.strip()
                if not summary_text:
                    summary_text = "⚠️ LLM returned an empty response."
            except Exception as e:
                summary_text = f"⚠️ LLM generation failed: {e}"

            return summary_text

        @st.cache_data
        def generate_bonds_llm_summary_cached(results: dict):
            return generate_bonds_llm_summary(results)

        # ---- Run analysis ----
        if "bonds_macro_summary" not in st.session_state:
            with st.spinner("Generating bond market summary..."):
                results = analyze_bonds()
                st.session_state.bonds_macro_summary = generate_bonds_llm_summary_cached(results)

        # Use cached summary
        bonds_macro_summary = st.session_state.bonds_macro_summary
        
        # Add Bonds summary to global collector
        summary_label = f"Bonds Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{bonds_macro_summary}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)

        # ---- Display Narrative Card ----
        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #4a4e69;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
        ">
        {bonds_macro_summary}
        </div>
        """, unsafe_allow_html=True)


     
# -------- Crypto Tab --------
if page == "Crypto":
    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Major Coins": ["Bitcoin", "Ethereum"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        crypto_map = {
            "Bitcoin": ("BTC-USD", "Bitcoin"),
            "Ethereum": ("ETH-USD", "Ethereum")
        }
        ticker, title = crypto_map[indicator]

        # Load crypto data
        df = get_fx_data_yahoo(ticker, start_date=dt.date(1990, 1, 1), end_date=dt.date.today())
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            "Bitcoin": (
                "Bitcoin is the largest cryptocurrency by market capitalization and is often considered 'digital gold.' "
                "Its price is influenced by investor sentiment, adoption trends, regulatory developments, macroeconomic conditions, and supply-demand dynamics of its fixed supply."
            ),

            "Ethereum": (
                "Ethereum is the leading smart contract platform, enabling decentralized applications (dApps), decentralized finance (DeFi), and NFTs. "
                "Its value is driven by network activity, adoption of dApps, technological upgrades, gas fees, and overall crypto market sentiment."
            )
        }


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

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)
        mean_val = df_filtered['value'].mean()
        latest_val = df_filtered['value'].iloc[-1]
        min_val = df_filtered['value'].min()
        max_val = df_filtered['value'].max()
        start_val = df_filtered['value'].iloc[0]
        change_since_start = latest_val - start_val

        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (using regression slope)
        slope, _, _, _, _ = linregress(range(n_obs), df_filtered['value'])
        if slope > 0:
            trend = "🔺 Upward"
        elif slope < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Volatility (range as % of mean)
        volatility = ((max_val - min_val) / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)

        # Detect if quarterly data (optional for crypto, usually daily)
        quarterly = False

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"

        fig = plot_chart(
            df_filtered,
            title,
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="daily",
            show_markers=False
        )

        # Display chart
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

                # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=indicator
        )
        
        # ==============================
        # 🧠 Crypto Market Macro Summary (LLM-enhanced)
        # ==============================

        import streamlit as st
        import pandas as pd
        import numpy as np
        import datetime as dt
        from scipy.stats import linregress
        import openai  # pip install openai

        # ✅ Set your OpenAI API key in Streamlit secrets or environment variable
        # e.g., in .streamlit/secrets.toml -> [openai] api_key="sk-XXXX"
        openai.api_key = st.secrets["openai"]["api_key"]

        # ---- Streamlit Section Header ----
        st.markdown("### Crypto Market Summary (Based on the last 3 Years)")

        @st.cache_data(ttl=3600)
        def get_crypto_data(ticker: str):
            """Wrapper for your existing get_fx_data_yahoo function."""
            # Replace this with your actual data loader
            df = get_fx_data_yahoo(ticker, start_date=dt.date(2018, 1, 1), end_date=dt.date.today())
            return df.dropna()

        @st.cache_data(ttl=1800)
        def analyze_crypto():
            """Compute normalized position and slope-based trend for major tickers."""
            crypto_tickers = {
                "Bitcoin": ("BTC-USD"),
                "Ethereum": ("ETH-USD")
            }

            results = {}
            for name, ticker in crypto_tickers.items():
                try:
                    df = get_crypto_data(ticker)
                    if len(df) < 12:
                        continue
                    df_3y = df[df["date"] >= (df["date"].max() - pd.DateOffset(years=3))]
                    latest = df_3y["value"].iloc[-1]
                    min_val, max_val = df_3y["value"].min(), df_3y["value"].max()
                    slope, _, _, _, _ = linregress(range(len(df_3y)), df_3y["value"])
                    pos = (latest - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50
                    trend = "up" if slope > 0 else "down" if slope < 0 else "flat"
                    results[name] = {"latest": latest, "pos": pos, "trend": trend}
                except Exception as e:
                    st.warning(f"⚠️ Could not process {name}: {e}")
            return results
        
        from openai import OpenAI
        client = OpenAI(api_key=st.secrets["openai"]["api_key"])

        def generate_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}, trend={data['trend']}, position={data['pos']:.1f}%"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of crypto summary**.
            You are given the latest 3-year data snapshot for several major crypto.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of crypto** based on these numbers.

            Guidelines:
            - Focus on patterns and contrasts across the commodities — e.g., which are leading, lagging, or showing extreme positions.
            - Do NOT add information not in the data.
            - Use a neutral, analytical tone (no adjectives like “impressive” or “strong”), but use clear concise english.
            - Output only one paragraph.
            - Keep it natural and varied in structure — not repetitive, like a normal person is saying it.
            - Mention the key data points selectively to illustrate your points.
            """


            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # or "gpt-5-mini" if available
                    messages=[{"role": "user", "content": prompt}],
                    max_completion_tokens=250,
                    temperature=0
                )

                summary_text = response.choices[0].message.content.strip()
                if not summary_text:
                    summary_text = "⚠️ LLM returned an empty response."

            except Exception as e:
                summary_text = f"⚠️ LLM generation failed: {e}"

            return summary_text

        # ---- Cached LLM Summary Function ----
        @st.cache_data
        def generate_llm_summary_cached(results: dict):
            return generate_llm_summary(results)


        # ---- Run analysis ----
        if "crypto_macro_summary" not in st.session_state:
            with st.spinner("Generating summary..."):
                results = analyze_crypto()
                # ✅ use the cached version here
                st.session_state.crypto_macro_summary = generate_llm_summary_cached(results)

        # Use cached summary
        crypto_macro_summary = st.session_state.crypto_macro_summary
        
        # Add Crypto summary to global collector
        summary_label = f"Crypto Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{crypto_macro_summary}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)

        # ---- Display Narrative Card ----
        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #4a4e69;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
        ">
        {crypto_macro_summary}
        </div>
        """, unsafe_allow_html=True)


       
# -------- Yield Curve Tab --------
if page == "Yield Curve":

    col1, col2 = st.columns([1.5, 5])

    with col1:
        # ---------- Centered Page Title ----------
        st.markdown(f"""
            <div style="
                position: absolute;
                top: 0px;  /* keeps it at the top of col1 */
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                {page}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Country Selection --------
        country = st.selectbox("Select Country", ["US", "UK", "Japan", "Euro"])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # -------- Delta Type --------
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Maturity Functions --------
        yield_funcs = {
            "US": {"1M": get_usa_1mo_yield_data, "3M": get_usa_3mo_yield_data, "6M": get_usa_6mo_yield_data,
                   "1Y": get_usa_1yr_yield_data, "2Y": get_usa_2yr_yield_data, "3Y": get_usa_3yr_yield_data,
                   "5Y": get_usa_5yr_yield_data, "7Y": get_usa_7yr_yield_data, "10Y": get_usa_10yr_yield_data,
                   "20Y": get_usa_20yr_yield_data, "30Y": get_usa_30yr_yield_data},
            "UK": {"2Y": get_uk_2yr_yield_data, "10Y": get_uk_10yr_yield_data},
            "Japan": {"2Y": get_japan_2yr_yield_data, "10Y": get_japan_10yr_yield_data},
            "Euro": {"2Y": get_euro_2yr_yield_data, "10Y": get_euro_10yr_yield_data}
        }

        # Sort maturities numerically
        def maturity_to_months(m):
            return int(m[:-1]) * 12 if m.endswith("Y") else int(m[:-1])

        maturities = sorted(list(yield_funcs[country].keys()), key=maturity_to_months)

        # Default selections
        default_long = "10Y" if "10Y" in maturities else maturities[-1]
        default_short = "2Y" if "2Y" in maturities else maturities[0]

        maturity_short = st.selectbox("Short-term Maturity", maturities,
                                      index=maturities.index(default_short))

        long_options = [m for m in maturities if maturity_to_months(m) > maturity_to_months(maturity_short)]
        if not long_options:
            long_options = [maturity_short]
        maturity_long = st.selectbox("Long-term Maturity", long_options,
                                     index=long_options.index(default_long) if default_long in long_options else 0)

        # -------- Load Data --------
        df_long = yield_funcs[country][maturity_long]().dropna().rename(columns={'value': f'yield_{maturity_long}'})
        df_short = yield_funcs[country][maturity_short]().dropna().rename(columns={'value': f'yield_{maturity_short}'})
        df = pd.merge(df_long, df_short, on='date')
        df['spread'] = df[f'yield_{maturity_long}'] - df[f'yield_{maturity_short}']

        # -------- Time Frame Logic --------
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365*years))
        else:
            default_start_date = earliest_date

        # -------- Start & End Dates side by side --------
        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("Start date cannot be after end date.")
            st.stop()

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = f"{country} {maturity_long}-{maturity_short} spread indicates yield curve shape and market expectations."
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
                {commentary}
            </div>
            """,
            unsafe_allow_html=True
        )

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        import numpy as np
        from scipy.stats import linregress

        # ======== Summary Stats ========

        n_obs = len(df_filtered)
        mean_val = df_filtered['spread'].mean()
        latest_val = df_filtered['spread'].iloc[-1]
        min_val = df_filtered['spread'].min()
        max_val = df_filtered['spread'].max()
        start_val = df_filtered['spread'].iloc[0]
        change_since_start = latest_val - start_val


        # Relative position (0–100%)
        position_pct = (latest_val - min_val) / (max_val - min_val) * 100 if max_val != min_val else 50

        # Trend (using regression slope)
        slope, _, _, _, _ = linregress(range(n_obs), df_filtered['spread'])
        if slope > 0:
            trend = "🔺 Upward"
        elif slope < 0:
            trend = "🔻 Downward"
        else:
            trend = "⏸ Flat"

        # Volatility (range as % of mean)
        volatility = ((max_val - min_val) / mean_val * 100) if mean_val != 0 else np.nan

        # ======== Display (Minimal Modern Summary Bar) ========

        summary_html = f"""
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
            <div>Data Points: <b>{n_obs}</b></div>
            <div>Mean: <b>{mean_val:.2f}</b></div>
            <div>Latest: <b>{latest_val:.2f}</b></div>
            <div>Change: <b style='color:{'#06b606' if change_since_start>0 else '#e63946' if change_since_start<0 else '#333'};'>{change_since_start:+.2f}</b></div>
            <div>Trend: <b>{trend}</b></div>
            <div>Position: <b>{position_pct:.0f}% ({'High' if position_pct>70 else 'Low' if position_pct<30 else 'Mid'})</b></div>
            <div>Volatility: <b>{volatility:.1f}%</b></div>
        </div>
        """

        st.markdown(summary_html, unsafe_allow_html=True)
        df_plot = df_filtered[['date', 'spread']].rename(columns={'spread': 'value'})

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg else "none"

        fig = plot_chart(
            df_plot,
            title=f"{country} {maturity_long}-{maturity_short} Yield Spread",
            chart_type=chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="daily",
            show_markers=False
        )

        fig.add_hline(
            y=0,
            line=dict(color="black", width=3, dash="solid"),
            annotation_text="0",
            annotation_position="top left",
            opacity=0.8
        )

        fig.update_layout(
            hoverlabel=dict(font_size=13, font_color="black", font_family="Arial")
        )

        # -------- Display Chart --------
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

                # -------- Full-width Indicator Alert Panel --------
        def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
            """
            Display a full-width alert panel for the selected indicator
            """
            # Determine status
            if position_pct >= 90 and slope > 0:
                status = "Extreme High"
                color = "#e63946"  # Red
                emoji = "🚨"
                message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
            elif position_pct <= 10 and slope < 0:
                status = "Extreme Low"
                color = "#1d3557"  # Dark blue
                emoji = "⚠️"
                message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
            elif position_pct >= 70:
                status = "High"
                color = "#f77f00"  # Orange
                emoji = "🔺"
                message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
            elif position_pct <= 30:
                status = "Low"
                color = "#2a9d8f"  # Teal
                emoji = "🔻"
                message = f"{indicator_name} is below normal levels. Could indicate caution."
            else:
                status = "Normal"
                color = "#06b606"  # Green
                emoji = "✅"
                message = f"{indicator_name} is within normal historical range."

            # HTML panel
            alert_html = f"""
            <div style="
                width: 100%;
                background-color:{color}1A;  /* light transparent background */
                border-left: 6px solid {color};
                border-radius: 8px;
                padding: 18px 24px;
                margin-top: 18px;
                margin-bottom: 24px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                box-shadow:0 2px 6px rgba(0,0,0,0.05);
            ">
                <div style="font-size:18px; font-weight:700; margin-bottom:6px;">
                    {emoji} {indicator_name}: {status}
                </div>
                <div style="font-size:14px; line-height:1.5; color:#111;">
                    Latest: <b>{latest_val:.2f}</b> | Mean: <b>{mean_val:.2f}</b> | Position: <b>{position_pct:.0f}%</b> | Volatility: <b>{volatility:.1f}%</b>
                </div>
                <div style="margin-top:6px; font-size:14px; color:#333;">
                    {message}
                </div>
            </div>
            """
            st.markdown(alert_html, unsafe_allow_html=True)

        # -------- Call it after plotting chart --------
        display_indicator_alert(
            latest_val=latest_val,
            mean_val=mean_val,
            position_pct=position_pct,
            slope=slope,
            volatility=volatility,
            indicator_name=f"{country} {maturity_long}-{maturity_short} Yield Spread"
        )




# -------- Regime Yield Curve Tab (All Maturities + Line Chart Only) --------
if page == "Curve Regimes":

    # Outer columns: left for controls + table, right for chart
    outer_col1, outer_col2 = st.columns([3, 5])

    with outer_col1:
        # Select country
        country = st.selectbox("Select Country", ["US", "UK", "Japan", "Euro"])

        # Periods for delta table
        period_offsets = {
            "1M": pd.DateOffset(months=1),
            "3M": pd.DateOffset(months=3),
            "1Y": pd.DateOffset(years=1)
        }

        # Map country to all yield maturities
        yield_funcs = {
            "US": {
                "1M": get_usa_1mo_yield_data,
                "3M": get_usa_3mo_yield_data,
                "1Y": get_usa_1yr_yield_data,
                "2Y": get_usa_2yr_yield_data,
                "3Y": get_usa_3yr_yield_data,
                "5Y": get_usa_5yr_yield_data,
                "7Y": get_usa_7yr_yield_data,
                "10Y": get_usa_10yr_yield_data,
                "20Y": get_usa_20yr_yield_data,
                "30Y": get_usa_30yr_yield_data
            },
            "UK": {"2Y": get_uk_2yr_yield_data, "10Y": get_uk_10yr_yield_data},
            "Japan": {"2Y": get_japan_2yr_yield_data, "10Y": get_japan_10yr_yield_data},
            "Euro": {"2Y": get_euro_2yr_yield_data, "10Y": get_euro_10yr_yield_data}
        }

        # Load all maturities for the country
        dfs = []
        for mat, func in yield_funcs[country].items():
            df_temp = func().dropna().rename(columns={'value': mat})
            dfs.append(df_temp)
        df = dfs[0]
        for df_next in dfs[1:]:
            df = pd.merge(df, df_next, on='date')

        # Latest date
        latest_date = df['date'].max()
        df_now = df[df['date'] == latest_date].iloc[0]

        # Build vertical delta table: maturities as rows, periods as columns
        maturities = [m for m in df.columns if m != 'date']
        table_data = {}
        table_data["Now"] = [df_now[m] for m in maturities]

        for label, offset in period_offsets.items():
            ref_date = latest_date - offset
            idx = (df['date'] - ref_date).abs().idxmin()
            row = df.loc[idx]
            table_data[label] = [df_now[m] - row[m] for m in maturities]

        df_table = pd.DataFrame(table_data, index=maturities)
        df_table.index.name = "Maturity"

        # HTML table rendering with color coding, unbold cell values, centered
        # HTML table rendering with color coding, unbold cell values, centered, first row & column highlighted
        def render_html_table(df):
            html = '<table style="border-collapse: collapse; width:100%;">'
            # Header row
            html += '<tr>'
            html += f'<th style="font-weight:bold; color:black; border: 1px solid black; padding:4px; text-align:center; background-color:#F9F9F9;">Maturity</th>'
            for col in df.columns:
                html += f'<th style="font-weight:bold; color:black; border: 1px solid black; padding:4px; text-align:center; background-color:#F9F9F9;">{col}</th>'
            html += '</tr>'
            # Rows
            for idx in df.index:
                html += f'<tr>'
                # First column (maturity)
                html += f'<th style="font-weight:bold; color:black; border: 1px solid black; padding:4px; text-align:center; background-color:#F9F9F9;">{idx}</th>'
                # Other columns
                for col in df.columns:
                    val = df.loc[idx, col]
                    if col == "Now":
                        color = "black"
                    else:
                        if val > 0:
                            color = "green"
                        elif val < 0:
                            color = "red"
                        else:
                            color = "black"
                    html += f'<td style="color:{color}; font-weight:normal; border: 1px solid black; padding:4px; text-align:center;">{val:+.2f}%</td>'
                html += '</tr>'
            html += '</table>'
            return html

        st.markdown(render_html_table(df_table), unsafe_allow_html=True)


    with outer_col2:
        # Regime calculation (short vs long 2Y vs 10Y)
        if "2Y" in df.columns and "10Y" in df.columns:
            ref_date_1m = latest_date - pd.DateOffset(months=1)
            idx_1m = (df['date'] - ref_date_1m).abs().idxmin()
            delta_2y = df_now['2Y'] - df.loc[idx_1m, '2Y']
            delta_10y = df_now['10Y'] - df.loc[idx_1m, '10Y']

            if delta_2y < 0 and delta_10y < 0:
                regime = "Bull Flattener" if abs(delta_10y) > abs(delta_2y) else "Bull Steepener"
            elif delta_2y > 0 and delta_10y > 0:
                regime = "Bear Flattener" if abs(delta_2y) > abs(delta_10y) else "Bear Steepener"
            elif delta_2y < 0 and delta_10y > 0:
                regime = "Bull Steepener"
            elif delta_2y > 0 and delta_10y < 0:
                regime = "Bear Steepener"
            else:
                regime = "Indeterminate"
        else:
            regime = "N/A"
        st.markdown(f"**Current Regime (Now vs 1M): {regime}**")

        # -------- Line Chart (all maturities, historical periods) --------
        df_plot_rows = []
        for label, offset in {"Now": None, **period_offsets}.items():
            if label == "Now":
                row = df_now.copy()
            else:
                ref_date = latest_date - offset
                idx = (df['date'] - ref_date).abs().idxmin()
                row = df.loc[idx].copy()
            row['Period'] = label
            df_plot_rows.append(row)

        df_plot = pd.DataFrame(df_plot_rows)
        df_melt = df_plot.melt(id_vars="Period", value_vars=maturities,
                               var_name="Maturity", value_name="Yield")

        fig = go.Figure()
        for period in df_plot['Period']:
            temp = df_melt[df_melt['Period'] == period]
            fig.add_trace(go.Scatter(
                x=temp['Maturity'],
                y=temp['Yield'],
                mode="lines+markers",
                name=period,
                hovertemplate="<b>%{x}</b><br>Yield: %{y:.2f}%<extra></extra>"
            ))

        axis_tickfont = dict(size=14, family="Arial Bold", color="black")
        axis_title_font = dict(size=16, family="Arial Bold", color="black")

        fig.update_layout(
            title=f"{country} Yield Curve (All Maturities)",
            xaxis=dict(title="Maturity", tickfont=axis_tickfont, linecolor='black', linewidth=2, showline=True,
                       title_font=axis_title_font),
            yaxis=dict(title="Yield (%)", tickfont=axis_tickfont, title_font=axis_title_font,
                       linecolor='black', linewidth=2, showline=True),
            template="plotly_white",
            font=dict(color="black"),
            legend=dict(x=0.01, y=1.1, orientation="h"),
            height=500,
            hoverlabel=dict(bgcolor="#F9F9F9")
        )

        st.plotly_chart(fig, use_container_width=True,
                        config={"displayModeBar": True, "displaylogo": False,
                                "modeBarButtonsToAdd": ["toImage", "resetScale2d", "zoom2d", "pan2d"],
                                "modeBarButtonsToRemove": ["lasso2d", "select2d"]})


# -------- USA Economic Cycle Tab (Professional Upgrade) --------
if page == "Cycle":
    # --- Centered Header + Black Text ---
    st.markdown("""
    <div style="text-align:center; font-size:30px; font-weight:700; color:#000000; margin-bottom:20px;">
        US Economic Cycle
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="color:#000000; font-size:16px; line-height:1.6; text-align:justify;">
        The <b>US Economic Cycle</b> assesses the current phase of the US economy using real-time data.  
        It aggregates key indicators across <b>growth (GDP, PMI)</b>, <b>inflation (CPI level & trend)</b>, 
        <b>labor markets (unemployment, NFP)</b>, and <b>financial conditions (yield curve)</b>, assigning each 
        a positive or negative score based on its level and trend.
        <br><br>
        • <b>Spring (Recovery):</b> Early rebound with improving growth and labor conditions; inflation remains contained. (+1.0 to +2.9)<br>
        • <b>Summer (Expansion):</b> Broad economic strength; output, employment, and demand are robust, often with rising inflation. (≥ +3.0)<br>
        • <b>Fall (Slowdown):</b> Growth momentum slows, hiring softens, inflation remains elevated; policy conditions may ease. (−1.0 to +0.9)<br>
        • <b>Winter (Contraction):</b> Economic activity contracts; unemployment rises, inflation moderates, and risk sentiment weakens. (≤ −1.1)
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<hr class='hr-separator'/>", unsafe_allow_html=True)
    
    from openai import OpenAI
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])


    # ---- Helper: Analyze a series ----
    def analyze_series(df, window=4):
        if df is None or df.empty:
            return {"latest_value": None, "trend_slope": 0}
        df = df.dropna(subset=["value"])
        latest_value = df["value"].iloc[-1]
        slope = 0
        if len(df) >= window:
            recent = df.tail(window)
            slope = np.polyfit(np.arange(len(recent)), recent["value"], 1)[0]
        return {"latest_value": latest_value, "trend_slope": slope}

    # ---- USA Cycle Classifier ----
    def classify_usa_cycle():
        # --- Load data ---
        gdp = analyze_series(get_usa_gdp_qoq_data())
        cpi = analyze_series(get_usa_cpi_yoy_data())
        unemp = analyze_series(get_usa_unemployment_rate_data())
        nfp = analyze_series(get_usa_nfp_data())
        pmi = analyze_series(get_usa_ism_manufacturing_pmi_data())
        yc_2y = analyze_series(get_usa_2yr_yield_data())
        yc_10y = analyze_series(get_usa_10yr_yield_data())

        # --- Compute derived metrics ---
        gdp_change = get_usa_gdp_qoq_data().tail(4)["value"].diff().sum()
        cpi_val = cpi["latest_value"]
        cpi_slope = cpi["trend_slope"]
        unemp_val = unemp["latest_value"]
        unemp_slope = unemp["trend_slope"]
        nfp_avg = get_usa_nfp_data().tail(4)["value"].mean()
        pmi_val = pmi["latest_value"]
        pmi_slope = pmi["trend_slope"]
        yc_spread = yc_10y["latest_value"] - yc_2y["latest_value"] if yc_10y["latest_value"] and yc_2y["latest_value"] else None

        # --- Scoring & details ---
        details, scores = {}, {}

        # GDP
        scores["GDP Trend"] = 1 if gdp_change > 0 else -1
        details["GDP Trend"] = ("Improving" if scores["GDP Trend"] > 0 else "Weakening", scores["GDP Trend"])

        # CPI Level & Trend
        scores["CPI Level"] = 1 if cpi_val > 4 else -1 if cpi_val < 1.5 else 0
        details["CPI Level"] = (f"{cpi_val:.1f}%" + (" (High)" if scores["CPI Level"] > 0 else " (Low)" if scores["CPI Level"] < 0 else ""), scores["CPI Level"])
        scores["CPI Trend"] = 1 if cpi_slope > 0 else -1 if cpi_slope < 0 else 0
        details["CPI Trend"] = ("Rising" if scores["CPI Trend"] > 0 else "Falling" if scores["CPI Trend"] < 0 else "Flat", scores["CPI Trend"])

        # Labor
        if unemp_val:
            if unemp_slope > 0.02:
                scores["Unemployment"] = -1
                details["Unemployment"] = (f"{unemp_val:.1f}% (Rising)", -1)
            elif unemp_val < 4 and unemp_slope <= 0:
                scores["Unemployment"] = 1
                details["Unemployment"] = (f"{unemp_val:.1f}% (Stable)", 1)
            else:
                scores["Unemployment"] = 0
                details["Unemployment"] = (f"{unemp_val:.1f}% (Neutral)", 0)
        scores["NFP Avg"] = 1 if nfp_avg > 200 else -1 if nfp_avg < 50 else 0
        details["NFP Avg"] = (f"{nfp_avg:.0f}k" + (" (Strong)" if scores["NFP Avg"] > 0 else " (Weak)" if scores["NFP Avg"] < 0 else ""), scores["NFP Avg"])

        # PMI
        scores["PMI"] = 1 if pmi_val >= 55 else -1 if pmi_val < 50 else 0
        details["PMI"] = (f"{pmi_val:.1f}" + (" (Strong)" if scores["PMI"] > 0 else " (Weak)" if scores["PMI"] < 0 else ""), scores["PMI"])
        scores["PMI Trend"] = 0.5 if pmi_slope > 0 else -0.5 if pmi_slope < 0 else 0
        details["PMI Trend"] = ("Improving" if pmi_slope > 0 else "Falling" if pmi_slope < 0 else "Flat", scores["PMI Trend"])

        # Yield Curve
        if yc_spread is not None:
            scores["Yield Curve"] = -1 if yc_spread < 0 else 1 if yc_spread > 1 else 0
            details["Yield Curve"] = (f"{yc_spread:.2f}" + (" (Inverted)" if scores["Yield Curve"] < 0 else " (Steep)" if scores["Yield Curve"] > 0 else ""), scores["Yield Curve"])

        # --- Weighted total ---
        weights = {"growth": 1.2, "inflation": 1.0, "labor": 1.3, "financials": 0.8}
        weighted_total = (
            (scores.get("GDP Trend", 0) + scores.get("PMI", 0) + scores.get("PMI Trend", 0)) * weights["growth"] +
            (scores.get("CPI Trend", 0) + scores.get("CPI Level", 0)) * weights["inflation"] +
            (scores.get("Unemployment", 0) + scores.get("NFP Avg", 0)) * weights["labor"] +
            scores.get("Yield Curve", 0) * weights["financials"]
        )

        # --- Classify macro season ---
        def classify_macro_season(score):
            if score <= -1.5: return "❄️ Winter (Recession)"
            elif -1.5 < score <= -0.5: return "Fall (Slowdown)"
            elif -0.5 < score <= 0.5: return "Late Fall (Weak Momentum)"
            elif 0.5 < score <= 1.5: return "Early Spring (Fragile Recovery)"
            elif 1.5 < score <= 2.5: return "Late Spring (Broad Recovery)"
            elif 2.5 < score <= 3.5: return "Early Summer (Expansion)"
            else: return "Late Summer (Peak Growth)"

        season = classify_macro_season(weighted_total)
        return season, details, round(weighted_total, 2)

    # ---- Get current USA position ----
    # ---- Get current USA position ----
    usa_position, details, total_score = classify_usa_cycle()

    st.markdown(f"""
    <div style="text-align:center; margin-bottom:30px;">
        <div style="font-size:22px; font-weight:550; color:#000000;">
            USA Macro Season = {usa_position}
        </div>
    </div>
    """, unsafe_allow_html=True)


    # ---- Professional HTML Table ----
    def render_cycle_html_table(details, total_score):
        html = '<table style="border-collapse: collapse; width:100%; font-family: Arial;">'
        # Header
        html += '<tr>'
        for h in ["Indicator", "Value", "Score"]:
            html += f'<th style="font-weight:bold; border:1px solid black; padding:6px; text-align:center; background-color:#d9d9d9;">{h}</th>'
        html += '</tr>'
        
        # Rows
        for k, (val, scr) in details.items():
            # Determine color
            if scr > 0:
                color = "#b6f0c3"  # green
            elif scr < 0:
                color = "#f7b6b6"  # red
            else:
                color = "#f0f0f0"  # gray
            
            html += '<tr>'
            html += f'<td style="font-weight:bold; border:1px solid black; padding:6px; text-align:center; background-color:#F0F0F0;">{k}</td>'
            html += f'<td style="border:1px solid black; padding:6px; text-align:center; background-color:{color};">{val}</td>'
            html += f'<td style="border:1px solid black; padding:6px; text-align:center; background-color:{color};">{scr:+.2f}</td>'
            html += '</tr>'
        
        # Total row
        if total_score > 0:
            total_color = "#b6f0c3"
        elif total_score < 0:
            total_color = "#f7b6b6"
        else:
            total_color = "#f0f0f0"
        
        html += '<tr>'
        html += f'<td colspan="2" style="font-weight:bold; border:1px solid black; padding:6px; text-align:center; background-color:#d9d9d9;">TOTAL</td>'
        html += f'<td style="font-weight:bold; border:1px solid black; padding:6px; text-align:center; background-color:{total_color};">{total_score:+.2f}</td>'
        html += '</tr>'
        
        html += '</table>'
        return html

    # Display table
    st.markdown(render_cycle_html_table(details, total_score), unsafe_allow_html=True)
    st.markdown("<hr class='hr-separator'/>", unsafe_allow_html=True)


 
    # ---- Wave-style Cycle Chart ----
    def build_cycle_wave(phase):
        import numpy as np
        import plotly.graph_objects as go

        # Base sine wave
        x = np.linspace(0, 2 * np.pi, 400)
        y = np.sin(x)

        # --- Figure ---
        fig = go.Figure()

        # --- Season background bands ---
        seasons = [
            {"name": "Spring", "x0": 0, "x1": np.pi/2, "color": "rgba(144,238,144,0.18)"},
            {"name": "Summer", "x0": np.pi/2, "x1": np.pi, "color": "rgba(255,215,0,0.18)"},
            {"name": "Fall",   "x0": np.pi, "x1": 3*np.pi/2, "color": "rgba(255,165,0,0.15)"},
            {"name": "Winter", "x0": 3*np.pi/2, "x1": 2*np.pi, "color": "rgba(173,216,230,0.18)"}
        ]

        # Draw season backgrounds + text + vertical dotted lines
        for s in seasons:
            fig.add_vrect(
                x0=s["x0"], x1=s["x1"],
                fillcolor=s["color"], opacity=0.5, line_width=0
            )
            # Add centered bold season text
            fig.add_annotation(
                x=(s["x0"] + s["x1"]) / 2,
                y=1.25,
                text=f"<b>{s['name']}</b>",
                showarrow=False,
                font=dict(size=16, color="rgba(0,0,0,0.65)")
            )

            # Add vertical dotted divider line (except before first season)
            if s["x0"] != 0:
                fig.add_shape(
                    type="line",
                    x0=s["x0"], x1=s["x0"],
                    y0=-1.2, y1=1.2,
                    line=dict(color="black", width=0.5, dash="dot")
                )

        # --- Add dotted horizontal 0-line manually ---
        fig.add_shape(
            type="line",
            x0=0, x1=2*np.pi,
            y0=0, y1=0,
            line=dict(color="black", width=1)
        )

        # --- Wave line (thinner) ---
        fig.add_trace(go.Scatter(
            x=x, y=y,
            mode="lines",
            line=dict(color="black", width=2),
            hoverinfo="none"
        ))

        # --- Phase position marker ---
        mapping = {
            "Early Spring (Fragile Recovery)": np.pi/4,
            "Late Spring (Broad Recovery)": np.pi/3,
            "Early Summer (Expansion)": 3*np.pi/4,
            "Late Summer (Peak Growth)": np.pi,
            "Fall (Slowdown)": 5*np.pi/4,
            "Late Fall (Weak Momentum)": 3*np.pi/2 - 0.4,
            "Winter (Recession)": 7*np.pi/4
        }
        xpos = mapping.get(phase, 0)
        ypos = np.sin(xpos)

        fig.add_trace(go.Scatter(
            x=[xpos], y=[ypos],
            mode="markers+text",
            text=["<b>USA</b>"],
            textposition="top center",
            textfont=dict(color="black", size=14),
            marker=dict(
                size=18,
                color="red",
                line=dict(color="black", width=2),
                symbol="circle"
            ),
            hoverinfo="none"
        ))

        # --- Layout styling ---
        fig.update_layout(
            title=dict(
                text="<b>US Economic Cycle</b>",
                x=0.5, xanchor="center", font=dict(size=20)
            ),
            xaxis=dict(
                visible=False,
                showline=True,
                linewidth=3,
                linecolor="black",
                mirror=True
            ),
            yaxis=dict(
                visible=False,
                showline=True,
                linewidth=3,
                linecolor="black",
                mirror=True
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=500,
            margin=dict(l=40, r=40, t=60, b=40),
            showlegend=False
        )

        # --- Border around chart ---
        fig.add_shape(
            type="rect",
            x0=0, x1=2*np.pi,
            y0=-1.5, y1=1.5,
            line=dict(color="black", width=3)
        )

        return fig


    st.plotly_chart(build_cycle_wave(usa_position), use_container_width=True)
    
    # ----------- Macro Cycle Summary (AI-Generated) -----------

    st.markdown("### US Economic Cycle Summary")

    # Prepare structured data context for LLM
    cycle_data_summary = "\n".join(
        [f"{indicator}: value={val[0]}, score={val[1]:+.1f}" for indicator, val in details.items()]
    )


    prompt = f"""
    You are a senior macroeconomic strategist writing a concise professional summary of the **U.S. economic cycle** 
    based on the following indicators and scores.

    Indicators (Level, Trend, Score):
    {cycle_data_summary}

    The overall cycle score is {total_score:.1f}, classified as **{usa_position}**.

    Write one paragraph (5–7 sentences) describing the current macroeconomic environment of the U.S., 
    interpreting the data holistically.

    Guidelines:
    - Keep it analytical and neutral — like an economist briefing a portfolio manager.
    - Summarize the growth, inflation, labor, and financial conditions implied by the data.
    - Avoid adjectives like “strong” or “weak” unless implied by score/trend.
    - Mention the current phase ({usa_position}) naturally.
    - Use professional, natural English (no lists or bullet points).
    - Output a single paragraph, no headings.
    """

    @st.cache_data(ttl=3600)
    def generate_cycle_summary():
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=250,
                temperature=0.2
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"⚠️ LLM generation failed: {e}"

    # Generate and display
    with st.spinner("Generating cycle summary..."):
        cycle_summary_text = generate_cycle_summary()
        
        # Add Cycle summary to global collector
        summary_label = f"Cycle Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{cycle_summary_text}"

        # Prevent duplicates (so it doesn’t re-add every rerun)
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)

    st.markdown(f"""
    <div style="
        background-color:#f8f9fa;
        border-left:6px solid #1d3557;
        border-radius:10px;
        padding:18px 24px;
        margin-top:10px;
        font-size:15px;
        font-family:'Inter','Segoe UI','Arial',sans-serif;
        line-height:1.6;
        color:#111;
    ">
    {cycle_summary_text}
    </div>
    """, unsafe_allow_html=True)

    
    
# -------- Macro Reports Tab --------
if page == "Reports":
    import os
    import base64
    from pathlib import Path

    # --- Title ---
    st.markdown("""
    <div style="text-align:center; font-size:32px; font-weight:800; color:#000000; margin-bottom:10px;">
        Macro Reports
    </div>
    """, unsafe_allow_html=True)

    # --- Intro text ---
    st.markdown("""
    <div style="color:#000000; font-size:16px; line-height:1.6; text-align:justify; margin-bottom:15px;">
        Welcome to the <b>Macro Lens Research Reports</b> section — a growing archive of weekly macroeconomic insights.
        Each report explores key developments in growth, inflation, financial markets, and global policy shifts,
        helping readers understand the forces shaping economies and investor sentiment worldwide.
        Select a report from the left to view it in full on the right.
    </div>
    """, unsafe_allow_html=True)

    # --- Reports folder setup ---
    reports_folder = Path("reports")
    pdf_files = sorted([f for f in reports_folder.glob("*.pdf")], reverse=True)

    if not pdf_files:
        st.info("No reports found yet. Add PDFs to the `reports/` folder.")
    else:
        # Adjust column width ratio (more space for the report)
        col1, col2 = st.columns([0.7, 1.5])

        # --- Custom button styling ---
        st.markdown("""
        <style>
        div.stButton > button {
            border-radius: 10px;
            border: 2px solid #cccccc;
            background-color: #ffffff;
            color: #000000;
            padding: 10px 18px;
            margin-bottom: 8px;
            font-size: 17px;
            font-weight: 700;
            text-align: center;
            transition: all 0.15s ease-in-out;
        }
        div.stButton > button:hover {
            border-color: #0072ff;
            color: #0072ff;
            background-color: #f9fbff;
            transform: scale(1.01);
        }
        div.stButton > button:focus:not(:active) {
            border-color: #0072ff;
            color: #0072ff;
            background-color: #f9fbff;
            transform: scale(1.01);
        }
        </style>
        """, unsafe_allow_html=True)

        # --- Month name map ---
        month_map = {
            "01": "January", "02": "February", "03": "March", "04": "April",
            "05": "May", "06": "June", "07": "July", "08": "August",
            "09": "September", "10": "October", "11": "November", "12": "December"
        }

        # --- Build report button list ---
        report_buttons = []
        for pdf_path in pdf_files:
            file_name = pdf_path.name.replace(".pdf", "")
            parts = file_name.split("_")[0].split("-")

            if len(parts) == 3:
                year, month, day = parts
                month_name = month_map.get(month, month)
                display_name = f"{month_name} {int(day)}, {year} Report"
            else:
                year, month = parts
                month_name = month_map.get(month, month)
                display_name = f"{month_name} {year} Report"

            report_buttons.append((display_name, pdf_path))

        # --- Default selection ---
        if "selected_report" not in st.session_state:
            st.session_state.selected_report = report_buttons[0][1]

        # --- Left column (buttons) ---
        with col1:
            st.markdown("### Weekly Reports")

            for display_name, pdf_path in report_buttons:
                is_selected = pdf_path == st.session_state.selected_report
                if is_selected:
                    st.markdown(
                        f"""
                        <div style="
                            border:2px solid #0072ff;
                            border-radius:10px;
                            padding:12px 18px;
                            margin-bottom:8px;
                            font-size:17px;
                            font-weight:700;
                            color:#0072ff;
                            background-color:#f9fbff;
                            text-align:center;
                        ">
                            {display_name}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    if st.button(display_name, use_container_width=True, key=display_name):
                        st.session_state.selected_report = pdf_path

        # --- Right column (PDF viewer) ---
        selected_pdf = st.session_state.selected_report
        with open(selected_pdf, "rb") as f:
            pdf_bytes = f.read()
        pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_data_uri = f"data:application/pdf;base64,{pdf_base64}"

        file_name = selected_pdf.name.replace(".pdf", "")
        parts = file_name.split("_")[0].split("-")
        if len(parts) == 3:
            year, month, day = parts
            month_name = month_map.get(month, month)
            display_title = f"{month_name} {int(day)}, {year} Report"
        else:
            year, month = parts
            month_name = month_map.get(month, month)
            display_title = f"{month_name} {year} Report"

        with col2:
            st.markdown(f"### 📈 {display_title}", unsafe_allow_html=True)
            st.download_button(
                label="⬇️ Download PDF",
                data=pdf_bytes,
                file_name=selected_pdf.name,
                mime="application/pdf",
            )

            st.markdown(
                f'<iframe src="{pdf_data_uri}" width="100%" height="450px" '
                f'style="border:none; margin-top:-10px; border-radius:10px; transform:scale(0.98); '
                f'transform-origin:top center;"></iframe>',
                unsafe_allow_html=True
            )

    # --- Footer ---
    st.markdown("""
    <div style="text-align:center; margin-top:35px; font-size:14px; color:#666;">
        © 2025 Macro Lens Research | Weekly Global Macro Insights
    </div>
    """, unsafe_allow_html=True)



# -------- Scenario Testing (Professional Edition) --------
if page == "Scenarios":

    st.markdown("""
    <div style="text-align:center; font-size:30px; font-weight:700; color:#000; margin-bottom:12px;">
        Scenario Testing — Daily Move Triggers
    </div>
    <div style="text-align:center; color:#444; margin-bottom:18px;">
        Highlight every day the asset’s daily move exceeded a selected % (colored markers). Analyze forward returns after custom periods.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.8, 5])

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

    # --- Reverse map for dropdown ---
    dropdown_map = {v: k for k, v in display_names.items()}

    with col1:
        st.markdown("<div style='margin-top:40px;'>", unsafe_allow_html=True)

        # --- Asset selection ---
        asset_map = {
            "FX": ["eurusd","gbpusd","usdjpy","dxy"],
            "Equities": ["eq_sp500","eq_nasdaq","eq_dow","eq_ftse","eq_nikkei","eq_dax","eq_msci_em","eq_vix"],
            "Stocks": ["st_aapl","st_amzn","st_meta","st_googl","st_nvda","st_msft","st_tsla"],
            "Commodities": ["cmd_gold","cmd_silver","cmd_wti","cmd_brent","cmd_ng","cmd_wheat","cmd_copper","cmd_corn","cmd_soy"],
            "Crypto": ["crypto_btc","crypto_eth"]
        }

        group = st.selectbox("Select Category", list(asset_map.keys()), index=1)

        # display names in dropdown
        asset_names_for_dropdown = [display_names.get(a, a) for a in asset_map[group]]
        selected_name = st.selectbox("Select Asset", asset_names_for_dropdown)

        # convert back to code for data
        code = dropdown_map.get(selected_name, selected_name)

        # --- User inputs ---
        direction = st.selectbox("Direction", ["Up", "Down"], index=0)
        threshold = st.number_input("Daily % Move Threshold", min_value=0.1, max_value=100.0, value=5.0, step=0.1)
        forward_unit = st.selectbox("Forward Unit", ["days","weeks","months","years"], index=0)
        forward_period = st.number_input(f"Forward Period ({forward_unit})", min_value=1, max_value=3650, value=30)

        # --- Load data ---
        df = load_indicator_data(code)
        if df.empty:
            st.error("No data available for this asset.")
            st.stop()

        df = df.rename(columns={c.lower(): c for c in df.columns})
        if 'date' not in df.columns:
            df = df.reset_index().rename(columns={'index':'date'})
        if 'adj close' in df.columns:
            df['value'] = df['adj close']
        elif 'close' in df.columns:
            df['value'] = df['close']
        elif 'value' not in df.columns:
            st.error("Data format not recognized.")
            st.stop()

        df = df[['date','value']].dropna()
        df['date'] = pd.to_datetime(df['date'])

        # --- Date range setup ---
        earliest_date = df['date'].min().date()
        latest_date = df['date'].max().date()
        timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"], index=3)

        if timeframe != "MAX":
            years = int(timeframe.replace("Y", ""))
            default_start_date = max(earliest_date, latest_date - dt.timedelta(days=365 * years))
        else:
            default_start_date = earliest_date

        date_col1, date_col2 = st.columns(2)
        with date_col1:
            start_date = st.date_input("Start Date", default_start_date, min_value=earliest_date, max_value=latest_date)
        with date_col2:
            end_date = st.date_input("End Date", latest_date, min_value=earliest_date, max_value=latest_date)

        if start_date > end_date:
            st.warning("⚠️ Start date cannot be after end date.")
            st.stop()

        df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))].reset_index(drop=True)

    with col2:
        # --- Compute daily % changes and triggers ---
        df['pct_change'] = df['value'].pct_change() * 100
        if direction == "Up":
            df['is_trigger'] = df['pct_change'] >= threshold
        else:
            df['is_trigger'] = df['pct_change'] <= -threshold

        triggers = df[df['is_trigger']].copy().reset_index().rename(columns={'index':'df_index'})

        ticker_display = display_names.get(code, code)

        # --- Plotly chart (highlight triggers) ---
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['value'],
            mode='lines', line=dict(color='#1f77b4', width=2),
            name=code.upper()
        ))

        fig.add_trace(go.Scatter(
            x=triggers['date'], y=triggers['value'],
            mode='markers',
            marker=dict(color='orange', size=8, line=dict(color='black', width=1)),
            customdata=triggers['pct_change'],
            hovertemplate="<b>Date:</b> %{x|%d %b %Y}<br><b>Value:</b> %{y:,.2f}<br><b>Move:</b> %{customdata:+.2f}%<extra></extra>",
            name="Trigger"
        ))

        fig.update_layout(
            title=dict(
                text=f"<b>{ticker_display}</b>",
                x=0.5,
                xanchor='center',
                y=0.95,  # moved up
                yanchor='top',
                font=dict(size=22, family="Inter, Arial Black", color="#000"),
            ),
            margin=dict(l=40, r=30, t=80, b=40),  # increased top margin
            xaxis=dict(showline=True, linecolor='black', showgrid=False),
            yaxis=dict(showline=True, linecolor='black', gridcolor='LightGrey', gridwidth=0.4, tickformat=',.2f'),
            plot_bgcolor='white',
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            font=dict(family="Inter, Arial", color="#000")
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- Forward outcome calculations ---
        results = []
        for _, tr in triggers.iterrows():
            trigger_date = tr['date']
            start_val = tr['value']
            daily_move = tr['pct_change']

            # Compute forward date
            if forward_unit == 'days':
                target = trigger_date + pd.Timedelta(days=forward_period)
            elif forward_unit == 'weeks':
                target = trigger_date + pd.Timedelta(weeks=forward_period)
            elif forward_unit == 'months':
                target = trigger_date + pd.DateOffset(months=forward_period)
            elif forward_unit == 'years':
                target = trigger_date + pd.DateOffset(years=forward_period)
            else:
                target = trigger_date

            next_row = df[df['date'] >= target].head(1)
            if not next_row.empty:
                end_val = float(next_row['value'].iloc[0])
                forward_ret = (end_val / start_val - 1) * 100
                forward_date = next_row['date'].iloc[0].date()
            else:
                end_val, forward_ret, forward_date = np.nan, np.nan, ""

            results.append({
                "Trigger Date": trigger_date.date(),
                "Daily Move (%)": round(daily_move, 2),
                "Start Value": round(start_val, 2),
                f"End Value (after {forward_period} {forward_unit})": (round(end_val, 2) if not np.isnan(end_val) else ""),
                "Forward Return (%)": (round(forward_ret, 2) if not np.isnan(forward_ret) else ""),
                "Forward Date Used": forward_date
            })

        results_df = pd.DataFrame(results)

        # --- Summary Stats ---
        if "Forward Return (%)" in results_df.columns and not results_df.empty:
            valid_forward = pd.to_numeric(results_df["Forward Return (%)"], errors='coerce').dropna()
            count_triggers = len(results_df)
            mean_forward = valid_forward.mean() if not valid_forward.empty else np.nan
        else:
            valid_forward = pd.Series(dtype=float)
            count_triggers = len(results_df)
            mean_forward = np.nan

        st.markdown("<h4 style='margin-top:18px;'>Trigger Outcomes</h4>", unsafe_allow_html=True)

        def render_scenario_html_table(df_results, total_count, mean_forward_val):
            header_bg = "#d9d9d9"
            html = '<table style="border-collapse: collapse; width:100%; font-family: Inter, Arial; font-size:14px;">'
            html += '<thead><tr>'
            for col in df_results.columns:
                html += f'<th style="font-weight:700; border:1px solid #ddd; padding:8px; text-align:center; background-color:{header_bg};">{col}</th>'
            html += '</tr></thead><tbody>'
            for _, row in df_results.iterrows():
                html += '<tr>'
                for col in df_results.columns:
                    val = row[col]
                    if col == "Forward Return (%)":
                        if val == "":
                            html += "<td style='border:1px solid #ddd; padding:8px; background-color:#f0f0f0;'></td>"
                        else:
                            color = "#b6f0c3" if float(val) > 0 else "#f7b6b6" if float(val) < 0 else "#f0f0f0"
                            html += f"<td style='border:1px solid #ddd; padding:8px; text-align:center; background-color:{color};'>{float(val):+.2f}%</td>"
                    elif col == "Daily Move (%)":
                        html += f"<td style='border:1px solid #ddd; text-align:center;'>{float(val):+.2f}%</td>"
                    else:
                        html += f"<td style='border:1px solid #ddd; text-align:center;'>{val}</td>"
                html += '</tr>'
            html += '</tbody>'
            html += f"<tfoot><tr><td colspan='{len(df_results.columns)-2}' style='padding:8px; font-weight:700; background-color:#f8f8f8;'>Count: {total_count} | Mean Forward Return:</td>"
            mean_disp = f"{mean_forward_val:+.2f}%" if not np.isnan(mean_forward_val) else "N/A"
            html += f"<td colspan='2' style='padding:8px; text-align:center; font-weight:700; background-color:#f8f8f8;'>{mean_disp}</td></tr></tfoot></table>"
            return html

        if results_df.empty:
            st.info("No triggers found for this range or threshold.")
        else:
            # --- Scrollable trigger outcomes table container ---
            st.markdown("""
            <style>
            .trigger-table-container {
                max-height: 350px;          /* Controls scroll area height */
                overflow-y: auto;           /* Enables vertical scrolling */
                overflow-x: hidden;         /* Optional: hide horizontal scroll */
                border: 1px solid #ddd;     /* Subtle border */
                border-radius: 8px;
                padding: 4px;
                background-color: #fafafa;  /* Soft background */
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            }
            .trigger-table-container::-webkit-scrollbar {
                width: 6px;
            }
            .trigger-table-container::-webkit-scrollbar-thumb {
                background-color: #bbb;
                border-radius: 3px;
            }
            .trigger-table-container::-webkit-scrollbar-thumb:hover {
                background-color: #999;
            }
            </style>
            """, unsafe_allow_html=True)

            st.markdown(
                f"""
                <div class="trigger-table-container">
                    {render_scenario_html_table(results_df, count_triggers, mean_forward)}
                </div>
                """,
                unsafe_allow_html=True
            )

       
               # ----------- AI Summary for Scenario Testing (Auto Refresh) -----------

        if not results_df.empty:
            st.markdown("<hr class='hr-separator'/>", unsafe_allow_html=True)
            st.markdown("### Scenario Summary")

            from openai import OpenAI
            client = OpenAI(api_key=st.secrets["openai"]["api_key"])

            # --- Summarize the scenario results for AI context ---
            scenario_summary_data = "\n".join([
                f"Trigger on {row['Trigger Date']}: daily move {row['Daily Move (%)']:+.2f}%, "
                f"forward return {row['Forward Return (%)']}% after {forward_period} {forward_unit}"
                for _, row in results_df.iterrows()
                if row['Forward Return (%)'] != ""
            ])

            ticker_display = display_names.get(code, code)

            prompt = f"""
            You are a professional macro and market strategist writing a concise report-style summary
            of a scenario test.

            Asset: {ticker_display}
            Direction tested: {direction} moves beyond {threshold}%
            Forward horizon: {forward_period} {forward_unit}
            Number of triggers: {count_triggers}
            Average forward return: {mean_forward:+.2f}%

            Historical trigger outcomes:
            {scenario_summary_data}

            Write a single paragraph (4–6 sentences) that:
            - Describes how this asset tends to behave after similar daily {direction.lower()} moves.
            - Explains whether these events usually lead to trend continuation or mean reversion.
            - Comments briefly on the statistical strength or limitations of the findings.
            - Keeps the tone professional, objective, and suitable for an institutional macro research dashboard.
            - Do not use bullet points or markdown formatting — write one cohesive paragraph.
            """

            # --- Cache summary with parameter dependencies ---
            @st.cache_data(ttl=3600, show_spinner=False)
            def generate_scenario_summary(asset, direction, threshold, forward_period, forward_unit, data_text):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}],
                        max_completion_tokens=250,
                        temperature=0.25
                    )
                    return response.choices[0].message.content.strip()
                except Exception as e:
                    return f"⚠️ AI summary generation failed: {e}"

            with st.spinner("Generating AI summary..."):
                scenario_summary_text = generate_scenario_summary(
                    code,
                    direction,
                    threshold,
                    forward_period,
                    forward_unit,
                    scenario_summary_data
                )
                
                # Add Scenario summary to global collector
                summary_label = f"Scenario Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
                entry = f"{summary_label}:\n{scenario_summary_text}"

                # Prevent duplicates (so it doesn’t re-add every rerun)
                if entry not in st.session_state["ai_summaries"]:
                    st.session_state["ai_summaries"].append(entry)

            # --- Styled display ---
            st.markdown(f"""
            <div style="
                background-color:#f8f9fa;
                border-left:6px solid #1d3557;
                border-radius:10px;
                padding:18px 24px;
                margin-top:10px;
                font-size:15px;
                font-family:'Inter','Segoe UI','Arial',sans-serif;
                line-height:1.6;
                color:#111;
            ">
            {scenario_summary_text}
            </div>
            """, unsafe_allow_html=True)


# -------- Seasonality Tab --------
if page == "Seasonality":
    st.markdown("""
    <div style="text-align:center; font-size:30px; font-weight:700; color:#000; margin-bottom:12px;">
        Seasonality Analysis
    </div>
    <div style="text-align:center; color:#444; margin-bottom:18px;">
        Compare a given asset's YTD monthly returns vs its historical average for a selected timeframe.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 5])

    # --- Asset categories & mapping ---
    asset_map = {
        "FX": ["eurusd","gbpusd","usdjpy","dxy"],
        "Equities": ["eq_sp500","eq_nasdaq","eq_dow","eq_ftse","eq_nikkei","eq_dax","eq_msci_em","eq_vix"],
        "Stocks": ["st_aapl","st_amzn","st_meta","st_googl","st_nvda","st_msft","st_tsla"],
        "Commodities": ["cmd_gold","cmd_silver","cmd_wti","cmd_brent","cmd_ng","cmd_wheat","cmd_copper","cmd_corn","cmd_soy"],
        "Crypto": ["crypto_btc","crypto_eth"]
    }

    display_names = {
        "eurusd": "EUR/USD", "gbpusd": "GBP/USD", "usdjpy": "USD/JPY", "dxy": "US Dollar Index (DXY)",
        "eq_sp500": "S&P 500", "eq_nasdaq": "Nasdaq 100", "eq_dow": "Dow Jones Industrial", "eq_ftse": "FTSE 100",
        "eq_nikkei": "Nikkei 225", "eq_dax": "DAX", "eq_msci_em": "MSCI Emerging Markets", "eq_vix": "VIX",
        "st_aapl": "Apple", "st_amzn": "Amazon", "st_meta": "Meta", "st_googl": "Google", "st_nvda": "Nvidia",
        "st_msft": "Microsoft", "st_tsla": "Tesla",
        "cmd_gold": "Gold", "cmd_silver": "Silver", "cmd_wti": "WTI Crude", "cmd_brent": "Brent Crude", "cmd_ng": "Natural Gas",
        "cmd_wheat": "Wheat", "cmd_copper": "Copper", "cmd_corn": "Corn", "cmd_soy": "Soy",
        "crypto_btc": "Bitcoin", "crypto_eth": "Ethereum"
    }

    dropdown_map = {v: k for k, v in display_names.items()}

    with col1:
        cat1 = st.selectbox("Select Category", list(asset_map.keys()), index=1)
        cat2_options = asset_map[cat1]
        cat2 = st.selectbox("Select Asset", [display_names[a] for a in cat2_options])
        code = dropdown_map.get(cat2, cat2)

        timeframe = st.selectbox("Select Timeframe", ["1Y","3Y","5Y","10Y","MAX"], index=3)

        if timeframe != "MAX":
            years = int(timeframe.replace("Y",""))
            end_date = pd.Timestamp.today().date()
            start_date = end_date - pd.DateOffset(years=years)
        else:
            df_temp = load_indicator_data(code)
            start_date = df_temp['date'].min().date()
            end_date = df_temp['date'].max().date()

        d1, d2 = st.columns(2)
        with d1:
            start_date = st.date_input("Start Date", start_date, min_value=start_date, max_value=end_date)
        with d2:
            end_date = st.date_input("End Date", end_date, min_value=start_date, max_value=end_date)

        # --- Chart type selection ---
        c1, c2 = st.columns(2)
        with c1:
            avg_chart_type = st.selectbox("Historical Avg Chart", ["Line", "Bar"], index=0)
        with c2:
            ytd_chart_type = st.selectbox("YTD Chart", ["Bar", "Line"], index=0)

    # --- Load & prep data ---
    df = load_indicator_data(code)
    if df.empty:
        st.error("No data available for this asset.")
        st.stop()

    df['date'] = pd.to_datetime(df['date'])
    df['value'] = df.get('adj close', df.get('close', df.get('value', np.nan)))
    df = df[['date','value']].dropna()
    df = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))].reset_index(drop=True)

    def calc_monthly_returns(df):
        df = df.copy()
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        monthly = []
        for (y, m), g in df.groupby(['year','month']):
            g = g.sort_values('date')
            if len(g) > 1 and g['value'].iloc[0] != 0:
                ret = ((g['value'].iloc[-1] / g['value'].iloc[0]) - 1) * 100
                monthly.append({'year': y, 'month': m, 'return': ret})
        return pd.DataFrame(monthly)

    monthly_df = calc_monthly_returns(df)
    avg_df = monthly_df.groupby('month')['return'].mean().reset_index().rename(columns={'return':'avg_return'})
    current_year = pd.Timestamp.today().year
    # Exclude the current (incomplete) month from YTD data
    current_year = pd.Timestamp.today().year
    current_month = pd.Timestamp.today().month

    ytd_df = monthly_df[
        (monthly_df['year'] == current_year) &
        (monthly_df['month'] < current_month)
    ][['month', 'return']].rename(columns={'return': 'ytd_return'})


    chart_df = pd.DataFrame({'month':range(1,13)})
    chart_df = chart_df.merge(avg_df, on='month', how='left').merge(ytd_df, on='month', how='left')
    chart_df['month_name'] = chart_df['month'].apply(lambda x: pd.Timestamp(2000, x, 1).strftime('%b'))

    # --- Plotly chart ---
    import plotly.graph_objects as go
    fig = go.Figure()

    # Historical Average
    if avg_chart_type == "Line":
        fig.add_trace(go.Scatter(
            x=chart_df['month_name'],
            y=chart_df['avg_return'].round(1),
            name='Historical Average',
            mode='lines+markers+text',
            line=dict(color='#ffb703', width=3, dash='dot'),
            # 💫 Yellow markers with subtle black outline
            marker=dict(size=8, color='#ffb703', line=dict(color='black', width=0.8)),
            text=[f"{v:.1f}%" if not pd.isna(v) else "" for v in chart_df['avg_return']],
            textposition="top center",
            # 🟡 Bold yellow text labels
            textfont=dict(color='#ffb703', size=11, family='Arial', weight='bold'),
            hovertemplate='%{y:.1f}%%<extra></extra>'
        ))
    else:
        fig.add_trace(go.Bar(
            x=chart_df['month_name'],
            y=chart_df['avg_return'].round(1),
            name='Historical Average',
            marker=dict(color='#ffb703', line=dict(color='black', width=1.2)),
            text=[f"{v:.1f}%" if not pd.isna(v) else "" for v in chart_df['avg_return']],
            textposition="outside",
            # 🟡 Bold yellow text labels
            textfont=dict(color='#ffb703', size=11, family='Arial', weight='bold'),
            opacity=0.7,
            hovertemplate='%{y:.1f}%%<extra></extra>'
        ))

    # YTD
    if ytd_chart_type == "Bar":
        fig.add_trace(go.Bar(
            x=chart_df['month_name'],
            y=chart_df['ytd_return'].round(1),
            name=f'YTD {current_year}',
            marker=dict(color='#1f77b4', line=dict(color='black', width=1.2)),
            text=[f"{v:.1f}%" if not pd.isna(v) else "" for v in chart_df['ytd_return']],
            textposition="outside",
            textfont=dict(color='black', size=11, family='Arial', weight='bold'),
            hovertemplate='%{y:.1f}%%<extra></extra>'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=chart_df['month_name'],
            y=chart_df['ytd_return'].round(1),
            name=f'YTD {current_year}',
            mode='lines+markers+text',
            line=dict(color='#1f77b4', width=3),
            marker=dict(size=7, color='#1f77b4', line=dict(color='black', width=1)),
            text=[f"{v:.1f}%" if not pd.isna(v) else "" for v in chart_df['ytd_return']],
            textposition="top center",
            textfont=dict(color='#1f77b4', size=11, family='Arial', weight='bold'),
            hovertemplate='%{y:.1f}%%<extra></extra>'
        ))

    # --- Fix bar overlap and ensure labels visible ---
    fig.update_layout(
        barmode='group',  # group bars side by side instead of stacking
        bargap=0.2,       # spacing between groups
        uniformtext_minsize=8,
        uniformtext_mode='hide'
    )

    # --- Layout styling ---
    fig.update_layout(
        title=f"{cat2} - Monthly Seasonality",
        xaxis=dict(
            title=dict(
                text="Month",
                font=dict(color='black', size=13, family='Arial')
            ),
            showgrid=False,
            tickfont=dict(color='black', size=12, family='Arial'),
        ),
        yaxis=dict(
            title=dict(
                text="Return (%)",
                font=dict(color='black', size=13, family='Arial')
            ),
            showgrid=True,
            gridcolor='LightGrey',
            tickfont=dict(color='black', size=12, family='Arial'),
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=520,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        hoverlabel=dict(
            bgcolor='white',
            font=dict(color='black', size=13, family='Arial'),
            bordercolor='black'
        ),
        font=dict(color='black', family='Arial')
    )

    with col2:
        st.plotly_chart(fig, use_container_width=True)

        
        

    # ----------- AI Summary for Seasonality -----------

    st.markdown("<hr class='hr-separator'/>", unsafe_allow_html=True)
    st.markdown("### Seasonality Summary")

    from openai import OpenAI
    client = OpenAI(api_key=st.secrets["openai"]["api_key"])

    # --- Prepare structured context ---
    seasonality_data_summary = "\n".join([
        f"{row['month_name']}: avg_return={row['avg_return']:.2f}%, ytd_return={row['ytd_return'] if not np.isnan(row['ytd_return']) else 'N/A'}%"
        for _, row in chart_df.iterrows()
    ])

    from datetime import datetime
    current_month = datetime.now().month
    current_month_name = datetime.now().strftime("%B")

    prompt = f"""
    You are a financial analyst writing a concise professional summary of a seasonality analysis.

    Asset: {cat2}
    Timeframe: {timeframe}
    Today's date: {datetime.now().strftime('%B %d, %Y')}
    Current month number: {current_month}

    Data summary (monthly average vs YTD returns):
    {seasonality_data_summary}

    Instructions:
    - Compare each completed month’s YTD return against its historical monthly average.
    - Treat months before {current_month_name} as completed.
    - Mention any statistics you think is necessary.
    - Do NOT mention “missing data” for months that have not yet occurred (November and December).
    - Instead, phrase future months as “historically strong/weak” if relevant, but not “lacking data.”
    - September and October should be analyzed if YTD data is available.
    - Keep it one professional paragraph (4–6 sentences).
    - Use an analytical tone suitable for an investment research brief.
    """




    def generate_seasonality_summary():
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=250,
                temperature=0.2
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"⚠️ AI summary generation failed: {e}"

    # --- Generate and display ---
    with st.spinner("Generating summary..."):
        seasonality_summary_text = generate_seasonality_summary()
        
        # Add Seasonality summary to global collector
        summary_label = f"Seasonality Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{seasonality_summary_text}"  # <-- fixed variable name

        # Prevent duplicates
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)


    st.markdown(f"""
    <div style="
        background-color:#f8f9fa;
        border-left:6px solid #1d3557;
        border-radius:10px;
        padding:18px 24px;
        margin-top:10px;
        font-size:15px;
        font-family:'Inter','Segoe UI','Arial',sans-serif;
        line-height:1.6;
        color:#111;
    ">
    {seasonality_summary_text}
    </div>
    """, unsafe_allow_html=True)

import streamlit as st
from openai import OpenAI
import pandas as pd
from copy import deepcopy
import os

# -----------------------------
# Initialize OpenAI client
# -----------------------------
try:
    OPENAI_API_KEY = st.secrets["openai"]["api_key"]
except Exception:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("❌ OpenAI API key not found!")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)

# -----------------------------
# Helper: Generate LLM Summary
# -----------------------------
def generate_country_llm_summary(results: dict, country_name: str) -> str:
    """
    Generate a concise macro summary for a country based on indicator data.
    """
    if not results:
        return f"No data available for {country_name}."

    # Convert to LLM-readable text
    context_text = "\n".join(
        [f"{name}: latest={data['latest']:.2f}%, trend={data['trend']}" 
         for name, data in results.items()]
    )

    prompt = f"""
    You are a senior macro-financial strategist writing a concise, data-driven
    condition of the {country_name} economy. You are given the latest 1-year snapshot
    of various economic indicators.

    Data points:
    {context_text}

    Write one short paragraph (5–7 sentences) summarizing the overall condition
    of the {country_name} economy. Focus on patterns, contrasts, and relative positions.
    Use only the data provided. Keep it professional, concise, and analytical.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=250,
            temperature=0
        )
        summary_text = response.choices[0].message.content.strip()
        if not summary_text:
            summary_text = "⚠️ LLM returned an empty response."
    except Exception as e:
        summary_text = f"⚠️ LLM generation failed: {e}"

    return summary_text

# -----------------------------
# --- Helper Functions for Summaries ---
# -----------------------------
def generate_asset_llm_summary(results, asset_name):
    """
    Calls the existing country summary function but strips any trailing % formatting
    or instructs LLM to avoid percentages in output.
    """
    # Option A: just call it and return text as-is
    summary = generate_country_llm_summary(results, asset_name)

    # Option B (safer): if your summary sometimes adds % values, replace/remove them
    import re
    summary = re.sub(r'(\d+\.?\d*)%', r'\1', summary)

    return summary

def get_country_summary_from_indicator_data(country_name: str, analyze_fn) -> str:
    """
    Uses the analyze function for a country to compute indicator results
    and generate (or fetch cached) summary.
    """
    key_name = f"{country_name.lower()}_macro_summary"

    if key_name not in st.session_state:
        with st.spinner(f"Generating {country_name} market summary..."):
            results = analyze_fn()
            summary = generate_country_llm_summary(results, country_name)
            st.session_state[key_name] = summary
    return st.session_state[key_name]

def get_asset_summary_from_indicator_data(asset_name: str, analyze_fn) -> str:
    key_name = f"{asset_name.lower()}_summary"

    if key_name not in st.session_state:
        with st.spinner(f"Generating {asset_name} summary..."):
            results = analyze_fn()
            summary = generate_asset_llm_summary(results, asset_name)  # <--- updated line
            st.session_state[key_name] = summary
    return st.session_state[key_name]


# -----------------------------
# --- Summary Page ---
# -----------------------------
if page == "Summary":
    # --- Page Title ---
    st.markdown(
        "<h1 style='text-align:center; color:black; font-weight:bold; font-size:32px;'>Global Macro Summary</h1>",
        unsafe_allow_html=True
    )

    st.markdown(
        "<p style='text-align:center; color:black; font-size:16px;'>A concise professional overview of key country and asset class trends to guide market decisions.</p>",
        unsafe_allow_html=True
    )

    # --- 1. Country Summaries ---
    usa_summary = get_country_summary_from_indicator_data("United States", analyze_usa)
    uk_summary = get_country_summary_from_indicator_data("United Kingdom", analyze_uk)
    euro_summary = get_country_summary_from_indicator_data("Euro Area", analyze_euro)
    japan_summary = get_country_summary_from_indicator_data("Japan", analyze_japan)

    combined_country_summaries = f"""
United States:
{usa_summary}

United Kingdom:
{uk_summary}

Euro Area:
{euro_summary}

Japan:
{japan_summary}
    """

    st.markdown("<h3 style='color:black; font-weight:bold;'>Individual Country Summaries</h3>", unsafe_allow_html=True)
    st.text_area("Collected Summaries", combined_country_summaries, height=300)

    # --- 2. Asset Class Summaries ---
    equities_summary = get_asset_summary_from_indicator_data("Equities", analyze_equities)
    stocks_summary = get_asset_summary_from_indicator_data("Stocks", analyze_stocks)
    commodities_summary = get_asset_summary_from_indicator_data("Commodities", analyze_commodities)
    bonds_summary = get_asset_summary_from_indicator_data("Bonds", analyze_bonds)
    fx_summary = get_asset_summary_from_indicator_data("FX", analyze_fx)
    crypto_summary = get_asset_summary_from_indicator_data("Crypto", analyze_crypto)

    combined_asset_summaries = f"""
Equities:
{equities_summary}

Stocks:
{stocks_summary}

Commodities:
{commodities_summary}

Bonds:
{bonds_summary}

FX:
{fx_summary}

Crypto:
{crypto_summary}
    """

    st.markdown("<h3 style='color:black; font-weight:bold;'>Individual Asset Class Summaries</h3>", unsafe_allow_html=True)
    st.text_area("Collected Asset Summaries", combined_asset_summaries, height=300)

    # --- 3. Global Synthesis ---
    synthesis_prompt = f"""
You are a senior global macro strategist. Combine the following regional and asset class summaries
into one unified, professional market commentary. Identify overarching trends,
divergences, risks, and opportunities. Keep it under 3 paragraphs and analytical.

--- Country Summaries ---
{combined_country_summaries}

--- Asset Summaries ---
{combined_asset_summaries}
    """

    with st.spinner("Synthesizing global market summary..."):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": synthesis_prompt}],
            max_completion_tokens=600,
            temperature=0
        )

    global_summary = response.choices[0].message.content.strip()

    st.markdown("<h3 style='color:black; font-weight:bold;'>Global Market Commentary</h3>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="
        background-color:#f8f9fa;
        border-left:6px solid #0a9396;
        border-radius:10px;
        padding:18px 24px;
        margin-top:10px;
        font-size:15px;
        font-family:'Inter','Segoe UI','Arial',sans-serif;
        line-height:1.6;
        color:black;
    ">
    {global_summary}
    </div>
    """, unsafe_allow_html=True)

if page == "Forecasting":
    import streamlit as st
    import pandas as pd
    import numpy as np
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error
    import plotly.graph_objects as go
    from datetime import datetime
    from openai import OpenAI

    st.markdown("""
    <div style="text-align:center; font-size:30px; font-weight:700; color:#000; margin-bottom:12px;">
        Macro Indicator Forecasting
    </div>
    <div style="text-align:center; color:#444; margin-bottom:18px;">
        Forecast macro indicators using related economic data with scenario simulation and AI summary.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2,5])

    # --- 1. Region & Target Selection ---
    regions = ["USA", "UK", "Japan", "Euro"]
    with col1:
        region = st.selectbox("Select Region", regions)

        if region == "USA":
            indicators = ["usa_rate","usa_cpi","usa_core_cpi","usa_gdp","usa_unemp","usa_ahe","usa_core_pce"]
        elif region == "UK":
            indicators = ["uk_rate","uk_cpi","uk_gdp","uk_unemp"]
        elif region == "Japan":
            indicators = ["jp_rate","jp_cpi","jp_gdp","jp_unemp"]
        else:
            indicators = ["eu_rate","eu_cpi","eu_gdp","eu_unemp"]

        target = st.selectbox("Select Target Indicator", indicators)
        lags = st.slider("Number of Lag Months", 1, 6, 3)
        forecast_horizon = st.selectbox("Forecast Horizon", ["1M","3M","6M","12M"], index=1)

    # --- 2. Define indicator relationships ---
    forecast_inputs = {
        "usa_rate": ["usa_cpi", "usa_core_pce", "usa_gdp", "usa_unemp"],
        "usa_cpi": ["usa_rate", "usa_core_ppi", "usa_ahe"],
        "usa_gdp": ["usa_rate", "usa_cpi", "usa_retail", "usa_trade"],
        "usa_unemp": ["usa_gdp", "usa_nfp", "usa_jolts"],

        "uk_rate": ["uk_cpi","uk_gdp","uk_unemp"],
        "uk_cpi": ["uk_rate","uk_gdp"],
        "uk_gdp": ["uk_rate","uk_cpi","uk_unemp"],
        "uk_unemp": ["uk_gdp","uk_rate"],

        "jp_rate": ["jp_cpi","jp_gdp","jp_unemp"],
        "jp_cpi": ["jp_rate","jp_gdp"],
        "jp_gdp": ["jp_rate","jp_cpi","jp_unemp"],
        "jp_unemp": ["jp_gdp","jp_rate"],

        "eu_rate": ["eu_cpi","eu_gdp","eu_unemp"],
        "eu_cpi": ["eu_rate","eu_gdp"],
        "eu_gdp": ["eu_rate","eu_cpi","eu_unemp"],
        "eu_unemp": ["eu_gdp","eu_rate"]
    }

    input_codes = forecast_inputs.get(target, [])

    # --- 3. Prepare lagged dataset with single-column extraction ---
    def extract_series(df):
        if isinstance(df, pd.Series):
            return df.reset_index(drop=True)
        elif isinstance(df, pd.DataFrame):
            for col in ["value","close","adj close"]:
                if col in df.columns:
                    return df[col].reset_index(drop=True)
            return df.iloc[:,0].reset_index(drop=True)  # fallback
        else:
            return pd.Series(df)

    def prepare_data(target, input_codes, lags=3):
        df = pd.DataFrame()
        df[target] = extract_series(load_indicator_data(target))
        for code in input_codes:
            series = extract_series(load_indicator_data(code))
            for lag in range(1,lags+1):
                df[f"{code}_lag{lag}"] = series.shift(lag)
        df.dropna(inplace=True)
        return df

    df = prepare_data(target, input_codes, lags)

    if df.empty:
        st.error("Insufficient data to generate forecast for this target.")
        st.stop()

    X = df.drop(columns=[target])
    y = df[target]

    train_size = int(0.8 * len(df))
    X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
    y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

    # --- 4. Train model ---
    model = Ridge()
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    # --- 5. Metrics ---
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)  # Works for all sklearn versions

    st.write(f"**MAE:** {mae:.3f} | **RMSE:** {rmse:.3f}")

    # --- 6. Forecast vs Actual Plot ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=y_test.index, y=y_test, mode='lines+markers', name='Actual'))
    fig.add_trace(go.Scatter(x=y_test.index, y=y_pred, mode='lines+markers', name='Forecast'))
    fig.update_layout(
        title=f"{target} Forecast vs Actual",
        xaxis_title="Time Index",
        yaxis_title=target,
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=520
    )
    with col2:
        st.plotly_chart(fig, use_container_width=True)

    # --- 7. Next-period forecast / scenario ---
    with col1:
        st.markdown("### Scenario Simulation")
        scenario_inputs = {}
        for code in input_codes:
            last_val = extract_series(load_indicator_data(code)).iloc[-1]
            val = st.number_input(f"{code} Shock (+/-)", value=float(last_val))
            scenario_inputs[code] = val

        if st.button("Forecast Next Period"):
            last_row = X.iloc[-1].copy()
            for code in input_codes:
                for lag in range(1,lags+1):
                    col_name = f"{code}_lag{lag}"
                    last_row[col_name] = scenario_inputs[code]
            next_pred = model.predict(last_row.values.reshape(1,-1))[0]
            st.write(f"Predicted next {target}: **{next_pred:.3f}**")

    # --- 8. AI Summary ---
    st.markdown("<hr class='hr-separator'/>", unsafe_allow_html=True)
    st.markdown("### Forecast Summary")

    client = OpenAI(api_key=st.secrets["openai"]["api_key"])
    forecast_table = "\n".join([f"{i}: Actual={a:.3f}, Forecast={f:.3f}" for i,a,f in zip(y_test.index, y_test, y_pred)])
    prompt = f"""
    You are a financial analyst. Provide a professional summary of the forecast for {target} in {region}.
    Include interpretation of forecast accuracy, recent trends, and implications for the economy.
    Here is the forecast data:
    {forecast_table}
    Keep it concise (4-6 sentences), analytical, and suitable for an investment research brief.
    """

    @st.cache_data(ttl=3600)
    def generate_forecast_summary():
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                max_completion_tokens=250,
                temperature=0.2
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"⚠️ AI summary generation failed: {e}"

    with st.spinner("Generating AI summary..."):
        summary_text = generate_forecast_summary()
        if "ai_summaries" not in st.session_state:
            st.session_state["ai_summaries"] = []
        entry = f"Forecast Summary ({datetime.now().strftime('%Y-%m-%d')}):\n{summary_text}"
        if entry not in st.session_state["ai_summaries"]:
            st.session_state["ai_summaries"].append(entry)

        st.markdown(f"""
        <div style="
            background-color:#f8f9fa;
            border-left:6px solid #1d3557;
            border-radius:10px;
            padding:18px 24px;
            margin-top:10px;
            font-size:15px;
            font-family:'Inter','Segoe UI','Arial',sans-serif;
            line-height:1.6;
            color:#111;
        ">
        {summary_text}
        </div>
        """, unsafe_allow_html=True)

    # --- 9. Download Forecast Table ---
    forecast_df = pd.DataFrame({"Actual": y_test.values, "Forecast": y_pred})
    st.download_button("Download Forecast Data", forecast_df.to_csv(), file_name=f"{target}_forecast.csv")
