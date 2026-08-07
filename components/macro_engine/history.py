from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
from typing import Any, Sequence

import plotly.graph_objects as go
import streamlit as st

from components.help_text import (
    help_text,
    tooltip_html,
)

@dataclass(frozen=True)
class RegimeDisplaySummary:
    current_label: str
    current_start_date: date
    current_observations: int
    previous_label: str | None
    regime_changes: int
    average_confidence: float
    average_conviction: float


def _format_percentage(score: float | None) -> str:
    if score is None:
        return "N/A"

    return f"{score * 100:.0f}%"


def _format_month(value: date) -> str:
    return value.strftime("%b %Y")


def _format_full_date(value: date) -> str:
    return value.strftime("%d %b %Y")


def _environment_tone(label: str) -> str:
    normalized = label.lower()

    negative_terms = (
        "contraction",
        "recession",
        "stagflation",
        "tightening",
    )

    warning_terms = (
        "slowdown",
        "inflationary",
        "transition",
        "mixed",
    )

    positive_terms = (
        "expansion",
        "recovery",
        "reflationary",
        "easing",
    )

    if any(term in normalized for term in negative_terms):
        return "negative"

    if any(term in normalized for term in warning_terms):
        return "warning"

    if any(term in normalized for term in positive_terms):
        return "positive"

    return "neutral"


def _build_regime_summary(
    snapshots: Sequence[Any],
) -> RegimeDisplaySummary:
    """
    Build presentation statistics from the ordered History Engine snapshots.

    This does not reclassify any historical observation. It only summarizes
    the labels and scores already produced by the engine.
    """
    latest = snapshots[-1]
    current_label = latest.environment_label
    current_start_index = len(snapshots) - 1

    while (
        current_start_index > 0
        and snapshots[current_start_index - 1].environment_label
        == current_label
    ):
        current_start_index -= 1

    previous_label = None

    if current_start_index > 0:
        previous_label = snapshots[
            current_start_index - 1
        ].environment_label

    regime_changes = sum(
        current.environment_label != previous.environment_label
        for previous, current in zip(
            snapshots,
            snapshots[1:],
        )
    )

    average_confidence = sum(
        snapshot.confidence_score
        for snapshot in snapshots
    ) / len(snapshots)

    average_conviction = sum(
        snapshot.environment_conviction_score
        for snapshot in snapshots
    ) / len(snapshots)

    return RegimeDisplaySummary(
        current_label=current_label,
        current_start_date=snapshots[
            current_start_index
        ].as_of_date,
        current_observations=(
            len(snapshots) - current_start_index
        ),
        previous_label=previous_label,
        regime_changes=regime_changes,
        average_confidence=average_confidence,
        average_conviction=average_conviction,
    )


