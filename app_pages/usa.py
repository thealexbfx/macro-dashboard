import streamlit as st
import pandas as pd
import datetime as dt
import numpy as np
from components.charts import plot_chart
from indicators.usa import *

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
                {"USA"}
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
                "Labor Productivity",
                "Unit Labor Costs",
                "Real Hourly Compensation",
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

            "Labor Productivity": (get_usa_labor_productivity_data, "quarterly", None),
            "Unit Labor Costs": (get_usa_unit_labor_costs_data, "quarterly", None),
            "Real Hourly Compensation": (get_usa_real_hourly_compensation_data, "quarterly", None),

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

            "Labor Productivity": "Labor productivity measures output per hour worked. Higher productivity can support stronger growth without the same inflation pressure.",
            "Unit Labor Costs": "Unit labor costs measure labor compensation adjusted for productivity. They are important for assessing whether wage growth is translating into inflation pressure.",
            "Real Hourly Compensation": "Real hourly compensation measures worker compensation adjusted for inflation. It helps assess purchasing power and real wage trends.",

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
        render_summary_bar(stats)

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

            "Labor Productivity": "Labor Productivity",
            "Unit Labor Costs": "Unit Labor Costs",
            "Real Hourly Compensation": "Real Hourly Compensation",

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

            "Labor Productivity": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Unit Labor Costs": "Source: U.S. Bureau of Labor Statistics (BLS)",
            "Real Hourly Compensation": "Source: U.S. Bureau of Labor Statistics (BLS)",

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
                "Labor Productivity", "Unit Labor Costs", "Real Hourly Compensation",
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



        # For quarterly, show only Q4 labels
        if quarterly:
            tickvals = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date']
            ticktext = df_filtered.loc[df_filtered['date'].dt.quarter == 4, 'date'] \
                .dt.to_period('Q').apply(lambda x: f"Q{x.quarter} {x.year}")
            fig.update_xaxes(tickmode='array', tickvals=tickvals, ticktext=ticktext)
            
        fig.update_layout(
            hoverlabel=dict(
                font_size=13,       # optional
                font_color="black", # change text color to black
                font_family="Arial" # optional
            )
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
        # 🧠 USA Economy Macro Summary (LLM-enhanced)
        # ==============================

       
        
        st.markdown("### USA Economy Summary (Based on the last 12 Months)")

        

        def generate_usa_llm_summary(results: dict):
            if not results:
                return "No data available to summarize."

            context_text = "\n".join(
                [f"{name}: latest={data['latest']:.2f}%, trend={data['trend']}"
                 for name, data in results.items()]
            )

            prompt = f"""
            You are a senior macro-financial strategist writing a concise, data-driven **condition of the US economy summary**.
            You are given the latest 1-year snapshot for the US economy of various economic indicators.

            Here are the data points:
            {context_text}

            Write one short paragraph (5–7 sentences) summarizing the **overall condition of the US economy** based on these numbers.

            Guidelines:
            - Focus on patterns, contrasts, and relative positioning across indicators.
            - Mention current trends where relevant.
            - Make sure to use the right units for each indicator, for example jolts job openings is in millions etc.
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
        def generate_usa_llm_summary_cached(results: dict):
            return generate_usa_llm_summary(results)

        # ---- Run analysis ----
        st.info("USA Economy Summary temporarily disabled during development to reduce BLS API usage.")

        usa_macro_summary = (
            "USA economy summary is temporarily disabled while BLS caching is being tested."
        )

        # Use cached summary
      ###  usa_macro_summary = st.session_state.usa_macro_summary

        # Add USA summary to global collector
        summary_label = f"🇺🇸 USA Summary ({pd.Timestamp.now().strftime('%Y-%m-%d')})"
        entry = f"{summary_label}:\n{usa_macro_summary}"

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
        {usa_macro_summary}
        </div>
        """, unsafe_allow_html=True)