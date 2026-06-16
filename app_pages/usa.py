import streamlit as st
import pandas as pd
import datetime as dt
from components.charts import plot_chart
from indicators.usa import *

from app_pages.common import (
    calculate_summary_stats,
    render_summary_bar,
    render_commentary,
)
# -------- USA Tab --------
def render_usa_page():
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
                {"United States"}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Indicator Groups --------
        indicator_groups = {
            "Monetary Policy & Liquidity": [
                "Federal Funds Rate",
                "Fed Balance Sheet",
            ],

            "Inflation": [
                "CPI YoY",
                "Core CPI YoY",
                "PCE YoY",
                "Core PCE YoY",
                "PPI YoY",
                "Core PPI YoY",
                "Import Prices YoY",
                "Export Prices YoY",
            ],

            "Labor Market": [
                "Unemployment Rate",
                "Labor Force Participation Rate",
                "Non Farm Payrolls",
                "Initial Jobless Claims",
                "Average Hourly Earnings YoY",
                "JOLTS Job Openings",
                "Quits Rate",
                "ECI Total Compensation YoY",
                "ECI Wages & Salaries YoY",
            ],

            "Growth & Activity": [
                "GDP Growth Rate",
                "Personal Income MoM",
                "Personal Consumption MoM",
                "Retail Sales MoM",
                "Industrial Production MoM",
                "Capacity Utilization",
                "Durable Goods Orders MoM",
             ##   "ISM Manufacturing PMI",
             ##   "ISM Services PMI",
                "Trade Balance",
            ],

            "Housing": [
                "Housing Starts MoM",
                "Building Permits MoM",
                "New Home Sales MoM",
            ],

            "Productivity & Costs": [
                "Labor Productivity YoY %",
                "Unit Labor Costs YoY %",
                "Real Hourly Compensation YoY %",
            ],

            "Sentiment & Financial Conditions": [
                "Michigan Consumer Sentiment",
                "Chicago Fed NFCI",
            ],
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
            "Federal Funds Rate": (get_usa_interest_rate_data, "daily", None),

            "CPI YoY": (get_usa_cpi_yoy_data, "monthly", None),
            "Core CPI YoY": (get_usa_core_cpi_yoy_data, "monthly", None),
            "PCE YoY": (get_usa_pce_yoy_data, "monthly", None),
            "Core PCE YoY": (get_usa_core_pce_yoy_data, "monthly", None),
            "PPI YoY": (get_usa_ppi_yoy_data, "monthly", None),
            "Core PPI YoY": (get_usa_core_ppi_yoy_data, "monthly", None),
            "Import Prices YoY": (get_usa_import_prices_yoy_data, "monthly", None),
            "Export Prices YoY": (get_usa_export_prices_yoy_data, "monthly", None),

            "Unemployment Rate": (get_usa_unemployment_rate_data, "monthly", None),
            "Labor Force Participation Rate": (get_usa_labor_force_participation_data, "monthly", None),
            "Non Farm Payrolls": (get_usa_nfp_data, "monthly", None),
            "Average Hourly Earnings YoY": (get_usa_average_hourly_earnings_yoy_data, "monthly", None),
            "JOLTS Job Openings": (get_usa_jolts_job_openings_data, "monthly", None),
            "Quits Rate": (get_usa_quits_rate_data, "monthly", None),
            "ECI Total Compensation YoY": (get_usa_eci_total_compensation_yoy_data, "quarterly", None),
            "ECI Wages & Salaries YoY": (get_usa_eci_wages_salaries_yoy_data, "quarterly", None),

            "GDP Growth Rate": (get_usa_gdp_qoq_data, "quarterly", None),
            "Personal Income MoM": (get_usa_personal_income_mom_data, "monthly", None),
            "Personal Consumption MoM": (get_usa_personal_consumption_mom_data, "monthly", None),
            "Retail Sales MoM": (get_usa_retail_sales_mom_data, "monthly", None),
            "Industrial Production MoM": (get_usa_industrial_production_mom_data, "monthly", None),
            "Capacity Utilization": (get_usa_capacity_utilization_data, "monthly", None),
            "Durable Goods Orders MoM": (get_usa_durable_goods_orders_mom_data, "monthly", None),
            "Trade Balance": (get_usa_trade_balance_data, "monthly", None),

            "Housing Starts MoM": (get_usa_housing_starts_mom_data, "monthly", None),
            "Building Permits MoM": (get_usa_building_permits_mom_data, "monthly", None),
            "New Home Sales MoM": (get_usa_new_home_sales_mom_data, "monthly", None),

            "Labor Productivity YoY %": (get_usa_labor_productivity_data, "quarterly", None),
            "Unit Labor Costs YoY %": (get_usa_unit_labor_costs_data, "quarterly", None),
            "Real Hourly Compensation YoY %": (get_usa_real_hourly_compensation_data, "quarterly", None),

            "Michigan Consumer Sentiment": (get_usa_michigan_consumer_sentiment_data, "monthly", None),
            "Chicago Fed NFCI": (get_usa_chicago_fed_nfci_data, "weekly", None),
            
            "Initial Jobless Claims": (get_usa_initial_jobless_claims_data, "weekly", None),
        ##    "ISM Manufacturing PMI": (get_usa_ism_manufacturing_pmi_data, "monthly", None),
         ##   "ISM Services PMI": (get_usa_ism_services_pmi_data, "monthly", None),
            "Fed Balance Sheet": (get_usa_fed_balance_sheet_data, "weekly", None)
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
            "Federal Funds Rate": "The Federal Funds Rate is the benchmark short-term interest rate set by the Federal Reserve. It influences borrowing costs, financial conditions, and the stance of monetary policy.",

            "CPI YoY": "CPI YoY measures the annual change in consumer prices across a broad basket of goods and services. It is one of the main gauges of household inflation pressure.",
            "Core CPI YoY": "Core CPI excludes food and energy prices to show underlying inflation trends. It is closely watched because it removes some of the most volatile components.",
            "PCE YoY": "PCE YoY measures annual inflation based on personal consumption expenditures. It is important because the Federal Reserve places significant weight on PCE inflation.",
            "Core PCE YoY": "Core PCE excludes food and energy and is widely viewed as the Fed’s preferred underlying inflation measure.",
            "PPI YoY": "PPI measures producer-level inflation. It can signal pipeline price pressures before they appear in consumer prices.",
            "Core PPI YoY": "Core PPI excludes more volatile components and helps identify underlying producer price pressure.",
            "Import Prices YoY": "Import prices measure inflation pressure from goods and services purchased abroad. They are influenced by global supply chains, commodity prices, and exchange rates.",
            "Export Prices YoY": "Export prices measure changes in prices received for U.S. goods and services sold abroad. They help assess external demand and U.S. pricing power.",

            "Unemployment Rate": "The unemployment rate measures the share of the labor force that is actively looking for work but unemployed. It is a key indicator of labor-market slack.",
            "Labor Force Participation Rate": "Labor force participation measures the share of the population either working or actively looking for work. It helps separate true labor-market improvement from people leaving the workforce.",
            "Non Farm Payrolls": "Non-farm payrolls measure the monthly change in employment across most sectors of the economy. It is one of the most market-moving U.S. labor indicators.",
            "Average Hourly Earnings YoY": "Average hourly earnings track wage growth. Rising wage growth can support consumption but may also contribute to inflation pressure if productivity does not keep pace.",
            "ECI Total Compensation YoY": "The Employment Cost Index tracks changes in total compensation, including wages, salaries, and benefits. It is valued because it controls for changes in workforce composition.",
            "ECI Wages & Salaries YoY": "ECI wages and salaries measure labor-cost growth excluding benefits. It gives a cleaner read on wage inflation than some payroll-based measures.",
            "JOLTS Job Openings": "JOLTS job openings measure labor demand by showing the number of unfilled positions across the economy. High openings can indicate tight labor-market conditions.",
            "Quits Rate": "The quits rate measures voluntary job separations. A higher quits rate can signal worker confidence and labor-market tightness.",

            "GDP Growth Rate": "Real GDP growth measures the pace of overall economic expansion or contraction. It summarizes changes in output across consumption, investment, government spending, and trade.",
            "Personal Income MoM": "Personal income tracks monthly changes in household income. It helps assess consumer purchasing power and the sustainability of spending.",
            "Personal Consumption MoM": "Personal consumption measures monthly changes in household spending. Since consumption is the largest part of GDP, it is central to growth analysis.",
            "Retail Sales MoM": "Retail sales measure monthly changes in spending at retailers. It is a timely signal of consumer demand and goods-sector momentum.",
            "Industrial Production MoM": "Industrial production tracks monthly output from manufacturing, mining, and utilities. It is useful for monitoring the goods-producing side of the economy.",
            "Capacity Utilization": "Capacity utilization measures how much of industrial capacity is being used. High utilization can indicate supply constraints and inflation pressure.",
            "Durable Goods Orders MoM": "Durable goods orders measure demand for longer-lasting manufactured goods. They help assess business investment and manufacturing momentum.",
            "Trade Balance": "The trade balance shows the difference between exports and imports. It helps evaluate external demand, domestic import demand, and the trade contribution to GDP.",
            "Saving Rate": "The personal saving rate measures saving as a share of disposable income. It helps assess household balance-sheet pressure and spending capacity.",

            "Housing Starts MoM": "Housing starts measure new residential construction activity. They are a key signal for housing demand, construction employment, and interest-rate sensitivity.",
            "Building Permits MoM": "Building permits measure authorized future construction. They often lead housing starts and provide insight into upcoming residential investment.",
            "New Home Sales MoM": "New home sales track purchases of newly built homes. They are sensitive to mortgage rates, affordability, and household demand.",

            "Labor Productivity YoY %": "Labor productivity measures output per hour worked. Higher productivity can support stronger growth without the same inflation pressure.",
            "Unit Labor Costs YoY %": "Unit labor costs measure labor compensation adjusted for productivity. They are important for assessing whether wage growth is translating into inflation pressure.",
            "Real Hourly Compensation YoY %": "Real hourly compensation measures worker compensation adjusted for inflation. It helps assess purchasing power and real wage trends.",

            "Michigan Consumer Sentiment": "The Michigan Consumer Sentiment Index measures household confidence in the economy, personal finances, and expectations. It can foreshadow changes in consumer spending.",
            "Chicago Fed NFCI": "The Chicago Fed National Financial Conditions Index summarizes U.S. financial conditions across money markets, credit markets, and risk indicators.",
            
            "Initial Jobless Claims": "Initial jobless claims measure the number of people filing for unemployment insurance for the first time. It is one of the highest-frequency labor-market indicators and can provide early signals of changes in employment conditions.",

       ##     "ISM Manufacturing PMI": "The ISM Manufacturing PMI tracks activity across the U.S. manufacturing sector. Readings above 50 generally indicate expansion, while readings below 50 generally indicate contraction.",

       ##     "ISM Services PMI": "The ISM Services PMI tracks activity across the U.S. services sector, which represents a large share of the U.S. economy. It is useful for monitoring demand, business activity, employment, and prices in services.",

            "Fed Balance Sheet": "The Federal Reserve balance sheet shows total assets held by the Fed. It is often used as a broad liquidity indicator because changes can reflect quantitative easing, quantitative tightening, emergency lending, and other monetary operations."
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
            "Federal Funds Rate": "Federal Funds Rate (%)",

            "CPI YoY": "Consumer Price Index (YoY, %)",
            "Core CPI YoY": "Core Consumer Price Index (YoY, %)",
            "PCE YoY": "Personal Consumption Expenditures Price Index (YoY, %)",
            "Core PCE YoY": "Core PCE Price Index (YoY, %)",
            "PPI YoY": "Producer Price Index: Final Demand (YoY, %)",
            "Core PPI YoY": "Core Producer Price Index (YoY, %)",
            "Import Prices YoY": "Import Price Index (YoY, %)",
            "Export Prices YoY": "Export Price Index (YoY, %)",

            "Unemployment Rate": "Unemployment Rate (%)",
            "Labor Force Participation Rate": "Labor Force Participation Rate (%)",
            "Non Farm Payrolls": "Non-Farm Payrolls (Monthly Change, Thousands)",
            "Average Hourly Earnings YoY": "Average Hourly Earnings (YoY, %)",
            "JOLTS Job Openings": "JOLTS Job Openings",
            "Quits Rate": "JOLTS Quits Rate",
            "ECI Total Compensation YoY": "Employment Cost Index: Total Compensation (YoY, %)",
            "ECI Wages & Salaries YoY": "Employment Cost Index: Wages & Salaries (YoY, %)",

            "GDP Growth Rate": "Real GDP Growth Rate (QoQ Annualized, %)",
            "Personal Income MoM": "Personal Income (MoM, %)",
            "Personal Consumption MoM": "Personal Consumption Expenditures (MoM, %)",
            "Retail Sales MoM": "Retail Sales (MoM, %)",
            "Industrial Production MoM": "Industrial Production (MoM, %)",
            "Capacity Utilization": "Capacity Utilization (%)",
            "Durable Goods Orders MoM": "Durable Goods Orders (MoM, %)",
            "Trade Balance": "Trade Balance",

            "Housing Starts MoM": "Housing Starts (MoM, %)",
            "Building Permits MoM": "Building Permits (MoM, %)",
            "New Home Sales MoM": "New Home Sales (MoM, %)",

            "Labor Productivity YoY %": "Labor Productivity YoY %",
            "Unit Labor Costs YoY %": "Unit Labor Costs YoY %",
            "Real Hourly Compensation YoY %": "Real Hourly Compensation YoY %",

            "Michigan Consumer Sentiment": "Michigan Consumer Sentiment Index",
            "Chicago Fed NFCI": "Chicago Fed National Financial Conditions Index",
            
            "Initial Jobless Claims": "Initial Jobless Claims",
       ##     "ISM Manufacturing PMI": "ISM Manufacturing PMI",
       ##     "ISM Services PMI": "ISM Services PMI",
            "Fed Balance Sheet": "Federal Reserve Balance Sheet: Total Assets"
        }
        
        source_map = {
            "Federal Funds Rate": "Source: Federal Reserve Economic Data (FRED)",
            "Fed Balance Sheet": "Source: Federal Reserve Economic Data (FRED)",

            "CPI YoY": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Core CPI YoY": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "PPI YoY": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Core PPI YoY": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Import Prices YoY": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Export Prices YoY": "Source: U.S. Bureau of Labor Statistics (BLS)",

            "PCE YoY": "Source: U.S. Bureau of Economic Analysis (BEA)",
            "Core PCE YoY": "Source: U.S. Bureau of Economic Analysis (BEA)",
            "GDP Growth Rate": "Source: U.S. Bureau of Economic Analysis (BEA)",
            "Personal Income MoM": "Source: U.S. Bureau of Economic Analysis (BEA)",
            "Personal Consumption MoM": "Source: U.S. Bureau of Economic Analysis (BEA)",

            "Unemployment Rate": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Labor Force Participation Rate": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Non Farm Payrolls": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Initial Jobless Claims": "Source: Federal Reserve Economic Data (FRED)",
            "Average Hourly Earnings YoY": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "JOLTS Job Openings": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Quits Rate": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "ECI Total Compensation YoY": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "ECI Wages & Salaries YoY": "Source: U.S. Bureau of Labor Statistics (BLS)",

            "Retail Sales MoM": "Source: Federal Reserve Economic Data (FRED)",
            "Industrial Production MoM": "Source: Federal Reserve Economic Data (FRED)",
            "Capacity Utilization": "Source: Federal Reserve Economic Data (FRED)",
            "Durable Goods Orders MoM": "Source: Federal Reserve Economic Data (FRED)",
            "Trade Balance": "Source: Federal Reserve Economic Data (FRED)",
            "Housing Starts MoM": "Source: Federal Reserve Economic Data (FRED)",
            "Building Permits MoM": "Source: Federal Reserve Economic Data (FRED)",
            "New Home Sales MoM": "Source: Federal Reserve Economic Data (FRED)",

            "Labor Productivity YoY %": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Unit Labor Costs YoY %": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Real Hourly Compensation YoY %": "Source: U.S. Bureau of Labor Statistics (BLS)",

            "Michigan Consumer Sentiment": "Source: University of Michigan via FRED",
            "Chicago Fed NFCI": "Source: Federal Reserve Bank of Chicago via FRED",
        }

        # Detect quarterly data
        quarterly = (date_format == "quarterly")

        # -------- Plot Chart --------
        # Convert "Off" to None for plot_chart
        delta_type_arg = None if delta_type == "Off" else delta_type.lower()

        # If delta_type is Off, disable hover delta
        hover_style = "delta" if delta_type_arg is not None else "none"
        
        def get_decimal_places(indicator):
            if indicator in ["Federal Funds Rate"]:
                return 2

            elif indicator in [
                "CPI YoY", "Core CPI YoY", "PCE YoY", "Core PCE YoY",
                "PPI YoY", "Core PPI YoY", "Import Prices YoY", "Export Prices YoY",
                "Unemployment Rate", "Labor Force Participation Rate",
                "Average Hourly Earnings YoY", "Quits Rate",
                "ECI Total Compensation YoY", "ECI Wages & Salaries YoY",
                "GDP Growth Rate", "Personal Income MoM", "Personal Consumption MoM",
                "Retail Sales MoM", "Industrial Production MoM", "Capacity Utilization",
                "Durable Goods Orders MoM", "Housing Starts MoM",
                "Building Permits MoM", "New Home Sales MoM",
                "Labor Productivity YoY %", "Unit Labor Costs YoY %", "Real Hourly Compensation YoY %",
                "Michigan Consumer Sentiment"
            ]:
                return 1

            elif indicator in [
                "Trade Balance", "Non Farm Payrolls", "Initial Jobless Claims",
                "Fed Balance Sheet"
            ]:
                return 0

            elif indicator in ["JOLTS Job Openings", "Chicago Fed NFCI"]:
                return 2

            else:
                return 2

        decimals = get_decimal_places(indicator)
        render_summary_bar(stats, decimals)

        fig = plot_chart(
            df_filtered,
            titles[indicator],
            chart_type,
            hover_style=hover_style,   # conditional hover
            delta_type=delta_type_arg,  # None if Off
            date_format="quarterly" if quarterly else date_format,
            tickformat_override=tickformat_override,
            show_markers=False,
            decimals=decimals
        )


        
        # -------- Fix Crowded X-Axis for Fed Funds Rate --------
        if indicator == "Federal Funds Rate":
            max_ticks = 8  # show ~8 evenly spaced date labels
            if len(df_filtered) > max_ticks:
                step = max(1, len(df_filtered) // max_ticks)
                tickvals = df_filtered['date'].iloc[::step]
                ticktext = [d.strftime('%b %Y') for d in tickvals]
                fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)


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
            