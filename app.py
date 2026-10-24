"""Production entry: three jobs, no dashboard/model-page imports."""

import streamlit as st
from components.layout import render_navigation, resolve_page
from components.product import render_today
from components.chart_workspace import render_investigate, render_chart_research
from styles.theme import inject_global_css

st.set_page_config(page_title="MacroLens", page_icon="logo_favicon.png", layout="wide")
inject_global_css()
raw = st.query_params.get("page", "Today")
page = resolve_page(raw)
render_navigation(page)
if raw != page:
    st.caption(
        "This older link now opens the simplified research workflow. Your saved records are unchanged."
    )
if page == "Today":
    render_today()
elif page == "Investigate":
    render_investigate()
else:
    render_chart_research()
