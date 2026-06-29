import streamlit as st
from datetime import datetime

from app_pages.macro_models import build_global_macro_table
from models.country_analysis import (
    analyze_usa,
    analyze_uk,
    analyze_euro,
    analyze_japan,
)


def render_global_macro_view():
    st.markdown("## Global Macro View")
    st.caption(f"Last updated: {datetime.now().strftime('%B %Y')}")

    st.markdown("""
    <div style="
        padding:24px;
        border-radius:16px;
        background:#0b1320;
        color:white;
        margin-bottom:20px;
    ">
        <div style="font-size:13px; letter-spacing:0.08em; text-transform:uppercase; color:#94a3b8;">
            Current Global Regime
        </div>
        <div style="font-size:34px; font-weight:800; margin-top:6px;">
            Model Output in Progress
        </div>
        <div style="font-size:15px; color:#cbd5e1; margin-top:8px;">
            This page is now beginning to move from static dashboard content toward model-driven
            macro signals across growth, inflation, and policy.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Macro Pillars")

    col1, col2, col3 = st.columns(3)

    pillars = [
        ("Growth", "Model Driven", "Tracks whether economic activity is improving, slowing, or neutral."),
        ("Inflation", "Model Driven", "Tracks whether inflation pressure is rising, cooling, or neutral."),
        ("Policy", "Model Driven", "Tracks whether policy is restrictive, accommodative, or unavailable."),
        ("Labor", "Later", "Labor-market signal will be added after the first model version is stable."),
        ("Liquidity", "Later", "Liquidity and financial conditions will be added in a later version."),
        ("Market Pricing", "Later", "Market-implied signals will be added after macro signals are working."),
    ]

    for i, (title, status, text) in enumerate(pillars):
        col = [col1, col2, col3][i % 3]
        with col:
            st.markdown(f"""
            <div style="
                border:1px solid #e5e7eb;
                border-radius:14px;
                padding:18px;
                margin-bottom:14px;
                background:white;
                min-height:145px;
            ">
                <div style="font-size:13px; color:#64748b; font-weight:700; text-transform:uppercase;">
                    {title}
                </div>
                <div style="font-size:24px; font-weight:800; margin:6px 0;">
                    {status}
                </div>
                <div style="font-size:14px; color:#374151; line-height:1.45;">
                    {text}
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### Regional Scorecard")

    try:
        macro_table = build_global_macro_table(
            usa=analyze_usa(),
            uk=analyze_uk(),
            euro=analyze_euro(),
            japan=analyze_japan(),
        )

        cols = st.columns(4)

        for i, row in macro_table.iterrows():
            with cols[i]:
                with st.container(border=True):
                    st.markdown(f"### {row['Country']}")
                    st.markdown(f"**Growth:** {row['Growth']}")
                    st.markdown(f"**Inflation:** {row['Inflation']}")
                    st.markdown(f"**Policy:** {row['Policy']}")

        with st.expander("View raw model output"):
            st.dataframe(macro_table, use_container_width=True, hide_index=True)

    except Exception:
        st.error("Global macro model is temporarily unavailable.")

    st.markdown("### Next Model Improvements")

    st.markdown("""
    - Add better scoring logic for growth and inflation.
    - Separate labor from growth.
    - Add policy direction, not just policy level.
    - Add market signals later.
    - Add analyst interpretation after model output is stable.
    """)