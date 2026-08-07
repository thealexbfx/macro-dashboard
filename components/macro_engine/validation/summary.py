from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from components.macro_engine.formatting import (
    format_percentage,
)

from components.help_text import (
    help_text,
    tooltip_html,
)


def _metric_card(
    label: str,
    value: str,
    detail: str,
) -> None:
    html = (
        '<div class="ml-history-metric ml-validation-metric">'
        f'<div class="ml-history-metric-label">{label}</div>'
        f'<div class="ml-history-metric-value">{escape(value)}</div>'
        f'<div class="ml-history-metric-detail">{escape(detail)}</div>'
        "</div>"
    )

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def render_validation_summary(
    *,
    environment_validation: Any,
) -> None:
    """
    Render the executive summary produced by the Environment
    Validation Engine.

    This component performs no validation calculations.
    """

    st.markdown(
        (
            '<div class="ml-history-chart-heading">'
            '<div class="ml-history-panel-title">'
            "Executive Summary"
            "</div>"
            '<div class="ml-history-panel-description">'
            "Historical coverage, classification breadth and model "
            "strength across the analysed environment history."
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    first_row = st.columns(4)

    with first_row[0]:
        _metric_card(
            label="History coverage",
            value=(
                f"{environment_validation.observation_count} "
                "observations"
            ),
            detail=(
                f"{environment_validation.start_date:%b %Y} to "
                f"{environment_validation.end_date:%b %Y}"
            ),
        )

    with first_row[1]:
        _metric_card(
            label="Unique regimes",
            value=str(
                environment_validation.unique_regime_count
            ),
            detail="Distinct environments observed",
        )

    with first_row[2]:
        _metric_card(
            label=tooltip_html(
                "Regime periods",
                help_text("regime_periods"),
            ),
            value=str(
                environment_validation.regime_period_count
            ),
            detail="Continuous classification periods",
        )

    with first_row[3]:
        _metric_card(
            label="Average confidence",
            value=format_percentage(
                environment_validation.average_confidence_score
            ),
            detail="Average model confidence",
        )

    second_row = st.columns(4)

    with second_row[0]:
        _metric_card(
            label="Average conviction",
            value=format_percentage(
                environment_validation.average_conviction_score
            ),
            detail="Average classification strength",
        )

    with second_row[1]:
        _metric_card(
            label=tooltip_html(
                "Transitional coverage",
                help_text("transitional_coverage"),
            ),
            value=format_percentage(
                environment_validation.transitional_coverage_ratio
            ),
            detail=(
                f"{environment_validation.transitional_observation_count} "
                "transitional observations"
            ),
        )

    with second_row[2]:
        _metric_card(
            label="Current regime",
            value=environment_validation.current_regime,
            detail="Latest environment classification",
        )

    with second_row[3]:
        _metric_card(
            label=tooltip_html(
                "Most persistent regime",
                help_text("most_persistent_regime"),
            ),
            value=(
                environment_validation.most_persistent_regime
            ),
            detail=(
                "Longest average historical duration"
            ),
        )

    st.markdown(
        (
            '<div class="ml-history-panel">'
            '<div class="ml-history-panel-header">'
            '<div>'
            '<div class="ml-history-panel-title">'
            "Historical Classification Profile"
            "</div>"
            '<div class="ml-history-panel-description">'
            "The most frequently observed environment and the regime "
            "that has historically persisted for the longest."
            "</div>"
            "</div>"
            "</div>"
            '<div class="ml-current-regime-grid ml-validation-profile-grid">'
            '<div class="ml-current-regime-item">'
            '<div class="ml-current-regime-item-label">'
            "Most common regime"
            "</div>"
            '<div class="ml-current-regime-item-value">'
            f'{escape(environment_validation.most_common_regime)}'
            "</div>"
            "</div>"
            '<div class="ml-current-regime-item">'
            '<div class="ml-current-regime-item-label">'
            f'{tooltip_html(
                "Most persistent regime",
                help_text("most_persistent_regime"),
            )}'
            "</div>"
            '<div class="ml-current-regime-item-value">'
            f'{escape(environment_validation.most_persistent_regime)}'
            "</div>"
            "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )