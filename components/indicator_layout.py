import streamlit as st


def render_analysis_bar(stats):
    items = [
        ("Latest", stats.get("latest", "—")),
        ("Trend", stats.get("trend", "—")),
        ("Position", stats.get("position", "—")),
        ("Significance", stats.get("significance", "—")),
        ("1M Change", stats.get("change_1m", "—")),
        ("1Y Change", stats.get("change_1y", "—")),
    ]

    html = "<div class='ml-analysis-bar'>"
    for label, value in items:
        html += f"""
        <div class='ml-analysis-item'>
            <div class='ml-analysis-label'>{label}</div>
            <div class='ml-analysis-value'>{value}</div>
        </div>
        """
    html += "</div>"

    st.markdown(html, unsafe_allow_html=True)


def render_bottom_cards(related_markets=None, price_changes=None, key_drivers=None):
    related_markets = related_markets or ["DXY", "Real Yields", "FedWatch"]
    price_changes = price_changes or {"1D": "—", "1W": "—", "1M": "—", "6M": "—"}
    key_drivers = key_drivers or ["Dollar", "Rates", "Inflation", "Risk sentiment"]

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("<div class='ml-bottom-card'><h3>Related Markets</h3>", unsafe_allow_html=True)
        for item in related_markets:
            st.markdown(f"<p>{item}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown("<div class='ml-bottom-card'><h3>Price Changes</h3>", unsafe_allow_html=True)
        for label, value in price_changes.items():
            st.markdown(f"<p><b>{label}</b>: {value}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with c3:
        st.markdown("<div class='ml-bottom-card'><h3>Key Drivers</h3>", unsafe_allow_html=True)
        for item in key_drivers:
            st.markdown(f"<p>{item}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_indicator_layout(
    title,
    description,
    stats,
    fig,
    chart_controls_func=None,
    related_markets=None,
    price_changes=None,
    key_drivers=None,
):
    st.markdown(f"<h1 class='ml-page-title'>{title}</h1>", unsafe_allow_html=True)

    if description:
        st.markdown(f"<p class='ml-page-description'>{description}</p>", unsafe_allow_html=True)

    render_analysis_bar(stats)

    st.markdown("<div class='ml-chart-card'>", unsafe_allow_html=True)

    if chart_controls_func:
        chart_controls_func()

    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)

    render_bottom_cards(
        related_markets=related_markets,
        price_changes=price_changes,
        key_drivers=key_drivers,
    )