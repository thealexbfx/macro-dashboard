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
from macro_engine.pipelines.environment import (
    run_usa_macro_environment,
)
from macro_engine.pipelines.history import (
    run_usa_environment_history,
)


HISTORY_START_DATE = date(2024, 1, 1)


@st.cache_data(ttl=1800, show_spinner=False)
def _load_usa_macro_environment():
    return run_usa_macro_environment()


@st.cache_data(ttl=1800, show_spinner=False)
def _load_usa_environment_history(
    start_date: date,
    end_date: date,
):
    return run_usa_environment_history(
        start_date=start_date,
        end_date=end_date,
        frequency="monthly",
        continue_on_error=True,
    )


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
        result = _load_usa_macro_environment()

    with st.spinner("Loading environment history..."):
        history_run = _load_usa_environment_history(
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