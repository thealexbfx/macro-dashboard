import streamlit as st

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

from data.bonds import (
    get_usa_1mo_yield_data,
    get_usa_3mo_yield_data,
    get_usa_6mo_yield_data,
    get_usa_1yr_yield_data,
    get_usa_2yr_yield_data,
    get_usa_3yr_yield_data,
    get_usa_5yr_yield_data,
    get_usa_7yr_yield_data,
    get_usa_10yr_yield_data,
    get_usa_20yr_yield_data,
    get_usa_30yr_yield_data,
    get_uk_5yr_yield_data,
    get_uk_10yr_yield_data,
    get_uk_20yr_yield_data,
    get_japan_1yr_yield_data,
    get_japan_2yr_yield_data,
    get_japan_3yr_yield_data,
    get_japan_5yr_yield_data,
    get_japan_7yr_yield_data,
    get_japan_10yr_yield_data,
    get_japan_20yr_yield_data,
    get_japan_30yr_yield_data,
    get_japan_40yr_yield_data,
    get_euro_1yr_yield_data,
    get_euro_2yr_yield_data,
    get_euro_3yr_yield_data,
    get_euro_5yr_yield_data,
    get_euro_7yr_yield_data,
    get_euro_10yr_yield_data,
    get_euro_20yr_yield_data,
    get_euro_30yr_yield_data,
)



