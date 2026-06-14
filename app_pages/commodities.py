import streamlit as st
import datetime as dt

from data.yahoo import get_fx_data_yahoo
from app_pages.common import (
    calculate_summary_stats,
    render_summary_bar,
    render_commentary,
)
from app_pages.market_utils import (
    render_date_controls,
    filter_by_dates,
    detect_quarterly_data,
    build_market_chart,
    display_market_chart,
)

def render_commodities_page():
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
                {"Commodities"}
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


        start_date, end_date = render_date_controls(df, timeframe)

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


        render_commentary(commentary, indicator)

        df_filtered = filter_by_dates(df, start_date, end_date)
        

        # ======== Summary Stats ========

        stats = calculate_summary_stats(df_filtered)
        render_summary_bar(stats, 2)

        latest_val = stats["latest_val"]
        mean_val = stats["mean_val"]
        position_pct = stats["position_pct"]
        slope = stats["slope"]
        volatility = stats["volatility"]

        quarterly = detect_quarterly_data(df_filtered)

        fig = build_market_chart(
            df_filtered,
            indicator,
            chart_type,
            delta_type,
            quarterly=quarterly,
        )

        display_market_chart(fig, "Source: Yahoo Finance")