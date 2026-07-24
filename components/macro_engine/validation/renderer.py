from __future__ import annotations

from typing import Any

import streamlit as st

from .stability import render_stability_analysis
from .summary import render_validation_summary


def render_validation(
    *,
    environment_validation: Any,
    stability_validation: Any,
    transition_validation: Any,
) -> None:
    """
    Render the Validation section.

    This component orchestrates the individual validation panels.
    All calculations are performed by the Validation Engine before
    reaching this layer.
    """

    st.markdown("## Validation")

    st.markdown(
        (
            '<div class="ml-section-description">'
            "The Validation section evaluates the historical behaviour "
            "of the Macro Engine, summarising regime persistence, "
            "stability and transition characteristics without "
            "introducing any additional model calculations."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    render_validation_summary(
        environment_validation=environment_validation,
    )

    st.markdown(
        '<hr class="ml-section-divider">',
        unsafe_allow_html=True,
    )

    render_stability_analysis(
        stability_validation=stability_validation,
    )

    # Transition Analysis and Methodology are added next.