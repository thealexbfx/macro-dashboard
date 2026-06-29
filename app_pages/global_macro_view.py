import streamlit as st
from datetime import datetime

from models.usa_growth import analyze_usa_growth
from models.usa_inflation import analyze_usa_inflation
from models.usa_labor import analyze_usa_labor
from models.usa_policy import analyze_usa_policy
from models.usa_liquidity import analyze_usa_liquidity


def render_country_macro_card(country, regime, growth, inflation, labor, policy, liquidity):
    html = f"""
    <div class="ml-card" style="min-height:210px;">
        <div class="small-label">{country}</div>
        <h3 style="font-size:24px; font-weight:900; margin:8px 0 14px 0;">
            {regime}
        </h3>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-size:14px;">
            <div><div class="small-label">Growth</div><b>{growth}</b></div>
            <div><div class="small-label">Inflation</div><b>{inflation}</b></div>
            <div><div class="small-label">Labor</div><b>{labor}</b></div>
            <div><div class="small-label">Policy</div><b>{policy}</b></div>
            <div><div class="small-label">Liquidity</div><b>{liquidity}</b></div>
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_global_macro_view():
    st.markdown("## Global Macro View")
    st.caption(f"Last updated: {datetime.now().strftime('%B %Y')}")

    growth = analyze_usa_growth()
    inflation = analyze_usa_inflation()
    labor = analyze_usa_labor()
    policy = analyze_usa_policy()
    liquidity = analyze_usa_liquidity()

    st.markdown(
        f"""
        <div class="hero-panel">
            <h1>Global macro regimes, country by country.</h1>
            <p>
                MacroLens tracks growth, inflation, labor, policy and liquidity to classify
                the current macro environment across major economies.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Current global snapshot</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        render_country_macro_card(
            country="United States",
            regime=f"{growth['regime']} / {inflation['regime']}",
            growth=growth["regime"],
            inflation=inflation["regime"],
            labor=labor["regime"],
            policy=policy["summary"],
            liquidity=liquidity["regime"],
        )

    with col2:
        render_country_macro_card(
            country="Euro Area",
            regime="Model Coming Soon",
            growth="Pending",
            inflation="Pending",
            labor="Pending",
            policy="Pending",
            liquidity="Pending",
        )

    with col3:
        render_country_macro_card(
            country="United Kingdom",
            regime="Model Coming Soon",
            growth="Pending",
            inflation="Pending",
            labor="Pending",
            policy="Pending",
            liquidity="Pending",
        )

    with col4:
        render_country_macro_card(
            country="Japan",
            regime="Model Coming Soon",
            growth="Pending",
            inflation="Pending",
            labor="Pending",
            policy="Pending",
            liquidity="Pending",
        )

    st.markdown('<div class="section-title">United States model summary</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="dark-regime-card">
            <div class="small-label" style="color:#94a3b8;">Current Model View</div>
            <h2>{growth["regime"]} / {inflation["regime"]}</h2>
            <p style="color:#cbd5e1; font-size:14px; line-height:1.65; margin-top:14px;">
                The US macro model currently shows <b>{growth["regime"]}</b> growth,
                <b>{inflation["regime"]}</b> inflation, <b>{labor["regime"]}</b> labor conditions,
                <b>{policy["summary"]}</b> policy, and <b>{liquidity["regime"]}</b> liquidity.
            </p>
            <div style="margin-top:18px; display:grid; grid-template-columns: repeat(5, 1fr); gap:12px;">
                <div><div class="small-label" style="color:#94a3b8;">Growth</div><b>{growth["total_score"]:.2f}</b></div>
                <div><div class="small-label" style="color:#94a3b8;">Inflation</div><b>{inflation["total_score"]:.2f}</b></div>
                <div><div class="small-label" style="color:#94a3b8;">Labor</div><b>{labor["total_score"]:.2f}</b></div>
                <div><div class="small-label" style="color:#94a3b8;">Policy</div><b>{policy["stance"]["total_score"]:.2f}</b></div>
                <div><div class="small-label" style="color:#94a3b8;">Liquidity</div><b>{liquidity["total_score"]:.2f}</b></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">How to read this page</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="ml-card">
            <p style="font-size:14px; line-height:1.7; color:#475569; margin:0;">
                Global Macro View is designed to compare macro regimes across economies.
                The Regime Monitor provides the detailed model breakdown for each pillar.
                Over time, this page will expand beyond the United States as full pillar models
                are built for the Euro Area, United Kingdom and Japan.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )