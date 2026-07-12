import streamlit as st
from datetime import datetime

from models.usa_growth import analyze_usa_growth
from models.usa_inflation import analyze_usa_inflation
from models.usa_labor import analyze_usa_labor
from models.usa_policy import analyze_usa_policy
from models.usa_liquidity import analyze_usa_liquidity


def render_country_macro_card(country, flag, regime, growth, inflation, labor, policy, liquidity):
    html = f"""
    <div class="ml-card" style="min-height:230px;">
        <div style="font-size:26px; margin-bottom:8px;">{flag}</div>
        <div class="small-label">{country}</div>

        <h3 style="font-size:22px; font-weight:950; margin:10px 0 18px 0; line-height:1.15;">
            {regime}
        </h3>

        <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px 18px; font-size:14px;">
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
    st.markdown("## Global Macro Outlook")
    st.caption(f"Last updated: {datetime.now().strftime('%B %Y')}")

    growth = analyze_usa_growth()
    inflation = analyze_usa_inflation()
    labor = analyze_usa_labor()
    policy = analyze_usa_policy()
    liquidity = analyze_usa_liquidity()

    st.markdown(
        """
        <div class="hero-panel">
            <div class="small-label">GLOBAL MACRO OUTLOOK</div>
            <h1>Macro regimes, translated into signals.</h1>
            <p>
                MacroLens tracks growth, inflation, labor, policy and liquidity across major economies
                to classify the current macro environment and identify cross-asset implications.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Macro Pillars</div>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)

    pillar_cards = [
        ("Growth", growth["regime"], growth["total_score"]),
        ("Inflation", inflation["regime"], inflation["total_score"]),
        ("Labor", labor["regime"], labor["total_score"]),
        ("Policy", policy["summary"], policy["stance"]["total_score"]),
        ("Liquidity", liquidity["regime"], liquidity["total_score"]),
    ]

    for col, (name, regime, score) in zip([c1, c2, c3, c4, c5], pillar_cards):
        with col:
            st.markdown(
                f"""
                <div class="ml-card" style="min-height:150px;">
                    <div class="small-label">{name}</div>
                    <h3 style="font-size:20px; font-weight:900; margin:8px 0;">{regime}</h3>
                    <div style="font-size:30px; font-weight:950;">{score:.2f}</div>
                    <div class="small-label">Model Score</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div class="section-title">Regional Scorecard</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="ml-card">
            <table style="width:100%; border-collapse:collapse; font-size:14px;">
                <thead>
                    <tr style="text-align:left; color:#64748b;">
                        <th>Economy</th>
                        <th>Growth</th>
                        <th>Inflation</th>
                        <th>Labor</th>
                        <th>Policy</th>
                        <th>Liquidity</th>
                        <th>Overall Regime</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><b>🇺🇸 United States</b></td>
                        <td>{growth["regime"]}<br><b>{growth["total_score"]:.2f}</b></td>
                        <td>{inflation["regime"]}<br><b>{inflation["total_score"]:.2f}</b></td>
                        <td>{labor["regime"]}<br><b>{labor["total_score"]:.2f}</b></td>
                        <td>{policy["summary"]}<br><b>{policy["stance"]["total_score"]:.2f}</b></td>
                        <td>{liquidity["regime"]}<br><b>{liquidity["total_score"]:.2f}</b></td>
                        <td><b>{growth["regime"]} / {inflation["regime"]}</b></td>
                    </tr>
                    <tr>
                        <td><b>🇪🇺 Euro Area</b></td>
                        <td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Model Coming Soon</td>
                    </tr>
                    <tr>
                        <td><b>🇬🇧 United Kingdom</b></td>
                        <td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Model Coming Soon</td>
                    </tr>
                    <tr>
                        <td><b>🇯🇵 Japan</b></td>
                        <td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Pending</td><td>Model Coming Soon</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([2, 1])

    with left:
        st.markdown('<div class="section-title">Current Global Snapshot</div>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            render_country_macro_card(
                "United States", "🇺🇸",
                f"{growth['regime']} / {inflation['regime']}",
                growth["regime"], inflation["regime"], labor["regime"],
                policy["summary"], liquidity["regime"],
            )

        with col2:
            render_country_macro_card("Euro Area", "🇪🇺", "Model Coming Soon", "Pending", "Pending", "Pending", "Pending", "Pending")

        with col3:
            render_country_macro_card("United Kingdom", "🇬🇧", "Model Coming Soon", "Pending", "Pending", "Pending", "Pending", "Pending")

        with col4:
            render_country_macro_card("Japan", "🇯🇵", "Model Coming Soon", "Pending", "Pending", "Pending", "Pending", "Pending")

    with right:
        st.markdown('<div class="section-title">Regime Summary</div>', unsafe_allow_html=True)

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
            </div>
            """,
            unsafe_allow_html=True,
        )