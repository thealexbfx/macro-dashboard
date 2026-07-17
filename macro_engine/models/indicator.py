"""Core data contracts used by the MacroLens Indicator Engine."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal


EconomicDirection = Literal["positive", "negative"]

Frequency = Literal[
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "annual",
]


@dataclass(frozen=True)
class IndicatorConfig:
    """
    Defines how a macroeconomic indicator should be interpreted.

    This object contains metadata and calculation settings only.
    It does not contain observations or calculated results.
    """

    indicator_id: str
    name: str
    economy: str
    pillar: str
    bucket: str
    frequency: Frequency
    economic_direction: EconomicDirection

    state_window: int = 3
    trend_window: int = 3
    minimum_history: int = 36
    historical_lookback: int | None = 240


    description: str = ""
    source: str = ""
    unit: str = ""

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        required_text_fields = {
            "indicator_id": self.indicator_id,
            "name": self.name,
            "economy": self.economy,
            "pillar": self.pillar,
            "bucket": self.bucket,
        }

        for field_name, value in required_text_fields.items():
            if not value or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")

        if self.state_window < 1:
            raise ValueError("state_window must be at least 1.")

        if self.trend_window < 1:
            raise ValueError("trend_window must be at least 1.")

        minimum_required = self.state_window + self.trend_window

        if self.minimum_history < minimum_required:
            raise ValueError(
                "minimum_history must be at least "
                "state_window + trend_window."
            )


@dataclass(frozen=True)
class IndicatorResult:
    """
    Structured output produced by the MacroLens Indicator Engine.
    """

    indicator_id: str
    name: str
    economy: str
    pillar: str
    bucket: str

    latest_date: date | None
    latest_value: float | None

    state_value: float | None
    state_score: float | None
    state_label: str

    trend_value: float | None
    trend_score: float | None
    trend_label: str

    historical_percentile: float | None
    confidence_score: float
    confidence_label: str

    observations_used: int
    flags: tuple[str, ...] = ()

    diagnostics: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """Return True when the engine produced a usable signal."""
        return (
            self.latest_date is not None
            and self.state_score is not None
            and self.trend_score is not None
            and self.confidence_score > 0
        )