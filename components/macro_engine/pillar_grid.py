from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from components.macro_engine.formatting import (
    clean_pillar_name,
    format_percentage,
    format_score,
    pillar_tone,
)


def _render_pillar_card(
    name: str,
    state_label: str,
    trend_label: str,
    state_score: float,
    confidence_score: float,
) -> None:
    tone = pillar_tone(state_score)

    html = (
        f'<div class="ml-pillar-card {tone}">'
        f'<div class="ml-pillar-name">{escape(name)}</div>'
        '<div class="ml-pillar-label">Current state</div>'
        f'<div class="ml-pillar-value">{escape(state_label)}</div>'
        '<div class="ml-pillar-label">Trend</div>'
        f'<div class="ml-pillar-value">{escape(trend_label)}</div>'
        '<div class="ml-pillar-footer">'
        f"State {format_score(state_score)}"
        "<br>"
        f"Confidence {format_percentage(confidence_score)}"
        "</div>"
        "</div>"
    )

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def render_pillar_grid(result: Any) -> None:
    st.markdown("## Macro Pillars")

    st.markdown(
        (
            '<div class="ml-section-description">'
            "Current state and directional trend across the engine's "
            "five macroeconomic pillars."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    columns = st.columns(len(result.pillar_results))

    for column, pillar in zip(
        columns,
        result.pillar_results,
    ):
        with column:
            _render_pillar_card(
                name=clean_pillar_name(
                    pillar.name,
                    result.economy,
                ),
                state_label=pillar.state_label,
                trend_label=pillar.trend_label,
                state_score=pillar.state_score,
                confidence_score=pillar.confidence_score,
            )