from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from macro_engine.models.pillar import PillarResult

@dataclass(frozen=True)
class MacroEnvironmentHistory:
    economy: str
    snapshots: tuple[MacroEnvironmentSnapshot, ...]

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError("economy must not be empty")

        if not self.snapshots:
            raise ValueError(
                "snapshots must contain at least one observation"
            )

        mismatched_economies = [
            snapshot.economy
            for snapshot in self.snapshots
            if snapshot.economy.strip().upper()
            != self.economy.strip().upper()
        ]

        if mismatched_economies:
            raise ValueError(
                "all snapshots must match the history economy"
            )

        dates = [
            snapshot.as_of_date
            for snapshot in self.snapshots
        ]

        if len(set(dates)) != len(dates):
            raise ValueError(
                "snapshot dates must be unique"
            )

        if dates != sorted(dates):
            raise ValueError(
                "snapshots must be ordered by as_of_date"
            )

    @property
    def latest(self) -> MacroEnvironmentSnapshot:
        return self.snapshots[-1]

    @property
    def earliest(self) -> MacroEnvironmentSnapshot:
        return self.snapshots[0]

    @property
    def observation_count(self) -> int:
        return len(self.snapshots)
        
@dataclass(frozen=True)
class MacroRegimePeriod:
    economy: str
    environment_label: str

    start_date: date
    end_date: date

    observation_count: int

    average_confidence_score: float
    average_conviction_score: float

    starting_snapshot: MacroEnvironmentSnapshot
    ending_snapshot: MacroEnvironmentSnapshot

    is_current: bool = False

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError("economy must not be empty")

        if not self.environment_label.strip():
            raise ValueError(
                "environment_label must not be empty"
            )

        if self.end_date < self.start_date:
            raise ValueError(
                "end_date must not be before start_date"
            )

        if self.observation_count < 1:
            raise ValueError(
                "observation_count must be at least 1"
            )

        for field_name, score in {
            "average_confidence_score": (
                self.average_confidence_score
            ),
            "average_conviction_score": (
                self.average_conviction_score
            ),
        }.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        if (
            self.starting_snapshot.economy.strip().upper()
            != self.economy.strip().upper()
        ):
            raise ValueError(
                "starting_snapshot must match the period economy"
            )

        if (
            self.ending_snapshot.economy.strip().upper()
            != self.economy.strip().upper()
        ):
            raise ValueError(
                "ending_snapshot must match the period economy"
            )

        if (
            self.starting_snapshot.environment_label
            != self.environment_label
        ):
            raise ValueError(
                "starting_snapshot must match the period regime"
            )

        if (
            self.ending_snapshot.environment_label
            != self.environment_label
        ):
            raise ValueError(
                "ending_snapshot must match the period regime"
            )

        if self.starting_snapshot.as_of_date != self.start_date:
            raise ValueError(
                "starting_snapshot date must match start_date"
            )

        if self.ending_snapshot.as_of_date != self.end_date:
            raise ValueError(
                "ending_snapshot date must match end_date"
            )

    @property
    def duration_days(self) -> int:
        return (self.end_date - self.start_date).days

    @property
    def activity_change(self) -> float:
        return round(
            self.ending_snapshot.activity_score
            - self.starting_snapshot.activity_score,
            4,
        )

    @property
    def inflation_change(self) -> float:
        return round(
            self.ending_snapshot.inflation_impulse_score
            - self.starting_snapshot.inflation_impulse_score,
            4,
        )

    @property
    def financial_change(self) -> float:
        return round(
            self.ending_snapshot.financial_impulse_score
            - self.starting_snapshot.financial_impulse_score,
            4,
        )

@dataclass(frozen=True)
class MacroEnvironmentConfig:
    """Configuration for combining pillar results into a macro environment."""

    economy: str
    minimum_pillars: int = 3
    minimum_confidence: float = 0.50

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError("economy must not be empty")

        if self.minimum_pillars < 1:
            raise ValueError("minimum_pillars must be at least 1")

        if not 0.0 <= self.minimum_confidence <= 1.0:
            raise ValueError("minimum_confidence must be between 0 and 1")


@dataclass(frozen=True)
class EnvironmentSignal:
    """A structured interpretation produced by the environment engine."""

    code: str
    message: str
    pillars: tuple[str, ...] = field(default_factory=tuple)
    severity: str = "info"

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("signal code must not be empty")

        if not self.message.strip():
            raise ValueError("signal message must not be empty")

        valid_severities = {"info", "positive", "warning", "critical"}

        if self.severity not in valid_severities:
            raise ValueError(
                f"severity must be one of {sorted(valid_severities)}"
            )

@dataclass(frozen=True)
class MacroEnvironmentSnapshot:
    economy: str
    as_of_date: date

    activity_score: float
    activity_label: str

    inflation_impulse_score: float
    inflation_impulse_label: str

    financial_impulse_score: float
    financial_impulse_label: str

    environment_label: str

    confidence_score: float
    environment_conviction_score: float
    environment_conviction_label: str

    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError("economy must not be empty")

        score_fields = {
            "activity_score": self.activity_score,
            "inflation_impulse_score": (
                self.inflation_impulse_score
            ),
            "financial_impulse_score": (
                self.financial_impulse_score
            ),
        }

        for field_name, score in score_fields.items():
            if not -1.0 <= score <= 1.0:
                raise ValueError(
                    f"{field_name} must be between -1 and 1"
                )

        probability_fields = {
            "confidence_score": self.confidence_score,
            "environment_conviction_score": (
                self.environment_conviction_score
            ),
        }

        for field_name, score in probability_fields.items():
            if not 0.0 <= score <= 1.0:
                raise ValueError(
                    f"{field_name} must be between 0 and 1"
                )

        required_labels = {
            "activity_label": self.activity_label,
            "inflation_impulse_label": (
                self.inflation_impulse_label
            ),
            "financial_impulse_label": (
                self.financial_impulse_label
            ),
            "environment_label": self.environment_label,
            "environment_conviction_label": (
                self.environment_conviction_label
            ),
        }

        for field_name, value in required_labels.items():
            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty"
                )

@dataclass(frozen=True)
class MacroEnvironmentResult:
    """Combined interpretation of an economy's macro pillars."""

    economy: str
    as_of_date: date | None

    pillar_results: tuple[PillarResult, ...]
    pillar_map: dict[str, PillarResult]

    overall_direction: str

    activity_score: float = 0.0
    activity_label: str = "Unknown"

    inflation_impulse_score: float = 0.0
    inflation_impulse_label: str = "Unknown"

    financial_impulse_score: float = 0.0
    financial_impulse_label: str = "Unknown"

    environment_label: str = "Unknown"
    environment_summary: str = "No environment summary available."
    
    environment_conviction_score: float = 0.0
    environment_conviction_label: str = "Unknown"

    dimension_margins: dict[str, float] = field(default_factory=dict)

    confirmations: tuple[EnvironmentSignal, ...] = field(default_factory=tuple)
    tensions: tuple[EnvironmentSignal, ...] = field(default_factory=tuple)
    transition_signals: tuple[EnvironmentSignal, ...] = field(
        default_factory=tuple
    )

    confidence_score: float = 0.0
    confidence_label: str = "Unknown"

    key_drivers: tuple[str, ...] = field(default_factory=tuple)
    flags: tuple[str, ...] = field(default_factory=tuple)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.economy.strip():
            raise ValueError("economy must not be empty")

        if not self.pillar_results:
            raise ValueError("pillar_results must not be empty")

        if len(self.pillar_map) != len(self.pillar_results):
            raise ValueError(
                "pillar_map must contain exactly one entry per pillar result"
            )

        if not self.overall_direction.strip():
            raise ValueError("overall_direction must not be empty")

        if not -1.0 <= self.activity_score <= 1.0:
            raise ValueError("activity_score must be between -1 and 1")

        if not self.activity_label.strip():
            raise ValueError("activity_label must not be empty")

        if not -1.0 <= self.inflation_impulse_score <= 1.0:
            raise ValueError(
                "inflation_impulse_score must be between -1 and 1"
            )

        if not self.inflation_impulse_label.strip():
            raise ValueError(
                "inflation_impulse_label must not be empty"
            )

        if not -1.0 <= self.financial_impulse_score <= 1.0:
            raise ValueError(
                "financial_impulse_score must be between -1 and 1"
            )

        if not self.financial_impulse_label.strip():
            raise ValueError(
                "financial_impulse_label must not be empty"
            )

        if not self.environment_label.strip():
            raise ValueError("environment_label must not be empty")

        if not self.environment_summary.strip():
            raise ValueError("environment_summary must not be empty")
            
        if not 0.0 <= self.environment_conviction_score <= 1.0:
            raise ValueError(
                "environment_conviction_score must be between 0 and 1"
            )

        if not self.environment_conviction_label.strip():
            raise ValueError(
                "environment_conviction_label must not be empty"
            )

        valid_dimensions = {
            "activity",
            "inflation",
            "financial",
        }

        if not set(self.dimension_margins).issubset(valid_dimensions):
            raise ValueError(
                "dimension_margins contains an unknown dimension"
            )

        for margin in self.dimension_margins.values():
            if not 0.0 <= margin <= 1.0:
                raise ValueError(
                    "dimension margins must be between 0 and 1"
                )

        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("confidence_score must be between 0 and 1")

        expected_pillars = {
            result.name for result in self.pillar_results
        }

        if set(self.pillar_map) != expected_pillars:
            raise ValueError(
                "pillar_map keys must match pillar result config names"
            )