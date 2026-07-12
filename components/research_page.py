import streamlit as st


def render_stat_tile(label, value):
    st.markdown(
        f"""
        <div class="ml-stat-tile">
            <div class="ml-stat-label">{label}</div>
            <div class="ml-stat-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_analysis_bar(stats):
    st.markdown("<div class='ml-analysis-bar'>", unsafe_allow_html=True)

    cols = st.columns(len(stats))

    for col, (label, value) in zip(cols, stats.items()):
        with col:
            render_stat_tile(label, value)

    st.markdown("</div>", unsafe_allow_html=True)


def render_list_card(title, items):
    st.markdown(f"<div class='ml-bottom-card'><h3>{title}</h3>", unsafe_allow_html=True)

    for item in items:
        st.markdown(f"<p>{item}</p>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_price_card(title, price_changes):
    st.markdown(f"<div class='ml-bottom-card'><h3>{title}</h3>", unsafe_allow_html=True)

    for period, change in price_changes.items():
        st.markdown(f"<p><b>{period}:</b> {change}</p>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)


def render_research_page(
    title,
    description,
    stats,
    fig,
    source,
    related_markets,
    price_changes,
    key_drivers,
    display_chart_func,
    chart_controls=None,
):
    st.markdown("<div class='ml-chart-card'>", unsafe_allow_html=True)

    if chart_controls:
        chart_controls()

    display_chart_func(fig, source)

    st.markdown("</div>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)

    with c1:
        render_list_card("Related Markets", related_markets)

    with c2:
        render_price_card("Price Changes", price_changes)

    with c3:
        render_list_card("Key Drivers", key_drivers)