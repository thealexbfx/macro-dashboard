from __future__ import annotations

import re
from html import escape
from typing import Any

import streamlit as st

from components.macro_engine.formatting import signal_text


DRIVER_PATTERN = re.compile(
    r"^(?P<name>.+?):\s*"
    r"(?P<direction>[a-zA-Z\s]+)"
    r"\s*\(trend=(?P<trend>-?\d+(?:\.\d+)?),\s*"
    r"confidence=(?P<confidence>\d+(?:\.\d+)?)\)$"
)


FLAG_LABELS = {
    "activity_near_boundary": (
        "Activity close to regime boundary",
        "The activity dimension is near the threshold separating "
        "two environment classifications.",
    ),
    "inflation_near_boundary": (
        "Inflation close to regime boundary",
        "The inflation dimension is near the threshold separating "
        "two environment classifications.",
    ),
    "financial_near_boundary": (
        "Financial impulse close to regime boundary",
        "The financial dimension is near the threshold separating "
        "two environment classifications.",
    ),
}


def _clean_driver_name(name: str) -> str:
    """
    Remove the economy prefix from a driver label for presentation.
    """
    prefixes = (
        "USA ",
        "UK ",
        "Euro Area ",
        "Japan ",
    )

    for prefix in prefixes:
        if name.startswith(prefix):
            return name[len(prefix):]

    return name


def _direction_tone(direction: str) -> str:
    normalized = direction.strip().lower()

    positive_terms = (
        "improving",
        "accelerating",
        "strengthening",
        "expanding",
    )

    negative_terms = (
        "deteriorating",
        "weakening",
        "cooling",
        "contracting",
    )

    if any(term in normalized for term in positive_terms):
        return "positive"

    if any(term in normalized for term in negative_terms):
        return "negative"

    return "neutral"


def _direction_symbol(direction: str) -> str:
    tone = _direction_tone(direction)

    if tone == "positive":
        return "↑"

    if tone == "negative":
        return "↓"

    return "—"


def _parse_driver(driver: str) -> dict[str, str]:
    """
    Parse the existing key-driver text into display fields.

    If the engine output format changes, the unparsed text is retained
    so the evidence section still renders safely.
    """
    match = DRIVER_PATTERN.match(driver.strip())

    if not match:
        return {
            "name": driver,
            "direction": "Reported driver",
            "trend": "N/A",
            "confidence": "N/A",
            "tone": "neutral",
        }

    values = match.groupdict()
    direction = values["direction"].strip().title()

    try:
        confidence = f"{float(values['confidence']) * 100:.0f}%"
    except ValueError:
        confidence = values["confidence"]

    try:
        trend = f"{float(values['trend']):+.2f}"
    except ValueError:
        trend = values["trend"]

    return {
        "name": _clean_driver_name(values["name"].strip()),
        "direction": direction,
        "trend": trend,
        "confidence": confidence,
        "tone": _direction_tone(direction),
    }


