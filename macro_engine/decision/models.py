from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class DecisionEvidence:
    code: str
    category: str
    message: str
    direction: str
    strength: float
    source: str

    def __post_init__(self) -> None:
        valid_directions = {
            "bullish",
            "bearish",
            "neutral",
            "limitation",
        }

        if self.direction not in valid_directions:
            raise ValueError(
                f"direction must be one of {sorted(valid_directions)}"
            )

        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(
                "strength must be between 0 and 1"
            )


@dataclass(frozen=True)
class ResearchIdea:
    as_of_date: date
    asset: str
    model_direction: str
    horizon_months: int
    directional_score: float
    model_confidence: float
    model_conviction: float
    historical_support: str
    thesis: str
    supporting_evidence: tuple[DecisionEvidence, ...] = field(
        default_factory=tuple
    )
    contradicting_evidence: tuple[DecisionEvidence, ...] = field(
        default_factory=tuple
    )
    limitations: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.model_direction not in {
            "Bullish",
            "Bearish",
            "Neutral",
        }:
            raise ValueError(
                "model_direction must be Bullish, Bearish or Neutral"
            )

        if self.horizon_months <= 0:
            raise ValueError(
                "horizon_months must be positive"
            )

        if not -1.0 <= self.directional_score <= 1.0:
            raise ValueError(
                "directional_score must be between -1 and 1"
            )

        if not 0.0 <= self.model_confidence <= 1.0:
            raise ValueError(
                "model_confidence must be between 0 and 1"
            )

        if not 0.0 <= self.model_conviction <= 1.0:
            raise ValueError(
                "model_conviction must be between 0 and 1"
            )

    def to_text(self) -> str:
        lines = [
            f"Asset: {self.asset}",
            f"As of: {self.as_of_date}",
            f"Direction: {self.model_direction}",
            f"Horizon: {self.horizon_months} months",
            f"Directional score: {self.directional_score:+.2f}",
            f"Model confidence: {self.model_confidence:.0%}",
            f"Model conviction: {self.model_conviction:.0%}",
            f"Historical support: {self.historical_support}",
            "",
            "Thesis",
            self.thesis,
            "",
            "Supporting evidence",
        ]

        if self.supporting_evidence:
            lines.extend(
                f"- {item.message}"
                for item in self.supporting_evidence
            )
        else:
            lines.append("- None")

        lines.extend(["", "Contradicting evidence"])

        if self.contradicting_evidence:
            lines.extend(
                f"- {item.message}"
                for item in self.contradicting_evidence
            )
        else:
            lines.append("- None")

        lines.extend(["", "Limitations"])

        if self.limitations:
            lines.extend(
                f"- {item}"
                for item in self.limitations
            )
        else:
            lines.append("- None")

        return "\n".join(lines)