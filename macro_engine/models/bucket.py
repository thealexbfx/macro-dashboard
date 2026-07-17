"""Core data contracts used by the MacroLens Bucket Engine."""

from dataclasses import dataclass, field
from typing import Any

from macro_engine.models.indicator import IndicatorResult


@dataclass(frozen=True)
class BucketConfig:
    """Defines how a macroeconomic bucket should be constructed."""

    bucket_id: str
    name: str
    economy: str
    pillar: str

    minimum_indicators: int = 2
    indicator_weights: dict[str, float] = field(default_factory=dict)

    description: str = ""

    def __post_init__(self) -> None:
        required_fields = {
            "bucket_id": self.bucket_id,
            "name": self.name,
            "economy": self.economy,
            "pillar": self.pillar,
        }

        for field_name, value in required_fields.items():
            if not value or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")

        if self.minimum_indicators < 1:
            raise ValueError("minimum_indicators must be at least 1.")

        if any(weight < 0 for weight in self.indicator_weights.values()):
            raise ValueError("indicator weights must not be negative.")


@dataclass(frozen=True)
class BucketResult:
    """Structured output produced by the MacroLens Bucket Engine."""

    bucket_id: str
    name: str
    economy: str
    pillar: str

    state_score: float
    state_label: str

    trend_score: float
    trend_label: str

    breadth_score: float
    breadth_label: str

    confidence_score: float
    confidence_label: str

    indicators_used: int
    indicator_results: tuple[IndicatorResult, ...]

    key_drivers: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()

    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Return True when the bucket contains a usable signal."""
        return (
            self.indicators_used > 0
            and self.confidence_score > 0
        )