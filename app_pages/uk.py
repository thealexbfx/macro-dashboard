import streamlit as st
import pandas as pd
import datetime as dt
import numpy as np

from components.charts import plot_chart
from indicators.uk import *

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


# -------- UK Tab --------
def render_uk_page():
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
                {"UK"}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {      
            "Monetary Policy": [
                "Bank Rate"
            ],
            "Labor Market": [
                "Unemployment Rate",
                "Average Weekly Earnings YoY",
                "Vacancies"
            ],
            "Growth": [
                "GDP QoQ",
                "Retail Sales MoM",
                "Industrial Production MoM"
            ],
            "Inflation": [
                "CPI YoY",
                "Core CPI YoY",
                "House Prices YoY"
            ],
            "External Sector": [
                "Trade Balance"
            ]
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
            "Bank Rate": (get_uk_interest_rate_data, "daily", None),

            "CPI YoY": (get_uk_cpi_yoy_data, "monthly", None),
            "Core CPI YoY": (get_uk_core_cpi_yoy_data, "monthly", None),
            "House Prices YoY": (get_uk_house_prices_yoy_data, "monthly", None),

            "GDP QoQ": (get_uk_gdp_qoq_data, "quarterly", None),
            "Retail Sales MoM": (get_uk_retail_sales_mom_data, "monthly", None),
            "Industrial Production MoM": (get_uk_industrial_production_mom_data, "monthly", None),

            "Unemployment Rate": (get_uk_unemployment_rate_data, "monthly", None),
            "Average Weekly Earnings YoY": (get_uk_average_weekly_earnings_yoy_data, "monthly", None),
            "Vacancies": (get_uk_vacancies_data, "monthly", None),

            "Trade Balance": (get_uk_trade_balance_data, "monthly", None),

            
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
            "Bank Rate": (
                "The Bank Rate is the Bank of England's main policy interest rate. "
                "It influences borrowing costs across the economy, including mortgages, consumer credit, business loans, and money-market pricing. "
                "Markets watch this indicator closely because it signals the stance of UK monetary policy and the balance between inflation control and growth support."
            ),

            # Inflation
            "CPI YoY": (
                "Consumer Price Inflation measures the annual change in the price of a broad basket of goods and services purchased by UK households. "
                "It is the headline inflation measure most closely followed by households, policymakers, and markets. "
                "Higher CPI inflation can increase pressure on the Bank of England to keep policy restrictive, while falling inflation may support expectations for easier policy."
            ),

            "Core CPI YoY": (
                "Core CPI excludes more volatile components such as energy, food, alcohol, and tobacco. "
                "It helps identify the underlying trend in inflation, which is important for judging whether price pressures are becoming embedded. "
                "The Bank of England and financial markets often place significant weight on core inflation because it can be stickier than headline CPI."
            ),

            "House Prices YoY": (
                "House price growth measures the annual change in UK residential property prices. "
                "It provides insight into housing-market momentum, household wealth effects, mortgage affordability, and credit conditions. "
                "Rising house prices can support consumer confidence and balance sheets, while slowing or falling prices may signal pressure from higher interest rates or weaker demand."
            ),

            # Growth
            "GDP QoQ": (
                "GDP growth measures the quarterly change in the total output of the UK economy. "
                "It captures the broad direction of economic activity across consumption, investment, government spending, and trade. "
                "Positive GDP growth suggests expansion, while weak or negative growth can indicate stagnation or recession risk."
            ),

            "Retail Sales MoM": (
                "Retail sales measure the monthly change in the volume of goods sold by retailers. "
                "This is an important gauge of household consumption, which is a major driver of UK economic growth. "
                "Stronger retail sales can point to resilient consumer demand, while declines may indicate pressure from inflation, interest rates, or weaker real incomes."
            ),

            "Industrial Production MoM": (
                "Industrial production measures the monthly change in output from manufacturing, mining, energy, and related production industries. "
                "It provides insight into the goods-producing side of the UK economy and can be sensitive to global demand, energy costs, and supply-chain conditions. "
                "Although services dominate the UK economy, industrial production remains useful for tracking cyclical momentum."
            ),

            # Labor Market
            "Unemployment Rate": (
                "The unemployment rate measures the share of the UK labour force that is actively seeking work but currently unemployed. "
                "It is a key indicator of labour-market slack and household income risk. "
                "A low unemployment rate usually points to tight labour conditions, while a rising rate can signal weakening demand for workers."
            ),

            "Average Weekly Earnings YoY": (
                "Average weekly earnings measure annual wage growth across the UK labour market. "
                "This indicator is important because wage growth affects household purchasing power, services inflation, and the Bank of England's inflation outlook. "
                "Strong wage growth can support consumption but may also make inflation more persistent if it outpaces productivity."
            ),

            "Vacancies": (
                "Job vacancies measure the number of open positions employers are trying to fill. "
                "They provide a forward-looking view of labour demand and hiring appetite. "
                "Falling vacancies can suggest cooling labour-market conditions, while elevated vacancies may indicate that firms still face difficulty finding workers."
            ),

            # External Sector
            "Trade Balance": (
                "The trade balance measures the difference between UK exports and imports of goods and services. "
                "A deficit means imports exceed exports, while a surplus means exports exceed imports. "
                "This indicator helps assess external demand, domestic import demand, currency sensitivity, and the contribution of net trade to overall economic growth."
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
            "Bank Rate": "Bank of England Bank Rate (%)",

            "CPI YoY": "Consumer Price Inflation (YoY %)",
            "Core CPI YoY": "Core Consumer Price Inflation (YoY %)",
            "House Prices YoY": "House Price Growth (YoY %)",

            "GDP QoQ": "GDP Growth (QoQ %)",
            "Retail Sales MoM": "Retail Sales (MoM %)",
            "Industrial Production MoM": "Industrial Production (MoM %)",

            "Unemployment Rate": "Unemployment Rate (%)",
            "Average Weekly Earnings YoY": "Average Weekly Earnings (YoY %)",
            "Vacancies": "Job Vacancies (Thousands)",

            "Trade Balance": "Trade Balance (£ Millions)"
          
        }
        
        source_map = {
            "Bank Rate": "Source: Bank of England (BOE)",
            "CPI YoY": "Source: Office for National Statistics (ONS)",
            "Core CPI YoY": "Source: Office for National Statistics (ONS)",
            "GDP QoQ": "Source: Office for National Statistics (ONS)",
            "Unemployment Rate": "Source: Office for National Statistics (ONS)",
            "Retail Sales MoM": "Source: Office for National Statistics (ONS)",
            "Average Weekly Earnings YoY": "Source: Office for National Statistics (ONS)",
            "Industrial Production MoM": "Source: Office for National Statistics (ONS)",
            "Trade Balance": "Source: Office for National Statistics (ONS)",
            "House Prices YoY": "Source: Office for National Statistics (ONS)",
            "Vacancies": "Source: Office for National Statistics (ONS)",
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()
        hover_style = "delta" if delta_type_arg is not None else "none"
        
        def get_decimal_places(indicator):
            if indicator in ["Bank Rate"]:
                return 2

            elif indicator in [
                "CPI YoY",
                "Core CPI YoY",
                "House Prices YoY",
                "GDP QoQ",
                "Retail Sales MoM",
                "Industrial Production MoM",
                "Unemployment Rate",
                "Average Weekly Earnings YoY",
            ]:
                return 1

            elif indicator in [
                "Vacancies",
                "Trade Balance",
            ]:
                return 0

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
        # 🧠 UK Economy Macro Summary (LLM-enhanced)
        # ==============================

       
        
        st.markdown("### UK Economy Summary (Based on the last 12 Months)")

       

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
            st.session_state.uk_macro_summary = (
                "UK macro summary temporarily disabled during page refactor."
            )

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