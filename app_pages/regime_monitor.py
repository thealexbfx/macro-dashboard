import streamlit as st
from datetime import datetime

from models.usa_growth import analyze_usa_growth
from models.usa_inflation import analyze_usa_inflation
from models.usa_labor import analyze_usa_labor
from models.usa_policy import analyze_usa_policy
from models.usa_liquidity import analyze_usa_liquidity

from components.cards import render_pillar_card


def render_regime_monitor_page():
    st.markdown("## Regime Monitor")
    st.caption(f"Last updated: {datetime.now().strftime('%B %Y')}")

    growth = analyze_usa_growth()
    inflation = analyze_usa_inflation()
    labor = analyze_usa_labor()
    policy = analyze_usa_policy()
    liquidity = analyze_usa_liquidity()

    pillar_data = [
        (
            "Growth",
            growth["regime"],
            growth["total_score"],
            f"Growth breadth is {growth['breadth'].lower()} across {growth['total_indicators']} indicators."
        ),
        (
            "Inflation",
            inflation["regime"],
            inflation["total_score"],
            f"Inflation breadth is {inflation['breadth'].lower()} across {inflation['total_indicators']} indicators."
        ),
        (
            "Labor",
            labor["regime"],
            labor["total_score"],
            f"Labor breadth is {labor['breadth'].lower()} across {labor['total_indicators']} indicators."
        ),
        (
            "Policy",
            policy["summary"],
            policy["stance"]["total_score"],
            f"Policy stance is {policy['stance']['regime']} and direction is {policy['direction']['regime']}."
        ),
        (
            "Liquidity",
            liquidity["regime"],
            liquidity["total_score"],
            f"Liquidity breadth is {liquidity['breadth'].lower()} across {liquidity['total_indicators']} indicators."
        ),
    ]

    cols = st.columns(5)

    for col, data in zip(cols, pillar_data):
        with col:
            render_pillar_card(*data)

    st.markdown('<div class="section-title">Current macro environment</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="dark-regime-card">
            <div class="small-label" style="color:#94a3b8;">Model View</div>
            <h2>{growth["regime"]} / {inflation["regime"]}</h2>
            <p style="color:#cbd5e1; font-size:14px; line-height:1.65; margin-top:14px;">
                Growth is currently classified as <b>{growth["regime"]}</b>, inflation as
                <b>{inflation["regime"]}</b>, labor as <b>{labor["regime"]}</b>,
                policy as <b>{policy["summary"]}</b>, and liquidity as
                <b>{liquidity["regime"]}</b>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-title">Model details</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Growth",
        "Inflation",
        "Labor",
        "Policy",
        "Liquidity",
    ])

    with tab1:
        st.dataframe(growth["details"], use_container_width=True, hide_index=True)

    with tab2:
        st.dataframe(inflation["details"], use_container_width=True, hide_index=True)

    with tab3:
        st.dataframe(labor["details"], use_container_width=True, hide_index=True)

    with tab4:
        st.markdown("#### Policy Stance")
        st.dataframe(policy["stance"]["details"], use_container_width=True, hide_index=True)

        st.markdown("#### Policy Direction")
        st.dataframe(policy["direction"]["details"], use_container_width=True, hide_index=True)

    with tab5:
        st.dataframe(liquidity["details"], use_container_width=True, hide_index=True)