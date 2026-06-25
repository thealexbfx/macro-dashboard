import streamlit as st

from components.cards import (
    render_pillar_card,
    render_market_tile,
    render_country_card,
    render_framework_step,
)


def render_home_page():
    st.markdown(
        """
        <div class="hero-panel">
            <h1>Global macro regimes, translated into market signals.</h1>
            <p>
                MacroLens Research tracks growth, inflation, labor, policy and liquidity
                across major economies to identify macro regimes, policy cycles and
                cross-asset implications.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Macro regime dashboard</div>', unsafe_allow_html=True)

    cols = st.columns(5)

    pillar_data = [
        ("Growth", "Improving", 0.68, "Activity momentum is firming across key economic indicators."),
        ("Inflation", "Elevated", 0.74, "Price pressure remains above target despite cooling from cycle highs."),
        ("Labor", "Stable", 0.56, "Labor conditions remain resilient, but momentum is no longer accelerating."),
        ("Policy", "Restrictive", 0.82, "Central-bank policy remains tight relative to the growth backdrop."),
        ("Liquidity", "Neutral", 0.49, "Liquidity conditions are mixed, with no clear easing impulse yet."),
    ]

    for col, data in zip(cols, pillar_data):
        with col:
            render_pillar_card(*data)

    st.markdown('<div class="section-title">Current macro environment</div>', unsafe_allow_html=True)

    left, right = st.columns([1.25, 1])

    with left:
        st.markdown(
            """
            <div class="dark-regime-card">
                <div class="small-label" style="color:#94a3b8;">Overall regime</div>
                <h2>Late-cycle resilience <span class="badge">Model View</span></h2>
                <p style="color:#cbd5e1; font-size:14px; line-height:1.65; margin-top:14px;">
                    Growth remains positive, inflation is still above target and policy
                    remains restrictive. This creates a macro environment where asset
                    markets are sensitive to changes in inflation momentum, central-bank
                    guidance and liquidity conditions.
                </p>
                <div style="margin-top:18px; display:grid; grid-template-columns: repeat(3, 1fr); gap:12px;">
                    <div>
                        <div class="small-label" style="color:#94a3b8;">Cycle</div>
                        <b>Late Expansion</b>
                    </div>
                    <div>
                        <div class="small-label" style="color:#94a3b8;">Policy Bias</div>
                        <b>Restrictive</b>
                    </div>
                    <div>
                        <div class="small-label" style="color:#94a3b8;">Risk Bias</div>
                        <b>Selective</b>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
            <div class="ml-card" style="min-height:245px;">
                <div class="small-label">MacroLens takeaway</div>
                <h3 style="margin:10px 0 10px 0; font-size:22px; font-weight:900;">
                    The key question is not whether growth is positive.
                </h3>
                <p style="font-size:14px; line-height:1.7; color:#475569;">
                    The key question is whether growth is strong enough to absorb
                    restrictive policy while inflation remains above target. MacroLens
                    focuses on the interaction between the pillars, not isolated data points.
                </p>
                <div class="insight-box">
                    Framework: Indicators → Direction → Magnitude → Breadth → Regime → Market Implications
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="section-title">Market snapshot</div>', unsafe_allow_html=True)

    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        render_market_tile("DXY", "105.20", 0.18)
    with m2:
        render_market_tile("S&P 500", "5,480", 0.42)
    with m3:
        render_market_tile("10Y Yield", "4.31%", -0.06)
    with m4:
        render_market_tile("Gold", "2,335", 0.31)
    with m5:
        render_market_tile("Bitcoin", "64,200", -1.15)

    st.markdown('<div class="section-title">MacroLens framework</div>', unsafe_allow_html=True)

    f1, f2, f3, f4, f5, f6 = st.columns(6)

    steps = [
        ("1", "Indicators", "Collect economic and market data across major macro pillars."),
        ("2", "Direction", "Identify whether each series is improving, slowing, rising or falling."),
        ("3", "Magnitude", "Measure the size of the move relative to history."),
        ("4", "Breadth", "Check whether the signal is narrow or broad across indicators."),
        ("5", "Regime", "Combine signals into a macro environment classification."),
        ("6", "Markets", "Translate regimes into cross-asset implications."),
    ]

    for col, step in zip([f1, f2, f3, f4, f5, f6], steps):
        with col:
            render_framework_step(*step)

    st.markdown('<div class="section-title">Global macro snapshot</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        render_country_card("United States", "Late-cycle resilience", "Improving", "Elevated", "Restrictive")
    with c2:
        render_country_card("Euro Area", "Pending", "Pending", "Pending", "Pending")
    with c3:
        render_country_card("United Kingdom", "Pending", "Pending", "Pending", "Pending")
    with c4:
        render_country_card("Japan", "Pending", "Pending", "Pending", "Pending")

    st.markdown('<div class="section-title">Featured research</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns([1.4, 1])

    with col_a:
        st.markdown(
            """
            <div class="ml-card" style="min-height:220px;">
                <div class="small-label">Chart of the week</div>
                <h3 style="font-size:23px; font-weight:900; margin:10px 0;">
                    2022 vs 2026: a different inflation backdrop
                </h3>
                <p style="font-size:14px; line-height:1.7; color:#475569;">
                    Inflation may still be above target, but the composition, policy backdrop
                    and growth environment are different from the 2022 inflation shock. This
                    matters for how markets interpret central-bank reaction functions.
                </p>
                <div class="insight-box">
                    Coming soon: chart cards will combine data, model signal and written interpretation.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_b:
        st.markdown(
            """
            <div class="ml-card" style="min-height:220px;">
                <div class="small-label">Research focus</div>
                <h3 style="font-size:23px; font-weight:900; margin:10px 0;">
                    From dashboard to research platform
                </h3>
                <p style="font-size:14px; line-height:1.7; color:#475569;">
                    MacroLens is designed to move beyond displaying charts. The goal is to
                    explain what the data means, how the regime is changing and why it
                    matters for markets.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )