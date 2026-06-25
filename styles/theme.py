import streamlit as st
from pathlib import Path


def inject_global_css():
    css_path = Path(__file__).parent / "theme.css"

    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)