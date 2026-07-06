import streamlit as st
from pathlib import Path


CSS_FILES = [
    "base.css",
    "sidebar.css",
    "cards.css",
    "tables.css",
    "buttons.css",
    "dashboard.css",
    "charts.css",
]


def inject_global_css():
    styles_dir = Path(__file__).parent
    css = ""

    for file_name in CSS_FILES:
        css_path = styles_dir / file_name
        if css_path.exists():
            css += css_path.read_text(encoding="utf-8") + "\n"

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)