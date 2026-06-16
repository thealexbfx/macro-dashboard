import streamlit as st
import pandas as pd
import datetime as dt


from components.charts import plot_chart
from indicators.euro import *

from app_pages.common import (
    calculate_summary_stats,
    render_summary_bar,
    render_commentary,
)


# -------- EURO Tab --------
def render_euro_page():
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
                {"Euro Area"}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Monetary Policy": ["Interest Rate"],
            "Inflation": ["HICP YoY", "Core HICP YoY"],
            "Labor Market": ["Unemployment Rate"],
            "Growth": ["GDP QoQ", "GDP YoY", "Retail Sales MoM", "Industrial Production MoM"],
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
            "Interest Rate": (get_euro_interest_rate_data, "daily", None),
            "HICP YoY": (get_euro_hicp_yoy_data, "monthly", None),
            "Core HICP YoY": (get_euro_core_hicp_yoy_data, "monthly", None),
            "Unemployment Rate": (get_euro_unemployment_rate_data, "monthly", None),
            "GDP QoQ": (get_euro_gdp_qoq_data, "quarterly", None),
            "GDP YoY": (get_euro_gdp_yoy_data, "quarterly", None),
            "Retail Sales MoM": (get_euro_retail_sales_mom_data, "monthly", None),
            "Industrial Production MoM": (get_euro_industrial_production_mom_data, "monthly", None),
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
                "The European Central Bank (ECB) main refinancing rate is shown using the official ECB effective date of rate changes."
                "It directly affects short-term borrowing costs for banks, which influences loans, mortgages, and business investment across the Eurozone. "
                "Changes in the ECB rate are closely watched by global markets as signals of monetary tightening or easing."
            ),

            # Inflation
            "HICP YoY": (
                "The Harmonised Index of Consumer Prices (HICP YoY) measures annual inflation across the Euro Area using a standardized EU methodology. "
                "It is the ECB's main inflation reference and is central to monetary policy decisions, bond markets, and real income analysis."
            ),

            "Core HICP YoY": (
                "Core HICP YoY strips out volatile items such as energy and food to give a cleaner view of underlying inflation pressure. "
                "It is closely watched by the ECB because persistent core inflation can signal more durable price pressures."
            ),

            # Labor Market
            "Unemployment Rate": (
                "The unemployment rate represents the percentage of the Euro Area labor force actively seeking work but currently without a job. "
                "It is a key indicator of labor market slack, household income pressure, and the broader economic cycle."
            ),

            # Growth
            "GDP QoQ": (
                "Euro Area GDP QoQ measures the quarter-over-quarter change in real economic output. "
                "It captures short-term momentum in consumption, investment, government spending, and net trade across the currency bloc."
            ),

            "GDP YoY": (
                "Euro Area GDP YoY measures real economic growth compared with the same quarter one year earlier. "
                "It gives a smoother view of the underlying growth trend than quarter-over-quarter data."
            ),

            "Retail Sales MoM": (
                "Retail Sales MoM tracks the monthly change in retail trade volumes across the Euro Area. "
                "It is a useful gauge of household consumption momentum and consumer demand."
            ),
            
            "Industrial Production MoM": (
                "Industrial Production measures changes in the output of factories, utilities, and mining across the Euro Area. "
                "It is a key indicator of economic activity and manufacturing momentum, often providing an early signal of changes in growth and business conditions."
            ),
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
            "Interest Rate": "ECB Main Refinancing Rate (%)",
            "HICP YoY": "Euro Area HICP Inflation (YoY, %)",
            "Core HICP YoY": "Euro Area Core HICP Inflation (YoY, %)",
            "Unemployment Rate": "Euro Area Unemployment Rate (%)",
            "GDP QoQ": "Euro Area Real GDP Growth (QoQ, %)",
            "GDP YoY": "Euro Area Real GDP Growth (YoY, %)",
            "Retail Sales MoM": "Euro Area Retail Sales Volume (MoM, %)",
            "Industrial Production MoM": "Industrial Production (MoM, %)",
        }
        
        source_map = {
            "Interest Rate": "Source: European Central Bank (ECB)",
            "HICP YoY": "Source: Eurostat",
            "Core HICP YoY": "Source: Eurostat",
            "Unemployment Rate": "Source: Eurostat",
            "GDP QoQ": "Source: Eurostat",
            "GDP YoY": "Source: Eurostat",
            "Retail Sales MoM": "Source: Eurostat",
            "Industrial Production MoM": "Source: Eurostat",
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
                "HICP YoY",
                "Core HICP YoY",
                "Unemployment Rate",
                "GDP QoQ",
                "GDP YoY",
                "Retail Sales MoM",
                "Industrial Production MoM",
            ]:
                return 1

            else:
                return 2

        decimals = get_decimal_places(indicator)
        render_summary_bar(stats, decimals)
        
        fig = plot_chart(
            df_filtered,
            titles.get(indicator, indicator),
            chart_type,
            hover_style=hover_style,
            delta_type=delta_type_arg,
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False,
            decimals=decimals
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
            y=-0.30,
            showarrow=False,
            xanchor="left",
            font=dict(size=12, color="gray"),
            align="left"
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

            

       