def _render_summary_card(
    label: str,
    value: str,
    detail: str,
) -> None:
    html = (
        '<div class="ml-history-metric">'
        f'<div class="ml-history-metric-label">{label}</div>'
        f'<div class="ml-history-metric-value">{escape(value)}</div>'
        f'<div class="ml-history-metric-detail">{escape(detail)}</div>'
        "</div>"
    )

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def _render_history_summary(
    snapshots: Sequence[Any],
    history_run: Any,
) -> None:
    summary = _build_regime_summary(snapshots)
    latest = snapshots[-1]
    tone = _environment_tone(summary.current_label)

    previous_regime = (
        summary.previous_label
        if summary.previous_label is not None
        else "No prior regime"
    )

    observation_word = (
        "observation"
        if summary.current_observations == 1
        else "observations"
    )

    current_html = (
        f'<div class="ml-current-regime {tone}">'
        '<div class="ml-current-regime-header">'
        '<div>'
        '<div class="ml-current-regime-eyebrow">'
        f'{tooltip_html("Current regime", help_text("regime"))}'
        '</div>'
        f'<div class="ml-current-regime-name">'
        f'{escape(summary.current_label)}'
        "</div>"
        "</div>"
        f'<div class="ml-current-regime-date">'
        f'As of {_format_full_date(latest.as_of_date)}'
        "</div>"
        "</div>"
        '<div class="ml-current-regime-grid">'
        '<div class="ml-current-regime-item">'
        '<div class="ml-current-regime-item-label">Regime began</div>'
        f'<div class="ml-current-regime-item-value">'
        f'{_format_month(summary.current_start_date)}'
        "</div>"
        "</div>"
        '<div class="ml-current-regime-item">'
        '<div class="ml-current-regime-item-label">'
        f'{tooltip_html(
            "Consecutive observations",
            help_text("consecutive_observations"),
        )}'
        "</div>"
        f'<div class="ml-current-regime-item-value">'
        f'{summary.current_observations} {observation_word}'
        "</div>"
        "</div>"
        '<div class="ml-current-regime-item">'
        '<div class="ml-current-regime-item-label">Previous regime</div>'
        f'<div class="ml-current-regime-item-value">'
        f'{escape(previous_regime)}'
        "</div>"
        "</div>"
        '<div class="ml-current-regime-item">'
        '<div class="ml-current-regime-item-label">'
        "Current conviction"
        "</div>"
        f'<div class="ml-current-regime-item-value">'
        f'{escape(latest.environment_conviction_label)} · '
        f'{_format_percentage(latest.environment_conviction_score)}'
        "</div>"
        "</div>"
        "</div>"
        "</div>"
    )

    st.markdown(
        current_html,
        unsafe_allow_html=True,
    )

    attempted_count = len(history_run.attempted_dates)
    failure_count = len(history_run.failures)
    success_count = len(snapshots)

    success_rate = (
        success_count / attempted_count
        if attempted_count
        else 0.0
    )

    columns = st.columns(4)

    with columns[0]:
        _render_summary_card(
            label="History coverage",
            value=f"{len(snapshots)} observations",
            detail=(
                f"{_format_month(snapshots[0].as_of_date)} to "
                f"{_format_month(snapshots[-1].as_of_date)}"
            ),
        )

    with columns[1]:
        _render_summary_card(
            label=tooltip_html(
                "Regime changes",
                help_text("regime_changes"),
            ),
            value=str(summary.regime_changes),
            detail="Changes in monthly environment label",
        )

    with columns[2]:
        _render_summary_card(
            label="Average confidence",
            value=_format_percentage(
                summary.average_confidence
            ),
            detail="Across the displayed history",
        )

    with columns[3]:
        _render_summary_card(
            label="History completion",
            value=_format_percentage(success_rate),
            detail=(
                f"{success_count} successful · "
                f"{failure_count} failed"
            ),
        )


