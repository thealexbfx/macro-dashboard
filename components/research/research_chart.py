import streamlit as st


def render_research_chart(
    figure,
    source=None,
    chart_controls=None,
):
    # A real Streamlit container, rather than an HTML div opened
    # in one call and closed in another.
    with st.container(
        key="research_chart_card",
        border=True,
    ):
        if chart_controls:
            chart_controls()

        st.plotly_chart(
            figure,
            use_container_width=True,
            config={
                "displaylogo": False,
                "displayModeBar": False,
                "responsive": True,
                "scrollZoom": False,
            },
        )

        st.markdown(
            f"""
            <div class="ml-chart-footer">
                <span>{source or ""}</span>
                <span>macrolensresearch.com</span>
            </div>
            """,
            unsafe_allow_html=True,
        )