def _render_driver_table(drivers: list[str]) -> None:
    if not drivers:
        st.markdown(
            (
                '<div class="ml-evidence-empty">'
                "No primary drivers were reported by the engine."
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return

    rows: list[str] = []

    for driver in drivers:
        parsed = _parse_driver(driver)

        rows.append(
            (
                '<div class="ml-driver-row">'
                '<div class="ml-driver-main">'
                f'<div class="ml-driver-name">'
                f'{escape(parsed["name"])}'
                "</div>"
                f'<div class="ml-driver-direction '
                f'{escape(parsed["tone"])}">'
                f'{_direction_symbol(parsed["direction"])} '
                f'{escape(parsed["direction"])}'
                "</div>"
                "</div>"
                '<div class="ml-driver-stat">'
                '<div class="ml-driver-stat-label">Trend score</div>'
                f'<div class="ml-driver-stat-value">'
                f'{escape(parsed["trend"])}'
                "</div>"
                "</div>"
                '<div class="ml-driver-stat">'
                '<div class="ml-driver-stat-label">Confidence</div>'
                f'<div class="ml-driver-stat-value">'
                f'{escape(parsed["confidence"])}'
                "</div>"
                "</div>"
                "</div>"
            )
        )

    html = (
        '<div class="ml-evidence-panel">'
        '<div class="ml-evidence-panel-header">'
        '<div>'
        '<div class="ml-evidence-panel-title">Primary Drivers</div>'
        '<div class="ml-evidence-panel-description">'
        "Pillars making the largest directional contribution to the "
        "current environment assessment."
        "</div>"
        "</div>"
        f'<div class="ml-evidence-count">{len(drivers)} drivers</div>'
        "</div>"
        '<div class="ml-driver-table">'
        f'{"".join(rows)}'
        "</div>"
        "</div>"
    )

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def _render_signal_panel(
    title: str,
    explanation: str,
    signals: list[str],
    tone: str,
    empty_message: str,
) -> None:
    if signals:
        items = "".join(
            (
                '<div class="ml-signal-item">'
                '<span class="ml-signal-marker"></span>'
                f'<span>{escape(item)}</span>'
                "</div>"
            )
            for item in signals
        )

        status = f"{len(signals)} active"
        body = items
    else:
        status = "None active"
        body = (
            '<div class="ml-signal-empty">'
            f"{escape(empty_message)}"
            "</div>"
        )

    html = (
        f'<div class="ml-signal-panel {escape(tone)}">'
        '<div class="ml-signal-panel-top">'
        f'<div class="ml-signal-panel-title">{escape(title)}</div>'
        f'<div class="ml-signal-status">{escape(status)}</div>'
        "</div>"
        f'<div class="ml-signal-explanation">{escape(explanation)}</div>'
        f'<div class="ml-signal-body">{body}</div>'
        "</div>"
    )

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def _format_flag(flag: str) -> tuple[str, str]:
    if flag in FLAG_LABELS:
        return FLAG_LABELS[flag]

    readable_name = flag.replace("_", " ").strip().title()

    return (
        readable_name,
        "The environment engine identified this condition as relevant "
        "to the current classification.",
    )


def _render_boundary_watch(flags: list[str]) -> None:
    if not flags:
        return

    rows: list[str] = []

    for flag in flags:
        title, description = _format_flag(flag)

        rows.append(
            (
                '<div class="ml-boundary-row">'
                '<div class="ml-boundary-icon">!</div>'
                '<div class="ml-boundary-content">'
                f'<div class="ml-boundary-title">{escape(title)}</div>'
                f'<div class="ml-boundary-description">'
                f'{escape(description)}'
                "</div>"
                "</div>"
                "</div>"
            )
        )

    html = (
        '<div class="ml-boundary-panel">'
        '<div class="ml-evidence-panel-header">'
        '<div>'
        '<div class="ml-evidence-panel-title">Boundary Watch</div>'
        '<div class="ml-evidence-panel-description">'
        "Dimensions currently close to an environment-classification "
        "threshold. These conditions help explain the model's conviction."
        "</div>"
        "</div>"
        f'<div class="ml-evidence-count">{len(flags)} active</div>'
        "</div>"
        f'{"".join(rows)}'
        "</div>"
    )

    st.markdown(
        html,
        unsafe_allow_html=True,
    )


def render_model_evidence(result: Any) -> None:
    st.markdown("## Model Evidence")

    st.markdown(
        (
            '<div class="ml-section-description">'
            "The evidence layer explains which model components support "
            "the current environment, where signals disagree, and whether "
            "the classification may be approaching a transition."
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    _render_driver_table(
        list(result.key_drivers),
    )

    st.markdown(
        '<div class="ml-evidence-subheading">Signal Assessment</div>',
        unsafe_allow_html=True,
    )

    confirmations = [
        signal_text(signal)
        for signal in result.confirmations
    ]

    tensions = [
        signal_text(signal)
        for signal in result.tensions
    ]

    transitions = [
        signal_text(signal)
        for signal in result.transition_signals
    ]

    columns = st.columns(3)

    with columns[0]:
        _render_signal_panel(
            title="Confirmations",
            explanation=(
                "Signals that reinforce and independently support "
                "the current environment classification."
            ),
            signals=confirmations,
            tone="positive",
            empty_message=(
                "No additional confirmation signals are active."
            ),
        )

    with columns[1]:
        _render_signal_panel(
            title="Tensions",
            explanation=(
                "Areas where pillar signals disagree or create internal "
                "conflict within the environment assessment."
            ),
            signals=tensions,
            tone="negative",
            empty_message=(
                "No material internal tensions are currently active."
            ),
        )

    with columns[2]:
        _render_signal_panel(
            title="Transition Risk",
            explanation=(
                "Signals suggesting that the current environment may be "
                "early, fragile, or moving toward another classification."
            ),
            signals=transitions,
            tone="warning",
            empty_message=(
                "No active transition signals were identified."
            ),
        )

    _render_boundary_watch(
        list(result.flags),
    )