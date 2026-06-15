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


US_COMMENTARY = (
    "US Treasury yields reflect market expectations for Federal Reserve policy, "
    "inflation, economic growth, and fiscal conditions. Shorter maturities are "
    "more sensitive to expected Fed rate changes, while longer maturities reflect "
    "long-term growth, inflation, and term-premium expectations."
)

UK_COMMENTARY = (
    "UK Gilt yields reflect market expectations for Bank of England policy, "
    "inflation, economic growth, and government borrowing conditions. Shorter "
    "maturities are more sensitive to monetary policy expectations, while longer "
    "maturities reflect long-term growth, inflation, and fiscal outlook."
)

JAPAN_COMMENTARY = (
    "Japanese Government Bond yields reflect market expectations for Bank of Japan "
    "policy, inflation, economic growth, and government borrowing conditions. "
    "Shorter maturities are more sensitive to monetary policy expectations, while "
    "longer maturities reflect long-term growth, inflation, and fiscal outlooks."
)

EURO_COMMENTARY = (
    "Euro Area government bond yields reflect market expectations for European "
    "Central Bank policy, inflation, economic growth, and fiscal conditions across "
    "the euro area. Shorter maturities are more sensitive to ECB interest rate "
    "expectations, while longer maturities reflect long-term growth, inflation, "
    "and sovereign debt dynamics."
)


BOND_GROUPS = {
    "US Treasuries": [
        "US 1M",
        "US 3M",
        "US 6M",
        "US 1Y",
        "US 2Y",
        "US 3Y",
        "US 5Y",
        "US 7Y",
        "US 10Y",
        "US 20Y",
        "US 30Y",
    ],
    "UK Gilts": [
        "UK 5Y",
        "UK 10Y",
        "UK 20Y",
    ],
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


BOND_MAP = {
    "US 1M": (get_usa_1mo_yield_data, "US 1-Month Treasury Yield"),
    "US 3M": (get_usa_3mo_yield_data, "US 3-Month Treasury Yield"),
    "US 6M": (get_usa_6mo_yield_data, "US 6-Month Treasury Yield"),
    "US 1Y": (get_usa_1yr_yield_data, "US 1-Year Treasury Yield"),
    "US 2Y": (get_usa_2yr_yield_data, "US 2-Year Treasury Yield"),
    "US 3Y": (get_usa_3yr_yield_data, "US 3-Year Treasury Yield"),
    "US 5Y": (get_usa_5yr_yield_data, "US 5-Year Treasury Yield"),
    "US 7Y": (get_usa_7yr_yield_data, "US 7-Year Treasury Yield"),
    "US 10Y": (get_usa_10yr_yield_data, "US 10-Year Treasury Yield"),
    "US 20Y": (get_usa_20yr_yield_data, "US 20-Year Treasury Yield"),
    "US 30Y": (get_usa_30yr_yield_data, "US 30-Year Treasury Yield"),

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


COMMENTARY_BY_GROUP = {
    "US Treasuries": US_COMMENTARY,
    "UK Gilts": UK_COMMENTARY,
    "Japan JGBs": JAPAN_COMMENTARY,
    "Euro Area Bonds": EURO_COMMENTARY,
}


SOURCE_BY_GROUP = {
    "US Treasuries": "Source: Federal Reserve Economic Data (FRED)",
    "UK Gilts": "Source: Bank of England (BOE)",
    "Japan JGBs": "Source: Japan Ministry of Finance (MOF)",
    "Euro Area Bonds": "Source: European Central Bank (ECB)",
}


def render_rates_bonds_page():
    col1, col2 = st.columns([1.5, 5])

    with col1:
        st.markdown(
            """
            <div style="
                position: absolute;
                top: 0px;
                width: 100%;
                text-align: center;
                font-size: 28px;
                font-weight: 700;
                font-family: 'Inter','Segoe UI','Arial',sans-serif;
                color: #111;
                z-index: 10;
            ">
                Rates & Bonds
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)

        category = st.selectbox("Select Country/Group", list(BOND_GROUPS.keys()))
        indicator = st.selectbox("Select Bond", BOND_GROUPS[category])

        ct_col, tf_col = st.columns(2)

        with ct_col:
            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])

        with tf_col:
            timeframe = st.selectbox("Time Frame", ["1Y", "3Y", "5Y", "10Y", "MAX"])

        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])

        data_func, title = BOND_MAP[indicator]

        df = data_func()
        df = df.dropna()

        if df.empty:
            st.error("No data available.")
            st.stop()

        start_date, end_date = render_date_controls(df, timeframe)

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        render_commentary(
            {indicator: COMMENTARY_BY_GROUP[category]},
            indicator,
        )

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

        display_market_chart(
            fig,
            SOURCE_BY_GROUP.get(category, "Source: MacroLens Research"),
        )