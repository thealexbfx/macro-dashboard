from __future__ import annotations

import streamlit as st

from components.macro_engine.environment_overview import (
    render_macro_environment_overview,
)
from macro_engine.cache.storage import load_cache
from macro_engine.engine.validation_engine import (
    build_environment_validation_summary,
    build_regime_transition_summary,
    build_stability_validation_summary,
)


def render_japan_macro_engine_page() -> None:
    with st.spinner(
        "Loading Japan Macro Engine..."
    ):
        try:
            result = load_cache(
                "japan_environment"
            )

            history_run = load_cache(
                "japan_environment_history"
            )

        except FileNotFoundError:
            st.error(
                "The Japan model cache is not available. "
                "Run the MacroLens refresh process and try again."
            )
            return

    history = getattr(
        history_run,
        "history",
        None,
    )

    if history is None or not history.snapshots:
        st.error(
            "Validation could not be generated because no "
            "successful historical environment snapshots "
            "are available."
        )
        return

    environment_validation = (
        build_environment_validation_summary(
            history
        )
    )

    stability_validation = (
        build_stability_validation_summary(
            history
        )
    )

    transition_validation = (
        build_regime_transition_summary(
            history
        )
    )

    render_macro_environment_overview(
        result=result,
        history_run=history_run,
        environment_validation=environment_validation,
        stability_validation=stability_validation,
        transition_validation=transition_validation,
    )