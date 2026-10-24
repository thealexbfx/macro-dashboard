"""Consistent orientation without changing bookmarked production routes."""

import streamlit as st

PURPOSES = {
    "MacroEngineGlobal": "Compare economies, then open a regional model view to inspect the underlying pillars.",
    "ActiveIdeas": "Review what changed, then open an asset in Research Workspace to assess the evidence.",
    "ResearchWorkspace": "Start from a model view or investigate your own question. Neither establishes causation or future returns.",
    "HistoricalRegimeExplorer": "Select an environment and horizon to inspect historical conditional outcomes and sample sizes.",
}
MODEL_NOTE = "Model confidence describes classification agreement and coverage, not a calibrated probability of future market direction. Conviction is signal strength; historical support is descriptive sample evidence."


def render_page_context(page):
    text = PURPOSES.get(page)
    if page.startswith("MacroEngine") and page != "MacroEngineGlobal":
        text = "Review the regional environment, then inspect each pillar and its underlying indicators."
    if page in {"UnitedStates", "EuroArea", "UnitedKingdom", "Japan"}:
        text = "Choose an economic indicator, inspect its source and units, then compare it with another series."
    if page in {"RatesBonds", "Equities", "Commodities", "FX", "Crypto"}:
        text = "Choose a market series and sample, then inspect levels or compare economically appropriate changes."
    if text:
        st.caption(text)
    if page.startswith("MacroEngine") or page in {
        "ActiveIdeas",
        "ResearchWorkspace",
        "HistoricalRegimeExplorer",
    }:
        with st.expander("How to interpret model and historical evidence"):
            st.write(MODEL_NOTE)
            st.caption(
                "Latest-vintage economic data can be revised. Historical conditional outcomes may overlap and do not establish predictive accuracy."
            )
