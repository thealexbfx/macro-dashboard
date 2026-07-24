from __future__ import annotations

from typing import Any


def format_percentage(score: float | None) -> str:
    if score is None:
        return "N/A"

    return f"{score * 100:.0f}%"


def format_score(score: float | None) -> str:
    if score is None:
        return "N/A"

    return f"{score:+.2f}"


def display_date(value: Any) -> str:
    if value is None:
        return "Latest available"

    if hasattr(value, "strftime"):
        return value.strftime("%d %b %Y")

    return str(value)


def clean_pillar_name(name: str, economy: str) -> str:
    prefix = f"{economy} "

    if name.startswith(prefix):
        return name[len(prefix):]

    return name


def pillar_tone(state_score: float) -> str:
    if state_score >= 0.20:
        return "positive"

    if state_score <= -0.20:
        return "negative"

    return "neutral"


def signal_text(signal: Any) -> str:
    for attribute in (
        "summary",
        "message",
        "description",
        "label",
        "name",
        "signal",
    ):
        value = getattr(signal, attribute, None)

        if value:
            return str(value)

    return str(signal)