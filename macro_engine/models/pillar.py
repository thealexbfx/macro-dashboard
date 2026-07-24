"""Core data contracts used by the MacroLens Pillar Engine."""

from dataclasses import dataclass, field
from typing import Any

from macro_engine.models.bucket import BucketResult


@dataclass(frozen=True)
class PillarConfig:
    """Defines how a macroeconomic pillar should be constructed."""

    pillar_id: str
    pillar: str
    name: str
    economy: str

    minimum_buckets: int = 2
    bucket_weights: dict[str, float] = field(default_factory=dict)

    description: str = ""

    def __post_init__(self) -> None:
        required_fields = {
            "pillar_id": self.pillar_id,
            "pillar": self.pillar,
            "name": self.name,
            "economy": self.economy,
        }

        for field_name, value in required_fields.items():
            if not value or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")

        if self.minimum_buckets < 1:
            raise ValueError("minimum_buckets must be at least 1.")

        if any(weight < 0 for weight in self.bucket_weights.values()):
            raise ValueError("bucket weights must not be negative.")


@dataclass(frozen=True)
class PillarResult:
    """Structured output produced by the MacroLens Pillar Engine."""

    pillar_id: str
    name: str
    economy: str

    state_score: float
    state_label: str

    trend_score: float
    trend_label: str

    breadth_score: float
    breadth_label: str

    confidence_score: float
    confidence_label: str

    buckets_used: int
    bucket_results: tuple[BucketResult, ...]

    key_drivers: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()

    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Return True when the pillar contains a usable signal."""
        return (
            self.buckets_used > 0
            and self.confidence_score > 0
        )