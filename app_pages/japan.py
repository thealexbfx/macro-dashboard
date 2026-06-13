import streamlit as st
import pandas as pd
import datetime as dt
import numpy as np

from components.charts import plot_chart
from indicators.japan import *

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

def render_summary_bar(stats, decimals):
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
        font-size:16px;
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
        <div>Latest: <b>{stats["latest_val"]:.{decimals}f}</b></div>
        <div>Average: <b>{stats["mean_val"]:.{decimals}f}</b></div>
        <div>Change: <b style='color:{change_color};'>{stats["change_since_start"]:+.{decimals}f}</b></div>
        <div>Trend: <b>{stats["trend"]}</b></div>
        <div>Position: <b>{stats["position_pct"]:.0f}% ({position_label})</b></div>
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
            font=dict(size=12, color="gray"),
            align="left"
        )

        fig.add_annotation(
            text="macrolensresearch.com",
            xref="paper",
            yref="paper",
            x=1,
            y=-0.24,
            showarrow=False,
            font=dict(size=12, color="gray"),
            align="right"
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

           

      