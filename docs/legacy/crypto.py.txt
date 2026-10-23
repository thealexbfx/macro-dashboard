[1mdiff --git a/app_pages/crypto.py b/app_pages/crypto.py[m
[1mindex 6d70d97..933fc86 100644[m
[1m--- a/app_pages/crypto.py[m
[1m+++ b/app_pages/crypto.py[m
[36m@@ -1,126 +1,16 @@[m
[31m-import streamlit as st[m
[31m-import datetime as dt[m
[31m-[m
[31m-from data.yahoo import get_fx_data_yahoo[m
[31m-from app_pages.common import ([m
[31m-    calculate_summary_stats,[m
[31m-    render_summary_bar,[m
[31m-    render_commentary,[m
[31m-)[m
[31m-from app_pages.market_utils import ([m
[31m-    render_date_controls,[m
[31m-    filter_by_dates,[m
[31m-    detect_quarterly_data,[m
[31m-    build_market_chart,[m
[31m-    display_market_chart,[m
[32m+[m[32mfrom app_pages.market_page import render_market_page[m
[32m+[m[32mfrom market_data.crypto import ([m
[32m+[m[32m    CRYPTO_CATEGORY_MAP,[m
[32m+[m[32m    CRYPTO_COMPARE_MAP,[m
[32m+[m[32m    CRYPTO_MAP,[m
 )[m
 [m
[31m-def render_crypto_page():[m
[31m-    col1, col2 = st.columns([1.5, 5])[m
[31m-[m
[31m-    with col1:[m
[31m-        # ---------- Centered Page Title ----------[m
[31m-        st.markdown(f"""[m
[31m-            <div style="[m
[31m-                position: absolute;[m
[31m-                top: 0px;  /* keeps it at the top of col1 */[m
[31m-                width: 100%;[m
[31m-                text-align: center;[m
[31m-                font-size: 28px;[m
[31m-                font-weight: 700;[m
[31m-                font-family: 'Inter','Segoe UI','Arial',sans-serif;[m
[31m-                color: #111;[m
[31m-                z-index: 10;[m
[31m-            ">[m
[31m-                {"Crypto"}[m
[31m-            </div>[m
[31m-        """, unsafe_allow_html=True)[m
[31m-        [m
[31m-        st.markdown("<div style='margin-top:90px;'>", unsafe_allow_html=True)[m
[31m-[m
[31m-        # -------- Indicator Groups --------[m
[31m-        indicator_groups = {[m
[31m-            "Major Coins": ["Bitcoin", "Ethereum"][m
[31m-        }[m
[31m-[m
[31m-        # Category dropdown[m
[31m-        category = st.selectbox("Select Category", list(indicator_groups.keys()))[m
[31m-[m
[31m-        # Indicator dropdown based on category[m
[31m-        indicator = st.selectbox("Select Indicator", indicator_groups[category])[m
[31m-[m
[31m-        # -------- Chart Type + Timeframe side by side --------[m
[31m-        ct_col, tf_col = st.columns(2)[m
[31m-        with ct_col:[m
[31m-            chart_type = st.selectbox("Chart Type", ["Line", "Area", "Bar", "Step"])[m
[31m-        with tf_col:[m
[31m-            timeframe = st.selectbox([m
[31m-                "Time Frame",[m
[31m-                ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "5Y", "10Y", "MAX"],[m
[31m-                index=5[m
[31m-            )[m
[31m-[m
[31m-        # Delta Type (allow turning it off)[m
[31m-        delta_type = st.selectbox("Delta Type", ["Off", "Cumulative", "Daily"])[m
[31m-[m
[31m-        # -------- Indicator Function Mapping --------[m
[31m-        crypto_map = {[m
[31m-            "Bitcoin": ("BTC-USD", "Bitcoin"),[m
[31m-            "Ethereum": ("ETH-USD", "Ethereum")[m
[31m-        }[m
[31m-        ticker, title = crypto_map[indicator][m
[31m-[m
[31m-        # Load crypto data[m
[31m-        df = get_fx_data_yahoo(ticker, start_date=dt.date(1990, 1, 1), end_date=dt.date.today())[m
[31m-        df = df.dropna()[m
[31m-        if df.empty:[m
[31m-            st.error("No data available.")[m
[31m-            st.stop()[m
[31m-[m
[31m-        start_date, end_date = render_date_controls(df, timeframe)[m
 [m
[31m-        st.markdown("</div>", unsafe_allow_html=True)[m
[31m-[m
[31m-    with col2:[m
[31m-        # -------- Commentary --------[m
[31m-        commentary = {[m
[31m-            "Bitcoin": ([m
[31m-                "Bitcoin is the largest cryptocurrency by market capitalization and is often considered 'digital gold.' "[m
[31m-                "Its price is influenced by investor sentiment, adoption trends, regulatory developments, macroeconomic conditions, and supply-demand dynamics of its fixed supply."[m
[31m-            ),[m
[31m-[m
[31m-            "Ethereum": ([m
[31m-                "Ethereum is the leading smart contract platform, enabling decentralized applications (dApps), decentralized finance (DeFi), and NFTs. "[m
[31m-                "Its value is driven by network activity, adoption of dApps, technological upgrades, gas fees, and overall crypto market sentiment."[m
[31m-            )[m
[31m-        }[m
[31m-[m
[31m-[m
[31m-        render_commentary(commentary, indicator)[m
[31m-[m
[31m-        df_filtered = filter_by_dates(df, start_date, end_date)[m
[31m-        [m
[31m-    [m
[31m-        # ======== Summary Stats ========[m
[31m-[m
[31m-        stats = calculate_summary_stats(df_filtered)[m
[31m-        render_summary_bar(stats, 2)[m
[31m-[m
[31m-        latest_val = stats["latest_val"][m
[31m-        mean_val = stats["mean_val"][m
[31m-        position_pct = stats["position_pct"][m
[31m-        slope = stats["slope"][m
[31m-        volatility = stats["volatility"][m
[31m-[m
[31m-[m
[31m-        quarterly = detect_quarterly_data(df_filtered)[m
[31m-[m
[31m-        fig = build_market_chart([m
[31m-            df_filtered,[m
[31m-            title,[m
[31m-            chart_type,[m
[31m-            delta_type,[m
[31m-            quarterly=quarterly,[m
[31m-        )[m
[31m-[m
[31m-        display_market_chart(fig, "Source: Yahoo Finance")[m
\ No newline at end of file[m
[32m+[m[32mdef render_crypto_page():[m
[32m+[m[32m    render_market_page([m
[32m+[m[32m        market_map=CRYPTO_MAP,[m
[32m+[m[32m        category_map=CRYPTO_CATEGORY_MAP,[m
[32m+[m[32m        compare_map=CRYPTO_COMPARE_MAP,[m
[32m+[m[32m        page_key="crypto",[m
[32m+[m[32m        asset_label="Cryptocurrency",[m
[32m+[m[32m    )[m
\ No newline at end of file[m
