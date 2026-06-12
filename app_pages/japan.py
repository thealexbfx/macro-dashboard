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
def display_indicator_alert(latest_val, mean_val, position_pct, slope, volatility, indicator_name):
    if position_pct >= 90 and slope > 0:
        status, color, emoji = "Extreme High", "#e63946", "🚨"
        message = f"{indicator_name} is at a historical high and trending upward. Investigate potential risks or causes."
    elif position_pct <= 10 and slope < 0:
        status, color, emoji = "Extreme Low", "#1d3557", "⚠️"
        message = f"{indicator_name} is at a historical low and trending downward. This could signal weakness."
    elif position_pct >= 70:
        status, color, emoji = "High", "#f77f00", "🔺"
        message = f"{indicator_name} is above normal levels. Monitor for emerging trends."
    elif position_pct <= 30:
        status, color, emoji = "Low", "#2a9d8f", "🔻"
        message = f"{indicator_name} is below normal levels. Could indicate caution."
    else:
        status, color, emoji = "Normal", "#06b606", "✅"
        message = f"{indicator_name} is within normal historical range."

    st.markdown(f"""
    <div style="
        width: 100%;
        background-color:{color}1A;
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
    """, unsafe_allow_html=True)



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
        render_summary_bar(stats)

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

        
        
        st.markdown("### Japanese Economy Summary (Based on the last 12 Months)")

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
            st.session_state.japan_macro_summary = (
                "Japan macro summary temporarily disabled during page refactor."
            )

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