def render_rates_bonds_page():
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
                {"Rates & Bonds"}
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        # -------- Bond Categories --------
        bond_groups = {
            "US Treasuries": ["US 2Y", "US 10Y"],

            "UK Gilts": ["UK 5Y", "UK 10Y", "UK 20Y"],

            "Japan JGBs": [
                "Japan 1Y",
                "Japan 2Y",
                "Japan 3Y",
                "Japan 5Y",
                "Japan 7Y",
                "Japan 10Y",
                "Japan 20Y",
                "Japan 30Y",
                "Japan 40Y",
            ],

            "Euro Area Bonds": [
                "Euro 1Y",
                "Euro 2Y",
                "Euro 3Y",
                "Euro 5Y",
                "Euro 7Y",
                "Euro 10Y",
                "Euro 20Y",
                "Euro 30Y",
            ],
        }

        # Category dropdown
        category = st.selectbox("Select Country/Group", list(bond_groups.keys()))

        # Indicator dropdown based on category
        indicator = st.selectbox("Select Bond", bond_groups[category])

        # -------- Chart Type + Time Frame side by side --------
        ct_col, tf_col = st.columns(2)
        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])
        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        # Delta Type (allow turning it off)
        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        # -------- Bond Indicator Mapping --------
        bond_map = {
            "US 2Y": (get_usa_2yr_yield_data, "US 2-Year Treasury Yield"),
            "US 10Y": (get_usa_10yr_yield_data, "US 10-Year Treasury Yield"),

            "UK 5Y": (get_uk_5yr_yield_data, "UK 5-Year Gilt Yield"),
            "UK 10Y": (get_uk_10yr_yield_data, "UK 10-Year Gilt Yield"),
            "UK 20Y": (get_uk_20yr_yield_data, "UK 20-Year Gilt Yield"),

            "Japan 1Y": (get_japan_1yr_yield_data, "Japan 1-Year JGB Yield"),
            "Japan 2Y": (get_japan_2yr_yield_data, "Japan 2-Year JGB Yield"),
            "Japan 3Y": (get_japan_3yr_yield_data, "Japan 3-Year JGB Yield"),
            "Japan 5Y": (get_japan_5yr_yield_data, "Japan 5-Year JGB Yield"),
            "Japan 7Y": (get_japan_7yr_yield_data, "Japan 7-Year JGB Yield"),
            "Japan 10Y": (get_japan_10yr_yield_data, "Japan 10-Year JGB Yield"),
            "Japan 20Y": (get_japan_20yr_yield_data, "Japan 20-Year JGB Yield"),
            "Japan 30Y": (get_japan_30yr_yield_data, "Japan 30-Year JGB Yield"),
            "Japan 40Y": (get_japan_40yr_yield_data, "Japan 40-Year JGB Yield"),
            "Euro 1Y": (get_euro_1yr_yield_data, "Euro Area 1-Year AAA Yield"),
            "Euro 2Y": (get_euro_2yr_yield_data, "Euro Area 2-Year AAA Yield"),
            "Euro 3Y": (get_euro_3yr_yield_data, "Euro Area 3-Year AAA Yield"),
            "Euro 5Y": (get_euro_5yr_yield_data, "Euro Area 5-Year AAA Yield"),
            "Euro 7Y": (get_euro_7yr_yield_data, "Euro Area 7-Year AAA Yield"),
            "Euro 10Y": (get_euro_10yr_yield_data, "Euro Area 10-Year AAA Yield"),
            "Euro 20Y": (get_euro_20yr_yield_data, "Euro Area 20-Year AAA Yield"),
            "Euro 30Y": (get_euro_30yr_yield_data, "Euro Area 30-Year AAA Yield"),
        }

        data_func, title = bond_map[indicator]

        # Load bond data
        df = data_func()
        df = df.dropna()
        if df.empty:
            st.error("No data available.")
            st.stop()

        start_date, end_date = render_date_controls(df, timeframe)

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        # -------- Commentary --------
        commentary = {
            # U.S. Treasuries
            "US 2Y": (
                "The US 2-Year Treasury yield reflects short-term interest rate expectations and Federal Reserve policy guidance. "
                "It is highly sensitive to Fed rate changes, inflation data, and economic forecasts, serving as a barometer for near-term monetary policy."
            ),

            "US 10Y": (
                "The US 10-Year Treasury yield signals long-term growth and inflation expectations in the U.S. economy. "
                "It is influenced by economic data, Federal Reserve policy, and investor sentiment regarding future inflation and fiscal policy."
            ),

            # UK Gilts
            "UK 2Y": (
                "The UK 2-Year Gilt yield responds primarily to Bank of England policy guidance and short-term rate expectations. "
                "It reflects market sentiment on near-term monetary policy and economic conditions in the UK."
            ),

            "UK 10Y": (
                "The UK 10-Year Gilt yield indicates long-term expectations for inflation, growth, and fiscal stability. "
                "It is influenced by government borrowing, economic data, and Bank of England policy signals."
            ),

            # Japan Government Bonds
            "Japan 1Y": (
                "Japanese Government Bond (JGB) yields reflect market expectations for Bank of Japan policy, inflation, economic growth, and government borrowing conditions. "
                "Shorter maturities are more sensitive to monetary policy expectations, while longer maturities reflect long-term growth, inflation, and fiscal outlooks."
            ),

            "Japan 2Y": (
                "Japanese Government Bond (JGB) yields reflect market expectations for Bank of Japan policy, inflation, economic growth, and government borrowing conditions. "
                "Shorter maturities are more sensitive to monetary policy expectations, while longer maturities reflect long-term growth, inflation, and fiscal outlooks."
            ),

            "Japan 3Y": (
                "Japanese Government Bond (JGB) yields reflect market expectations for Bank of Japan policy, inflation, economic growth, and government borrowing conditions. "
                "Shorter maturities are more sensitive to monetary policy expectations, while longer maturities reflect long-term growth, inflation, and fiscal outlooks."
            ),

            "Japan 5Y": (
                "Japanese Government Bond (JGB) yields reflect market expectations for Bank of Japan policy, inflation, economic growth, and government borrowing conditions. "
                "Shorter maturities are more sensitive to monetary policy expectations, while longer maturities reflect long-term growth, inflation, and fiscal outlooks."
            ),

            "Japan 7Y": (
                "Japanese Government Bond (JGB) yields reflect market expectations for Bank of Japan policy, inflation, economic growth, and government borrowing conditions. "
                "Shorter maturities are more sensitive to monetary policy expectations, while longer maturities reflect long-term growth, inflation, and fiscal outlooks."
            ),

            "Japan 10Y": (
                "Japanese Government Bond (JGB) yields reflect market expectations for Bank of Japan policy, inflation, economic growth, and government borrowing conditions. "
                "Shorter maturities are more sensitive to monetary policy expectations, while longer maturities reflect long-term growth, inflation, and fiscal outlooks."
            ),

            "Japan 20Y": (
                "Japanese Government Bond (JGB) yields reflect market expectations for Bank of Japan policy, inflation, economic growth, and government borrowing conditions. "
                "Shorter maturities are more sensitive to monetary policy expectations, while longer maturities reflect long-term growth, inflation, and fiscal outlooks."
            ),

            "Japan 30Y": (
                "Japanese Government Bond (JGB) yields reflect market expectations for Bank of Japan policy, inflation, economic growth, and government borrowing conditions. "
                "Shorter maturities are more sensitive to monetary policy expectations, while longer maturities reflect long-term growth, inflation, and fiscal outlooks."
            ),

            "Japan 40Y": (
                "Japanese Government Bond (JGB) yields reflect market expectations for Bank of Japan policy, inflation, economic growth, and government borrowing conditions. "
                "Shorter maturities are more sensitive to monetary policy expectations, while longer maturities reflect long-term growth, inflation, and fiscal outlooks."
            ),

            # Eurozone Bonds
            "Euro 1Y": (
                "Euro Area government bond yields reflect market expectations for European Central Bank policy, inflation, economic growth, and fiscal conditions across the euro area. "
                "Shorter maturities are more sensitive to ECB interest rate expectations, while longer maturities reflect long-term growth, inflation, and sovereign debt dynamics."
            ),

            "Euro 2Y": (
                "Euro Area government bond yields reflect market expectations for European Central Bank policy, inflation, economic growth, and fiscal conditions across the euro area. "
                "Shorter maturities are more sensitive to ECB interest rate expectations, while longer maturities reflect long-term growth, inflation, and sovereign debt dynamics."
            ),

            "Euro 3Y": (
                "Euro Area government bond yields reflect market expectations for European Central Bank policy, inflation, economic growth, and fiscal conditions across the euro area. "
                "Shorter maturities are more sensitive to ECB interest rate expectations, while longer maturities reflect long-term growth, inflation, and sovereign debt dynamics."
            ),

            "Euro 5Y": (
                "Euro Area government bond yields reflect market expectations for European Central Bank policy, inflation, economic growth, and fiscal conditions across the euro area. "
                "Shorter maturities are more sensitive to ECB interest rate expectations, while longer maturities reflect long-term growth, inflation, and sovereign debt dynamics."
            ),

            "Euro 7Y": (
                "Euro Area government bond yields reflect market expectations for European Central Bank policy, inflation, economic growth, and fiscal conditions across the euro area. "
                "Shorter maturities are more sensitive to ECB interest rate expectations, while longer maturities reflect long-term growth, inflation, and sovereign debt dynamics."
            ),

            "Euro 10Y": (
                "Euro Area government bond yields reflect market expectations for European Central Bank policy, inflation, economic growth, and fiscal conditions across the euro area. "
                "Shorter maturities are more sensitive to ECB interest rate expectations, while longer maturities reflect long-term growth, inflation, and sovereign debt dynamics."
            ),

            "Euro 20Y": (
                "Euro Area government bond yields reflect market expectations for European Central Bank policy, inflation, economic growth, and fiscal conditions across the euro area. "
                "Shorter maturities are more sensitive to ECB interest rate expectations, while longer maturities reflect long-term growth, inflation, and sovereign debt dynamics."
            ),

            "Euro 30Y": (
                "Euro Area government bond yields reflect market expectations for European Central Bank policy, inflation, economic growth, and fiscal conditions across the euro area. "
                "Shorter maturities are more sensitive to ECB interest rate expectations, while longer maturities reflect long-term growth, inflation, and sovereign debt dynamics."
            )
        }


        render_commentary(commentary, indicator)

        df_filtered = filter_by_dates(df, start_date, end_date)

        stats = calculate_summary_stats(df_filtered)
        render_summary_bar(stats, 2)

        quarterly = detect_quarterly_data(df_filtered)

        fig = build_market_chart(
            df_filtered,
            title,
            chart_type,
            delta_type,
            quarterly=quarterly,
        )
        
        source_map = {
            "US 1M": "Source: Federal Reserve Economic Data (FRED)",
            "US 3M": "Source: Federal Reserve Economic Data (FRED)",
            "US 6M": "Source: Federal Reserve Economic Data (FRED)",
            "US 1Y": "Source: Federal Reserve Economic Data (FRED)",
            "US 2Y": "Source: Federal Reserve Economic Data (FRED)",
            "US 3Y": "Source: Federal Reserve Economic Data (FRED)",
            "US 5Y": "Source: Federal Reserve Economic Data (FRED)",
            "US 7Y": "Source: Federal Reserve Economic Data (FRED)",
            "US 10Y": "Source: Federal Reserve Economic Data (FRED)",
            "US 20Y": "Source: Federal Reserve Economic Data (FRED)",
            "US 30Y": "Source: Federal Reserve Economic Data (FRED)",

            "UK 5Y": "Source: Bank of England (BOE)",
            "UK 10Y": "Source: Bank of England (BOE)",
            "UK 20Y": "Source: Bank of England (BOE)",

            "Japan 1Y": "Source: Japan Ministry of Finance (MOF)",
            "Japan 2Y": "Source: Japan Ministry of Finance (MOF)",
            "Japan 3Y": "Source: Japan Ministry of Finance (MOF)",
            "Japan 5Y": "Source: Japan Ministry of Finance (MOF)",
            "Japan 7Y": "Source: Japan Ministry of Finance (MOF)",
            "Japan 10Y": "Source: Japan Ministry of Finance (MOF)",
            "Japan 20Y": "Source: Japan Ministry of Finance (MOF)",
            "Japan 30Y": "Source: Japan Ministry of Finance (MOF)",
            "Japan 40Y": "Source: Japan Ministry of Finance (MOF)",

            "Euro 1Y": "Source: European Central Bank (ECB)",
            "Euro 2Y": "Source: European Central Bank (ECB)",
            "Euro 3Y": "Source: European Central Bank (ECB)",
            "Euro 5Y": "Source: European Central Bank (ECB)",
            "Euro 7Y": "Source: European Central Bank (ECB)",
            "Euro 10Y": "Source: European Central Bank (ECB)",
            "Euro 20Y": "Source: European Central Bank (ECB)",
            "Euro 30Y": "Source: European Central Bank (ECB)",
        }

        display_market_chart(
            fig,
            source_map.get(indicator, "Source: MacroLens Research")
        )