import streamlit as st
import pandas as pd
import datetime as dt

from components.charts import plot_chart
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

def render_fx_page():
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
                {"FX"}
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
            timeframe = st.selectbox(
                "Time Frame",
                ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y", "MAX"],
                index=5
            )

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

        start_date, end_date = render_date_controls(df, timeframe)

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
            title,
            chart_type,
            delta_type,
            quarterly=quarterly,
        )

        display_market_chart(
            fig,
            "Source: Yahoo Finance"
        )
    
    