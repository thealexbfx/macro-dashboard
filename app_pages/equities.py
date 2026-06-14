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

def render_equities_page():
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
                {"Equities"}
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

        start_date, end_date = render_date_controls(df, timeframe)

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