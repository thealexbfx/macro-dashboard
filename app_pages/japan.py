import streamlit as st
import pandas as pd
import datetime as dt


from components.charts import plot_chart
from indicators.japan import *

from app_pages.common import (
    calculate_summary_stats,
    render_summary_bar,
    render_commentary,
)

# -------- Japan Tab --------
def render_japan_page():
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
                {"Japan"}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Monetary Policy": ["Interest Rate"],
            "Labor Market": ["Unemployment Rate"],
            "Growth": ["GDP Growth Rate"],
            "Inflation": ["CPI YoY"]
        }

        # Category dropdown
        category = st.selectbox("Select Category", list(indicator_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Indicator", indicator_groups[category])

        # -------- Chart Type + Timeframe side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            is_interest_rate = indicator in ["Federal Funds Rate", "Interest Rate", "Bank Rate"]

            chart_type = st.selectbox(
                "Chart Type",
                ["Line", "Area", "Bar", "Step"],
                index=3 if is_interest_rate else 0
            )
        with tf_col:
            timeframe = st.selectbox(
                "Time Frame",
                ["1Y", "3Y", "5Y", "10Y", "MAX"],
                index=2 if is_interest_rate else 0
            )

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Indicator Function Mapping --------
        indicator_map = {
            "Interest Rate": (get_japan_interest_rate_data, "daily", None),
            "CPI YoY": (get_japan_cpi_yoy_data, "monthly", None),
            "GDP Growth Rate": (get_japan_gdp_qoq_data, "quarterly", None),
            "Unemployment Rate": (get_japan_unemployment_rate_data, "monthly", None)
        }

        # Load data dynamically
        func, date_format, tickformat_override = indicator_map[indicator]
        df = func()
        df = df.dropna()

        if is_interest_rate and not df.empty:
            today = pd.Timestamp.today().normalize()
            last_date = df["date"].max()
            last_value = df["value"].iloc[-1]

            if last_date < today:
                df = pd.concat(
                    [
                        df,
                        pd.DataFrame(
                            {
                                "date": [today],
                                "value": [last_value]
                            }
                        )
                    ],
                    ignore_index=True
                )

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


        render_commentary(commentary, indicator)

        # -------- Filter Data by Date --------
        df_filtered = df[(df['date'] >= pd.to_datetime(start_date)) &
                         (df['date'] <= pd.to_datetime(end_date))]
        
        
        

        # ======== Summary Stats ========

        stats = calculate_summary_stats(df_filtered)

        latest_val = stats["latest_val"]
        mean_val = stats["mean_val"]
        position_pct = stats["position_pct"]
        slope = stats["slope"]
        volatility = stats["volatility"]


        # -------- Dynamic Titles --------
        titles = {
            "Interest Rate": "Bank of Japan Policy Rate (%)",
            "CPI YoY": "Consumer Price Index (YoY, %)",
            "GDP Growth Rate": "GDP Growth Rate (QoQ Annualized %)",
            "Unemployment Rate": "Unemployment Rate (%)"
        }
        
        source_map = {
            "Interest Rate": "Source: Bank of Japan (BOJ)",
            "CPI YoY": "Source: Statistics Bureau of Japan / e-Stat",
            "GDP Growth Rate": "Source: Cabinet Office of Japan / e-Stat",
            "Unemployment Rate": "Source: Statistics Bureau of Japan / e-Stat",
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"
        
        def get_decimal_places(indicator):
            if indicator == "Interest Rate":
                return 2

            elif indicator in [
                "CPI YoY",
                "GDP Growth Rate",
                "Unemployment Rate",
            ]:
                return 1

            else:
                return 2

        decimals = get_decimal_places(indicator)
        render_summary_bar(stats, decimals)
        
        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False,
            decimals=decimals
        )

        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']

            if len(tickvals) > 12:
                step = max(1, len(tickvals) // 12)
                tickvals = tickvals.iloc[::step]

            ticktext = [d.strftime("%Y") for d in tickvals]

            fig.update_xaxes(
                tickmode='array',
                tickvals=tickvals,
                ticktext=ticktext
            )

        fig.update_layout(
            hoverlabel=dict(
                font_size=13,
                font_color="black",
                font_family="Arial"
            )
        )
        
        fig.add_annotation(
            text=source_map.get(indicator, "Source: MacroLens Research"),
            xref="paper",
            yref="paper",
            x=0,
            y=-0.24,
            showarrow=False,
            xanchor="left",
            font=dict(size=12, color="gray"),
            align="left"
        )

        fig.add_annotation(
            text="macrolensresearch.com",
            xref="paper",
            yref="paper",
            x=0,
            y=-0.34,
            showarrow=False,
            xanchor="left",
            font=dict(size=12, color="gray"),
            align="left"
        )

        fig.update_layout(
            margin=dict(b=115)
        )

        fig.update_layout(
            margin=dict(b=115)
        )

        fig.update_layout(
            margin=dict(b=95)
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

           

      