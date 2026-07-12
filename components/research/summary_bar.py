import streamlit as st


def render_summary_bar(stats: dict):
    items_html = ""

    for label, value in stats.items():
        items_html += f"""
        <div class="ml-summary-item">
            <div class="ml-summary-label">{label}</div>
            <div class="ml-summary-value">{value}</div>
        </div>
        """

    st.markdown(
        f"""
        <div class="ml-summary-bar">
            {items_html}
        </div>
        """,
        unsafe_allow_html=True,
    )