from pathlib import Path
import streamlit as st


def inject_global_css():
    st.markdown(
        "<style>"
        + Path(__file__).with_name("product.css").read_text(encoding="utf-8")
        + "</style>",
        unsafe_allow_html=True,
    )
