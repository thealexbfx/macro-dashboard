from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetFactor:
    code: str
    name: str
    score: float
    explanation: str

    def __post_init__(self) -> None:
        if not -1.0 <= self.score <= 1.0:
            raise ValueError(
                "AssetFactor score must be between -1 and 1."
            )

    @property
    def direction(self) -> str:
        if self.score > 0:
            return "bullish"

        if self.score < 0:
            return "bearish"

        return "neutral"

    @property
    def strength(self) -> float:
        return abs(self.score)