def _render_recent_timeline(
    snapshots: Sequence[Any],
    months_to_show: int = 8,
) -> None:
    recent_snapshots = list(
        reversed(snapshots[-months_to_show:])
    )

    rows: list[str] = []

    for snapshot in recent_snapshots:
        tone = _environment_tone(
            snapshot.environment_label
        )

        flag_count = len(snapshot.flags)

        flags_text = (
            f"{flag_count} flags"
            if flag_count != 1
            else "1 flag"
        )

        rows.append(
            (
                '<div class="ml-history-row">'
                '<div class="ml-history-date">'
                f'{_format_month(snapshot.as_of_date)}'
                "</div>"
                '<div class="ml-history-regime-cell">'
                f'<span class="ml-history-regime-dot {tone}"></span>'
                '<div>'
                f'<div class="ml-history-regime-label">'
                f'{escape(snapshot.environment_label)}'
                "</div>"
                f'<div class="ml-history-regime-detail">'
                f'{escape(snapshot.activity_label)} activity · '
                f'{escape(snapshot.inflation_impulse_label)} inflation · '
                f'{escape(snapshot.financial_impulse_label)} financial impulse'
                "</div>"
                "</div>"
                "</div>"
                '<div class="ml-history-stat">'
                '<div class="ml-history-stat-label">Confidence</div>'
                f'<div class="ml-history-stat-value">'
                f'{_format_percentage(snapshot.confidence_score)}'
                "</div>"
                "</div>"
                '<div class="ml-history-stat">'
                '<div class="ml-history-stat-label">Conviction</div>'
                f'<div class="ml-history-stat-value">'
                f'{escape(snapshot.environment_conviction_label)}'
                "</div>"
                "</div>"
                '<div class="ml-history-stat">'
                '<div class="ml-history-stat-label">'
                f'{tooltip_html("Flags", help_text("flags"))}'
                '</div>'
                f'<div class="ml-history-stat-value">'
                f'{escape(flags_text)}'
                "</div>"
                "</div>"
                "</div>"
            )
        )

    html = (
        '<div class="ml-history-panel">'
        '<div class="ml-history-panel-header">'
        '<div>'
        '<div class="ml-history-panel-title">Recent Regime Timeline</div>'
        '<div class="ml-history-panel-description">'
        "Most recent monthly environment classifications, shown with "
        "their underlying macro dimensions and model strength."
        "</div>"
        "</div>"
        f'<div class="ml-evidence-count">'
        f'Last {len(recent_snapshots)} observations'
        "</div>"
        "</div>"
        f'{"".join(rows)}'
        "</div>"
    )

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def _build_impulse_chart(
    snapshots: Sequence[Any],
) -> go.Figure:
    dates = [
        snapshot.as_of_date
        for snapshot in snapshots
    ]

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=dates,
            y=[
                snapshot.activity_score
                for snapshot in snapshots
            ],
            mode="lines+markers",
            name="Activity",
            line={
                "width": 2.5,
                "color": "#2563eb",
            },
            marker={
                "size": 5,
                "color": "#2563eb",
            },
            hovertemplate=(
                "Activity: %{y:+.2f}"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Scatter(
            x=dates,
            y=[
                snapshot.inflation_impulse_score
                for snapshot in snapshots
            ],
            mode="lines+markers",
            name="Inflation",
            line={
                "width": 2.5,
                "color": "#f59e0b",
            },
            marker={
                "size": 5,
                "color": "#f59e0b",
            },
            hovertemplate=(
                "Inflation: %{y:+.2f}"
                "<extra></extra>"
            ),
        )
    )

    figure.add_trace(
        go.Scatter(
            x=dates,
            y=[
                snapshot.financial_impulse_score
                for snapshot in snapshots
            ],
            mode="lines+markers",
            name="Financial impulse",
            line={
                "width": 2.5,
                "color": "#7c3aed",
            },
            marker={
                "size": 5,
                "color": "#7c3aed",
            },
            hovertemplate=(
                "Financial: %{y:+.2f}"
                "<extra></extra>"
            ),
        )
    )

    figure.add_hline(
        y=0,
        line_width=1,
        line_dash="dash",
        line_color="#94a3b8",
    )

    figure.update_layout(
        height=390,
        margin={
            "l": 15,
            "r": 15,
            "t": 15,
            "b": 15,
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        hovermode="x unified",
        hoverlabel={
            "namelength": -1,
        },
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        xaxis={
            "title": None,
            "showgrid": False,
            "showline": True,
            "linecolor": "#cbd5e1",
            "tickfont": {
                "color": "#334155",
                "size": 12,
            },
        },
        yaxis={
            "title": {
                "text": "Impulse score",
                "font": {
                    "color": "#334155",
                    "size": 12,
                },
            },
            "range": [-1.0, 1.0],
            "zeroline": False,
            "gridcolor": "#e2e8f0",
            "tickfont": {
                "color": "#334155",
                "size": 12,
            },
        },
        font={
            "family": "Inter, Segoe UI, Arial, sans-serif",
            "color": "#0f172a",
        },
    )

    return figure


def _render_impulse_history(
    snapshots: Sequence[Any],
) -> None:
    st.markdown(
        (
            '<div class="ml-history-chart-heading">'
            '<div class="ml-history-panel-title">'
            "Macro Impulse History"
            "</div>"
            '<div class="ml-history-panel-description">'
            "Evolution of the activity, inflation and financial dimensions "
            "used by the Environment Engine."
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        _build_impulse_chart(snapshots),
        use_container_width=True,
        config={
            "displayModeBar": False,
            "responsive": True,
        },
    )


def render_environment_history(
    history_run: Any,
) -> None:
    st.markdown("## Environment History")

    st.markdown(
        (
            '<div class="ml-section-description">'
            "Historical snapshots show how the model's environment "
            "classification and underlying macro impulses have evolved "
            "through time."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    history = getattr(history_run, "history", None)

    if history is None or not history.snapshots:
        st.warning(
            "No successful environment-history snapshots are available."
        )
        return

    snapshots = history.snapshots

    _render_history_summary(
        snapshots=snapshots,
        history_run=history_run,
    )

    _render_recent_timeline(
        snapshots=snapshots,
    )

    _render_impulse_history(
        snapshots=snapshots,
    )