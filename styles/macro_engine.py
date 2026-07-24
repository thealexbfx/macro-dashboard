from pathlib import Path

import streamlit as st


CSS_PATH = Path(__file__).with_name("macro_engine.css")


def inject_macro_engine_css() -> None:
    """
    Load and inject Macro Engine styling.

    Keeping CSS in a standalone file makes the visual layer easier
    to maintain without mixing styling into Python components.
    """
    try:
        css = CSS_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        st.warning(
            f"Macro Engine styling could not be loaded: {exc}"
        )
        return

    st.markdown(
        f"<style>{css}</style>",
        unsafe_allow_html=True,
    )