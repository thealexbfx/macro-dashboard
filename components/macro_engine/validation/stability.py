from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from components.macro_engine.formatting import (
    format_percentage,
)


def _metric_card(
    *,
    label: str,
    value: str,
    detail: str,
) -> None:
    html = (
        '<div class="ml-history-metric ml-validation-metric">'
        f'<div class="ml-history-metric-label">{escape(label)}</div>'
        f'<div class="ml-history-metric-value">{escape(value)}</div>'
        f'<div class="ml-history-metric-detail">{escape(detail)}</div>'
        "</div>"
    )

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def _format_observations(
    value: float | int | None,
) -> str:
    if value is None:
        return "N/A"

    number = float(value)

    if number.is_integer():
        formatted = str(int(number))
    else:
        formatted = f"{number:.1f}"

    word = (
        "observation"
        if number == 1
        else "observations"
    )

    return f"{formatted} {word}"


def _format_rate(
    value: float | None,
) -> str:
    if value is None:
        return "N/A"

    return f"{value:.1f} per year"


def _churn_tone(
    label: str,
) -> str:
    normalized = label.lower()

    if "high" in normalized:
        return "negative"

    if "moderate" in normalized:
        return "warning"

    if "low" in normalized:
        return "positive"

    return "neutral"


def _build_assessment_text(
    stability_validation: Any,
) -> str:
    churn_label = stability_validation.churn_label
    short_lived_ratio = format_percentage(
        stability_validation.short_lived_period_ratio
    )
    oscillation_ratio = format_percentage(
        stability_validation.oscillation_ratio
    )

    return (
        f"The historical sample is classified as {churn_label.lower()}. "
        f"Average regime duration was "
        f"{stability_validation.average_regime_duration_observations:.1f} "
        f"observations, while {short_lived_ratio} of regime periods were "
        f"short-lived. Oscillatory transitions accounted for "
        f"{oscillation_ratio} of eligible transition sequences."
    )


def render_stability_analysis(
    *,
    stability_validation: Any,
) -> None:
    """
    Render historical regime-stability diagnostics.

    All values are supplied directly by the Stability Validation Engine.
    This component performs no stability calculations.
    """

    st.markdown(
        (
            '<div class="ml-history-chart-heading">'
            '<div class="ml-history-panel-title">'
            "Stability Analysis"
            "</div>"
            '<div class="ml-history-panel-description">'
            "Assessment of regime persistence, classification churn and "
            "model strength around historical transitions."
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    first_row = st.columns(4)

    with first_row[0]:
        _metric_card(
            label="Average regime duration",
            value=_format_observations(
                stability_validation
                .average_regime_duration_observations
            ),
            detail="Mean length of historical regime periods",
        )

    with first_row[1]:
        _metric_card(
            label="Median regime duration",
            value=_format_observations(
                stability_validation
                .median_regime_duration_observations
            ),
            detail="Typical historical regime length",
        )

    with first_row[2]:
        _metric_card(
            label="Annualized transition rate",
            value=_format_rate(
                stability_validation
                .annualized_transition_rate
            ),
            detail="Estimated classification changes per year",
        )

    with first_row[3]:
        _metric_card(
            label="Churn assessment",
            value=stability_validation.churn_label,
            detail="Overall regime stability classification",
        )

    second_row = st.columns(4)

    with second_row[0]:
        _metric_card(
            label="Short-lived regimes",
            value=format_percentage(
                stability_validation
                .short_lived_period_ratio
            ),
            detail=(
                f"{stability_validation.short_lived_period_count} "
                "regime periods"
            ),
        )

    with second_row[1]:
        _metric_card(
            label="Oscillation ratio",
            value=format_percentage(
                stability_validation.oscillation_ratio
            ),
            detail=(
                f"{stability_validation.oscillation_count} "
                "oscillatory sequences"
            ),
        )

    with second_row[2]:
        _metric_card(
            label="Confidence before transition",
            value=format_percentage(
                stability_validation
                .average_confidence_before_transition
            ),
            detail="Average immediately before regime changes",
        )

    with second_row[3]:
        _metric_card(
            label="Conviction before transition",
            value=format_percentage(
                stability_validation
                .average_conviction_before_transition
            ),
            detail="Average classification strength before changes",
        )

    tone = _churn_tone(
        stability_validation.churn_label
    )

    assessment_html = (
        f'<div class="ml-current-regime ml-validation-assessment {tone}">'
        '<div class="ml-current-regime-header">'
        '<div>'
        '<div class="ml-current-regime-eyebrow">'
        "Stability assessment"
        "</div>"
        '<div class="ml-current-regime-name">'
        f'{escape(stability_validation.churn_label)}'
        "</div>"
        "</div>"
        '<div class="ml-current-regime-date">'
        f'{stability_validation.completed_transition_count} '
        "completed transitions"
        "</div>"
        "</div>"
        '<div class="ml-history-panel-description">'
        f'{escape(_build_assessment_text(stability_validation))}'
        "</div>"
        '<div class="ml-current-regime-grid">'
        '<div class="ml-current-regime-item">'
        '<div class="ml-current-regime-item-label">'
        "Completed regime periods"
        "</div>"
        '<div class="ml-current-regime-item-value">'
        f'{stability_validation.completed_regime_period_count}'
        "</div>"
        "</div>"
        '<div class="ml-current-regime-item">'
        '<div class="ml-current-regime-item-label">'
        "Short-lived observations"
        "</div>"
        '<div class="ml-current-regime-item-value">'
        f'{stability_validation.short_lived_observation_count} '
        f'· {format_percentage(stability_validation.short_lived_observation_ratio)}'
        "</div>"
        "</div>"
        '<div class="ml-current-regime-item">'
        '<div class="ml-current-regime-item-label">'
        "Confidence drift"
        "</div>"
        '<div class="ml-current-regime-item-value">'
        f'{stability_validation.average_confidence_change_within_period:+.2f}'
        "</div>"
        "</div>"
        '<div class="ml-current-regime-item">'
        '<div class="ml-current-regime-item-label">'
        "Conviction drift"
        "</div>"
        '<div class="ml-current-regime-item-value">'
        f'{stability_validation.average_conviction_change_within_period:+.2f}'
        "</div>"
        "</div>"
        "</div>"
        "</div>"
    )

    st.markdown(
        assessment_html,
        unsafe_allow_html=True,
    )