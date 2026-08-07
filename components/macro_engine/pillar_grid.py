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

from components.help_text import (
    help_text,
    tooltip_html,
)

def _pillar_name_html(name: str) -> str:
    help_key = name.strip().casefold()

    return tooltip_html(
        name,
        help_text(help_key),
    )

def _render_pillar_card(
    name: str,
    state_label: str,
    trend_label: str,
    state_score: float,
    confidence_score: float,
) -> None:
    tone = pillar_tone(state_score)

    pillar_name_html = _pillar_name_html(name)

    current_state_html = "Current state"
    trend_html = "Trend"

    state_score_html = tooltip_html(
        "State",
        help_text("state_score"),
    )

    confidence_html = tooltip_html(
        "Confidence",
        help_text("confidence"),
    )

    html = (
        f'<div class="ml-pillar-card {tone}">'
        f'<div class="ml-pillar-name">{pillar_name_html}</div>'

        f'<div class="ml-pillar-label">{current_state_html}</div>'
        f'<div class="ml-pillar-value">{escape(state_label)}</div>'

        f'<div class="ml-pillar-label">{trend_html}</div>'
        f'<div class="ml-pillar-value">{escape(trend_label)}</div>'

        '<div class="ml-pillar-footer">'
        f"{state_score_html} {format_score(state_score)}"
        "<br>"
        f"{confidence_html} "
        f"{format_percentage(confidence_score)}"
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