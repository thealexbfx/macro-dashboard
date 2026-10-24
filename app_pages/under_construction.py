"""Honest unavailable state with useful routes back into the working product."""
import streamlit as st


def render_under_construction_page(page_name):
    st.title(page_name)
    st.info("This tool is not available yet. No live analysis is provided on this page.")
    st.write("Continue with a working research tool:")
    st.markdown("[Compare current economies](?page=MacroEngineGlobal) · [Explore historical environments](?page=HistoricalRegimeExplorer) · [Create or reopen an investigation](?page=ResearchWorkspace)")
