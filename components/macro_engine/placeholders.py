import streamlit as st


def render_history_placeholder() -> None:
    st.markdown("## Environment History")

    st.markdown(
        (
            '<div class="ml-placeholder">'
            "The existing History Engine output will be connected here."
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_validation_placeholder() -> None:
    st.markdown("## Validation")

    st.markdown(
        (
            '<div class="ml-placeholder">'
            "The existing Validation Engine output will be connected here."
            "</div>"
        ),
        unsafe_allow_html=True,
    )