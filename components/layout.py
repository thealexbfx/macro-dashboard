"""Three stable product routes with explicit legacy migration."""

import streamlit as st

NAV_ITEMS = {
    "MacroLens": [
        ("Today", "Today"),
        ("Investigate", "Investigate"),
        ("MyResearch", "My Research"),
    ]
}


def resolve_page(page):
    if page in {"Today", "Investigate", "MyResearch"}:
        return page
    if page in {"ResearchNotes"}:
        return "MyResearch"
    if page in {
        "ResearchWorkspace",
        "HistoricalRegimeExplorer",
        "UnitedStates",
        "EuroArea",
        "UnitedKingdom",
        "Japan",
        "RatesBonds",
        "Equities",
        "Commodities",
        "FX",
        "Crypto",
    }:
        return "Investigate"
    return "Today"


def _nav_link(key, label, active):
    current = ' aria-current="page"' if key == active else ""
    return f'<a href="?page={key}" target="_self"{current}>{label}</a>'


def render_navigation(page):
    st.html(
        '<nav aria-label="Main navigation"><strong>MacroLens</strong>'
        + "".join(_nav_link(k, v, page) for k, v in NAV_ITEMS["MacroLens"])
        + "</nav>"
    )
