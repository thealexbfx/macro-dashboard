import streamlit as st
from datetime import datetime


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
            Late-Cycle Disinflation
        </div>
        <div style="font-size:15px; color:#cbd5e1; margin-top:8px;">
            Growth is slowing, inflation remains sticky, labor markets are cooling,
            and policy remains restrictive.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Macro Pillars")

    col1, col2, col3 = st.columns(3)

    pillars = [
        ("Growth", "Slowing", "Growth momentum is moderating across major economies."),
        ("Inflation", "Sticky", "Inflation is no longer accelerating broadly, but remains above target."),
        ("Labor", "Cooling", "Labor markets remain resilient but are showing signs of softening."),
        ("Policy", "Restrictive", "Central banks remain cautious as real rates stay elevated."),
        ("Liquidity", "Tight", "Financial conditions remain restrictive relative to the post-pandemic period."),
        ("Market Pricing", "Soft Landing", "Risk assets appear to be pricing a benign slowdown."),
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

    st.dataframe(
        {
            "Region": ["United States", "Euro Area", "United Kingdom", "Japan"],
            "Growth": ["Slowing", "Weak", "Weak", "Improving"],
            "Inflation": ["Sticky", "Moderating", "Sticky", "Rising"],
            "Policy": ["Restrictive", "Restrictive", "Restrictive", "Normalizing"],
            "Macro View": [
                "Late-cycle slowdown",
                "Weak growth / easing bias",
                "Stagflation risk fading but growth weak",
                "Reflation / policy normalization",
            ],
        },
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Asset Allocation View")

    st.dataframe(
        {
            "Asset Class": ["Equities", "Bonds", "USD", "Gold", "Oil", "Credit"],
            "View": ["Neutral", "Positive", "Neutral", "Positive", "Neutral", "Neutral"],
            "Conviction": ["Medium", "High", "Medium", "Medium", "Low", "Medium"],
            "Reasoning": [
                "Supported by earnings resilience, but vulnerable to growth disappointment.",
                "Slowing growth and easing expectations support duration.",
                "Policy divergence is mixed across major economies.",
                "Supported by real-rate risk, policy uncertainty, and reserve diversification.",
                "Demand risks offset supply/geopolitical risks.",
                "Spreads remain contained but vulnerable if labor weakness accelerates.",
            ],
        },
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Key Risks")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        **Upside Risks**
        - Growth reaccelerates
        - Productivity improves
        - Inflation falls without labor damage
        """)

    with col2:
        st.markdown("""
        **Downside Risks**
        - Labor deterioration
        - Credit stress
        - Policy stays restrictive too long
        """)

    with col3:
        st.markdown("""
        **Watching Closely**
        - Core inflation
        - Initial claims
        - Yield curves
        - Credit spreads
        - Central bank guidance
        """)