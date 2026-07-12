import streamlit as st
import datetime as dt
import pandas as pd
from components.research_page import render_research_page

from data.yahoo import get_fx_data_yahoo
from app_pages.common import calculate_summary_stats
from app_pages.market_utils import (
    filter_by_dates,
    detect_quarterly_data,
    build_market_chart,
    display_market_chart,
)


def get_start_date(df, timeframe):
    end = df["date"].max()

    if timeframe == "1D":
        return end - pd.DateOffset(days=1)
    if timeframe == "1W":
        return end - pd.DateOffset(weeks=1)
    if timeframe == "1M":
        return end - pd.DateOffset(months=1)
    if timeframe == "3M":
        return end - pd.DateOffset(months=3)
    if timeframe == "6M":
        return end - pd.DateOffset(months=6)
    if timeframe == "1Y":
        return end - pd.DateOffset(years=1)
    if timeframe == "3Y":
        return end - pd.DateOffset(years=3)
    if timeframe == "5Y":
        return end - pd.DateOffset(years=5)
    if timeframe == "10Y":
        return end - pd.DateOffset(years=10)

    return df["date"].min()


def pct_change_over(df, label):
    end = df["date"].max()

    offsets = {
        "1D": pd.DateOffset(days=1),
        "1W": pd.DateOffset(weeks=1),
        "1M": pd.DateOffset(months=1),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
    }

    start_date = end - offsets[label]
    past = df[df["date"] <= start_date]

    if past.empty:
        return "—"

    start_val = past["value"].iloc[-1]
    latest_val = df["value"].iloc[-1]

    if start_val == 0:
        return "—"

    change = (latest_val / start_val - 1) * 100
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.2f}%"


