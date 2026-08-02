from __future__ import annotations

from typing import Any

import streamlit as st

from components.macro_engine.indicator_inventory import (
    render_model_indicator_inventory,
)
from components.macro_engine.evidence import (
    render_model_evidence,
)
from components.macro_engine.hero import (
    render_environment_hero,
)
from components.macro_engine.history import (
    render_environment_history,
)
from components.macro_engine.methodology import (
    render_methodology_explainer,
)
from components.macro_engine.pillar_grid import (
    render_pillar_grid,
)
from components.macro_engine.validation.renderer import (
    render_validation,
)
from styles.macro_engine import inject_macro_engine_css


def render_historical_explorer_link(
    environment: str,
) -> None:
    st.markdown(
        """
        <div style="
            margin-top: 10px;
            margin-bottom: 6px;
            color: #6b7788;
            font-size: 12px;
        ">
            Compare the current model environment with previous historical
            episodes and cross-asset outcomes.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "View Historical Episodes",
        key="open_historical_regime_explorer",
        use_container_width=False,
    ):
        st.query_params["page"] = "HistoricalRegimeExplorer"
        st.query_params["environment"] = environment
        st.rerun()


def render_macro_environment_overview(
    result: Any,
    history_run: Any,
    environment_validation: Any,
    stability_validation: Any,
    transition_validation: Any,
) -> None:
    """
    Render the reusable Macro Environment overview.

    The component consumes completed environment, history and validation
    results. It performs no engine calculations.
    """
    inject_macro_engine_css()

    render_environment_hero(result)

    render_historical_explorer_link(
        result.environment_label,
    )

    st.markdown(
        '<hr class="ml-section-divider">',
        unsafe_allow_html=True,
    )

    render_methodology_explainer()

    st.markdown(
        '<hr class="ml-section-divider">',
        unsafe_allow_html=True,
    )

    render_pillar_grid(result)

    st.markdown(
        '<hr class="ml-section-divider">',
        unsafe_allow_html=True,
    )

    render_model_indicator_inventory(result)

    st.markdown(
        '<hr class="ml-section-divider">',
        unsafe_allow_html=True,
    )

    render_model_evidence(result)

    st.markdown(
        '<hr class="ml-section-divider">',
        unsafe_allow_html=True,
    )

    render_environment_history(history_run)

    st.markdown(
        '<hr class="ml-section-divider">',
        unsafe_allow_html=True,
    )

    render_validation(
        environment_validation=environment_validation,
        stability_validation=stability_validation,
        transition_validation=transition_validation,
    )