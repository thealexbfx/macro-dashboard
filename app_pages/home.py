import streamlit as st

from components.cards import (
    render_pillar_card,
    render_market_tile,
    render_country_card,
)

from app_pages.home_market_data import get_home_market_snapshot, get_biggest_movers

def render_research_opportunities(movers):
    if movers.empty:
        st.info("Research opportunity data is temporarily unavailable.")
        return

    questions = {
        "Gold": "Why did gold move this much?",
        "DXY": "Is the dollar repricing Fed expectations?",
        "S&P 500": "Is equities weakness broad or sector specific?",
        "10Y": "Are yields reacting to growth or inflation?",
        "Bitcoin": "Is crypto reacting to liquidity or risk sentiment?",
    }

    icons = {
        "Gold": "gold",
        "DXY": "dxy",
        "S&P 500": "sp",
        "10Y": "bond",
        "Bitcoin": "btc",
    }

    st.markdown(
        """
        <div class="research-header-row">
            <div></div>
            <div>Asset</div>
            <div>Move</div>
            <div>Unusualness</div>
            <div>Research question</div>
            <div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for idx, (_, row) in enumerate(movers.iterrows(), start=1):
        asset = row["Asset"]
        move = row["Move"]
        score = row["Volatility Score"]

        move_class = "positive" if move > 0 else "negative" if move < 0 else "neutral"
        question = questions.get(asset, "What macro driver explains this move?")
        icon = icons.get(asset, "●")

        st.markdown(
            f"""
            <div class="research-compact-row">
                <div class="research-rank">{idx}</div>
                <div class="research-asset">
                    <span class="asset-icon asset-{icon}"></span>
                    <span>{asset}</span>
                </div>
                <div class="research-move {move_class}">{move:+.2f}%</div>
                <div class="research-score {move_class}">{score:.2f}σ</div>
                <div class="research-question">{question}</div>
                <div class="research-arrow">→</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
def render_home_page():

    # Market Snapshot
    st.markdown(
        """
        <div class="home-title">
            <h1>Market Snapshot</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    market_snapshot = get_home_market_snapshot()
    cols = st.columns(len(market_snapshot))

    for col, item in zip(cols, market_snapshot):
        with col:
            render_market_tile(
                item["label"],
                item["value"],
                item["change_pct"],
                item["sparkline_df"],
                item["trend_positive"],
            )

    # Research Opportunities
    st.markdown(
        """
        <div class="home-section research-section">
            <h2>Research Opportunities</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        if "home_period" not in st.session_state:
            st.session_state.home_period = "1D"

        st.markdown('<div class="period-buttons">', unsafe_allow_html=True)

        c1, c2, c3, _ = st.columns([0.75, 0.75, 0.75, 7])

        with c1:
            if st.button("1D", key="period_1d"):
                st.session_state.home_period = "1D"

        with c2:
            if st.button("1W", key="period_1w"):
                st.session_state.home_period = "1W"

        with c3:
            if st.button("1M", key="period_1m"):
                st.session_state.home_period = "1M"

        st.markdown('</div>', unsafe_allow_html=True)

        period = st.session_state.home_period

    movers = get_biggest_movers(period=period)
    render_research_opportunities(movers)

    # Macro Regime Dashboard
    st.markdown(
        """
        <div class="home-section">
            <h2>Macro Regime Dashboard</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

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

    # Current Macro Environment
    st.markdown(
        """
        <div class="home-section">
            <h2>Current Macro Environment</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.15, 1])

    with left:
        st.markdown(
            """
            <div class="ml-card" style="min-height:245px;">
                <div class="small-label">Overall Regime</div>
                <h3 style="font-size:25px; font-weight:900; margin:10px 0; color:#f8fafc;">
                    Late-cycle resilience
                </h3>
                <p style="font-size:14px; line-height:1.7; color:#cbd5e1;">
                    Growth remains positive, inflation is still above target and policy remains restrictive.
                    This creates a macro environment where asset markets are sensitive to changes in
                    inflation momentum, central-bank guidance and liquidity conditions.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        st.markdown(
            """
            <div class="ml-card" style="min-height:245px;">
                <div class="small-label">MacroLens Takeaway</div>
                <h3 style="font-size:23px; font-weight:900; margin:10px 0; color:#f8fafc;">
                    Focus on the disconnect between the model and the market.
                </h3>
                <p style="font-size:14px; line-height:1.7; color:#cbd5e1;">
                    The research process starts by comparing macro conditions with asset price behavior.
                    When the data says one thing and markets say another, that disconnect becomes the
                    research question.
                </p>
                <div class="insight-box">
                    Market move → Macro driver → Regime context → Market implication
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Global Macro Snapshot
    st.markdown(
        """
        <div class="home-section">
            <h2>Global Macro Snapshot</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        render_country_card("United States", "Late-cycle resilience", "Improving", "Elevated", "Restrictive")
    with c2:
        render_country_card("Euro Area", "Pending", "Pending", "Pending", "Pending")
    with c3:
        render_country_card("United Kingdom", "Pending", "Pending", "Pending", "Pending")
    with c4:
        render_country_card("Japan", "Pending", "Pending", "Pending", "Pending")