def render_stat_tile(label, value):
    st.markdown(
        f"""
        <div class="ml-stat-tile">
            <div class="ml-stat-label">{label}</div>
            <div class="ml-stat-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_commodities_page():
    # -----------------------
    # Indicator setup
    # -----------------------
    commodity_map = {
        "Gold": {
            "ticker": "GC=F",
            "description": "Gold is a safe-haven asset that reacts to inflation expectations, USD strength, interest rates, real yields, and geopolitical uncertainty.",
            "related": ["DXY", "US 10Y Real Yield", "FedWatch", "Silver", "Oil"],
            "drivers": ["Dollar strength", "Real yields", "Fed expectations", "Inflation expectations", "Geopolitical risk"],
        },
        "Crude Oil": {
            "ticker": "CL=F",
            "description": "Crude oil prices reflect global supply and demand dynamics, OPEC production decisions, inventories, and geopolitical risk.",
            "related": ["Brent Oil", "DXY", "Energy equities", "Inflation expectations", "10Y Yield"],
            "drivers": ["Global growth", "OPEC supply", "Inventories", "Geopolitics", "Dollar strength"],
        },
        "Silver": {
            "ticker": "SI=F",
            "description": "Silver acts both as a precious metal and industrial commodity, reacting to real yields, risk appetite, and manufacturing demand.",
            "related": ["Gold", "DXY", "Copper", "Real Yields", "Industrial metals"],
            "drivers": ["Gold trend", "Industrial demand", "Real yields", "Dollar strength", "Risk sentiment"],
        },
        "Copper": {
            "ticker": "HG=F",
            "description": "Copper is a key industrial metal closely linked to global manufacturing, construction, China demand, and the growth cycle.",
            "related": ["China data", "DXY", "Industrial production", "Equities", "Oil"],
            "drivers": ["Global growth", "China demand", "Manufacturing activity", "Supply disruptions", "Dollar strength"],
        },
        "Natural Gas": {
            "ticker": "NG=F",
            "description": "Natural gas prices are sensitive to weather, storage levels, LNG flows, production, and seasonal demand.",
            "related": ["Crude Oil", "Power prices", "Weather", "Inventories", "Energy equities"],
            "drivers": ["Weather", "Storage", "LNG exports", "Production", "Seasonal demand"],
        },
        "Brent Oil": {
            "ticker": "BZ=F",
            "description": "Brent crude is a global oil benchmark influenced by international demand, OPEC policy, supply risk, and geopolitical events.",
            "related": ["Crude Oil", "DXY", "Inflation expectations", "Energy equities", "10Y Yield"],
            "drivers": ["Global demand", "OPEC supply", "Middle East risk", "Inventories", "Dollar strength"],
        },
        "Wheat": {
            "ticker": "ZW=F",
            "description": "Wheat prices respond to weather, crop yields, export policy, global demand, and geopolitical supply disruptions.",
            "related": ["Corn", "Soybeans", "DXY", "Food inflation", "Weather"],
            "drivers": ["Weather", "Crop yields", "Export policy", "Global demand", "Geopolitical supply risk"],
        },
        "Corn": {
            "ticker": "ZC=F",
            "description": "Corn prices are driven by crop conditions, ethanol demand, livestock feed demand, weather, and global trade flows.",
            "related": ["Wheat", "Soybeans", "Ethanol", "DXY", "Weather"],
            "drivers": ["Weather", "Ethanol demand", "Feed demand", "Crop yields", "Trade policy"],
        },
        "Soybeans": {
            "ticker": "ZS=F",
            "description": "Soybean prices track crop supply, global demand, China imports, biofuel demand, and trade policy.",
            "related": ["Corn", "Wheat", "China demand", "DXY", "Biofuels"],
            "drivers": ["China demand", "Weather", "Crop yields", "Biofuel demand", "Trade policy"],
        },
    }

    st.markdown("<div class='ml-market-nav-title'>Commodities</div>", unsafe_allow_html=True)

    category = st.segmented_control(
        "Commodity Category",
        ["Metals", "Energy", "Agriculture"],
        default="Metals",
        label_visibility="collapsed",
    )

    category_map = {
        "Metals": ["Gold", "Silver", "Copper"],
        "Energy": ["Crude Oil", "Brent Oil", "Natural Gas"],
        "Agriculture": ["Wheat", "Corn", "Soybeans"],
    }

    indicator = st.segmented_control(
        "Commodity",
        category_map[category],
        default=category_map[category][0],
        label_visibility="collapsed",
    )

    meta = commodity_map[indicator]

  #  st.markdown(f"<h1 class='ml-page-title'>{indicator}</h1>", unsafe_allow_html=True)
  #  st.markdown(f"<p class='ml-page-description'>{meta['description']}</p>", unsafe_allow_html=True)

    # -----------------------
    # Data
    # -----------------------
    df = get_fx_data_yahoo(
        meta["ticker"],
        start_date=dt.date(1990, 1, 1),
        end_date=dt.date.today(),
    ).dropna()

    if df.empty:
        st.error("No data available.")
        st.stop()

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # -----------------------
    # Controls row
    # -----------------------
    st.markdown("<div class='ml-chart-toolbar'>", unsafe_allow_html=True)

    timeframe = st.segmented_control(
        "Time Frame",
        ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y", "MAX"],
        default="1Y",
        label_visibility="collapsed",
    )

    chart_type = st.segmented_control(
        "Chart Type",
        ["Line", "Area", "Bar", "Step"],
        default="Line",
        label_visibility="collapsed",
    )

    delta_type = st.segmented_control(
        "Delta Type",
        ["Off", "Cumulative", "Daily"],
        default="Off",
        label_visibility="collapsed",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    start_date = get_start_date(df, timeframe)
    end_date = df["date"].max()
    df_filtered = filter_by_dates(df, start_date, end_date)

    stats = calculate_summary_stats(df_filtered)

    latest_val = stats["latest_val"]
    position_pct = stats["position_pct"]
    slope = stats["slope"]
    volatility = stats["volatility"]

    trend = "Upward" if slope > 0 else "Downward" if slope < 0 else "Flat"
    position_label = "High" if position_pct > 70 else "Low" if position_pct < 30 else "Mid"

    significance = "High" if volatility > 25 else "Moderate" if volatility > 12 else "Low"
    
    page_stats = {
        "Latest": f"{latest_val:,.2f}",
        "Trend": trend,
        "Position": f"{position_pct:.0f}% ({position_label})",
        "Volatility": f"{volatility:.1f}%",
        "Significance": significance,
        "Context": f"{timeframe} view",
    }

    price_changes = {
        "1D": pct_change_over(df, "1D"),
        "1W": pct_change_over(df, "1W"),
        "1M": pct_change_over(df, "1M"),
        "6M": pct_change_over(df, "6M"),
        "1Y": pct_change_over(df, "1Y"),
    }

    quarterly = detect_quarterly_data(df_filtered)

    fig = build_market_chart(
        df_filtered,
        indicator,
        chart_type,
        delta_type,
        quarterly=quarterly,
    )

    render_research_page(
        title=indicator,
        description=meta["description"],
        stats=page_stats,
        fig=fig,
        source="Source: Yahoo Finance",
        related_markets=meta["related"],
        price_changes=price_changes,
        key_drivers=meta["drivers"],
        display_chart_func=display_market_chart,
    )