from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from components.macro_engine.formatting import (
    display_date,
    format_percentage,
)


def _render_metric_card(
    label: str,
    value: str,
    detail: str,
) -> None:
    html = (
        '<div class="ml-card">'
        f'<div class="ml-card-label">{escape(label)}</div>'
        f'<div class="ml-card-value">{escape(value)}</div>'
        f'<div class="ml-card-detail">{escape(detail)}</div>'
        "</div>"
    )

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def render_environment_hero(result: Any) -> None:
    hero_html = (
        '<div class="ml-environment-hero">'
        '<div class="ml-environment-badge">'
        "Current macro environment"
        "</div>"
        '<h2 class="ml-environment-name">'
        f"{escape(result.environment_label)}"
        "</h2>"
        '<p class="ml-environment-summary">'
        f"{escape(result.environment_summary)}"
        "</p>"
        "</div>"
    )

    st.markdown(
        hero_html,
        unsafe_allow_html=True,
    )

    columns = st.columns(4)

    with columns[0]:
        _render_metric_card(
            label="Confidence",
            value=format_percentage(result.confidence_score),
            detail=result.confidence_label,
        )

    with columns[1]:
        _render_metric_card(
            label="Conviction",
            value=format_percentage(
                result.environment_conviction_score
            ),
            detail=result.environment_conviction_label,
        )

    with columns[2]:
        _render_metric_card(
            label="Overall direction",
            value=result.overall_direction,
            detail="Composite model direction",
        )

    with columns[3]:
        _render_metric_card(
            label="As of",
            value=display_date(result.as_of_date),
            detail="Engine observation basis",
        )