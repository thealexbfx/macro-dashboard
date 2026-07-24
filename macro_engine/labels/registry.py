"""Context-aware labels for MacroLens engine scores."""


def classify_state(pillar: str, score: float) -> str:
    """Convert a state score into terminology appropriate for its pillar."""

    if pillar == "inflation":
        if score >= 0.60:
            return "Very High Pressure"

        if score >= 0.20:
            return "High Pressure"

        if score > -0.20:
            return "Normal Pressure"

        if score > -0.60:
            return "Low Pressure"

        return "Very Low Pressure"

    if score >= 0.60:
        return "Very Strong"

    if score >= 0.20:
        return "Strong"

    if score > -0.20:
        return "Normal"

    if score > -0.60:
        return "Weak"

    return "Very Weak"


def classify_trend(pillar: str, score: float) -> str:
    """Convert a trend score into terminology appropriate for its pillar."""

    if pillar == "inflation":
        if score >= 0.20:
            return "Accelerating"

        if score <= -0.20:
            return "Cooling"

        return "Stable"

    if score >= 0.20:
        return "Improving"

    if score <= -0.20:
        return "Deteriorating"

    return "Stable"


def classify_breadth(pillar: str, score: float) -> str:
    """Convert a breadth score into terminology appropriate for its pillar."""

    if pillar == "inflation":
        if score >= 0.75:
            return "Broadly Inflationary"

        if score >= 0.25:
            return "Mostly Inflationary"

        if score > -0.25:
            return "Mixed"

        if score > -0.75:
            return "Mostly Disinflationary"

        return "Broadly Disinflationary"

    if score >= 0.75:
        return "Broadly Positive"

    if score >= 0.25:
        return "Mostly Positive"

    if score > -0.25:
        return "Mixed"

    if score > -0.75:
        return "Mostly Negative"

    return "Broadly Negative"