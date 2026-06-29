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

def render_crypto_page():
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
                {"Crypto"}
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
            timeframe = st.selectbox(
                "Time Frame",
                ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y", "MAX"],
                index=5
            )

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

        start_date, end_date = render_date_controls(df, timeframe)

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

        display_market_chart(fig, "Source: Yahoo Finance")