from __future__ import annotations

from datetime import date

import streamlit as st

from components.macro_engine.environment_overview import (
    render_macro_environment_overview,
)
from macro_engine.engine.validation_engine import (
    build_environment_validation_summary,
    build_regime_transition_summary,
    build_stability_validation_summary,
)
from app_pages.macro_engine.loaders import (
    STANDARD_HISTORY_START_DATE,
    load_usa_environment_history,
    load_usa_macro_environment,
)

HISTORY_START_DATE = STANDARD_HISTORY_START_DATE


def render_usa_macro_engine_page() -> None:
    """
    Render the United States Macro Engine page.

    The environment and historical pipelines are each called once and
    cached. Validation summaries are built once from the completed
    historical result and passed into the UI without recalculation.
    """
    today = date.today()

    with st.spinner(
        "Running the United States Macro Engine..."
    ):
        result = load_usa_macro_environment()

    with st.spinner("Loading environment history..."):
        history_run = load_usa_environment_history(
            start_date=HISTORY_START_DATE,
            end_date=today,
        )

    history = getattr(history_run, "history", None)

    if history is None or not history.snapshots:
        st.error(
            "Validation could not be generated because no successful "
            "historical environment snapshots are available."
        )
        return

    environment_validation = (
        build_environment_validation_summary(history)
    )

    stability_validation = (
        build_stability_validation_summary(history)
    )

    transition_validation = (
        build_regime_transition_summary(history)
    )

    render_macro_environment_overview(
        result=result,
        history_run=history_run,
        environment_validation=environment_validation,
        stability_validation=stability_validation,
        transition_validation=transition_validation,
    )
