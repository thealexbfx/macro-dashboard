import streamlit as st
import pandas as pd
import datetime as dt

from components.charts import plot_chart
from indicators.uk import *

from app_pages.common import (
    calculate_summary_stats,
    render_summary_bar,
    render_commentary,
)


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
                {"United Kingdom"}
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

            ticktext = [
                d.strftime("%Y")
                for d in tickvals
            ]

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
        

        