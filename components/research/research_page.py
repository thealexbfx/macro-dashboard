import streamlit as st

from .summary_bar import render_summary_bar
from .research_chart import render_research_chart
from .bottom_cards import render_bottom_cards


def render_research_page(
    title,
    description,
    stats,
    figure,
    source,
    cards,
    chart_controls=None,
    show_header=True,
):
    if show_header:
        st.markdown(
            f"""
            <div class="ml-research-header">
                <h1>{title}</h1>
                <p>{description}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    render_summary_bar(stats)

    render_research_chart(
        figure=figure,
        source=source,
        chart_controls=chart_controls,
    )

    render_bottom_cards(cards)