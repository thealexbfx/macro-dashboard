from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EnvironmentEpisode:
    """A consecutive historical occurrence of one macro environment."""

    environment: str

    start_month: str
    end_month: str
    duration_months: int

    previous_environment: str | None
    next_environment: str | None

    entry_confidence: float | None
    entry_conviction: float | None
    entry_conviction_label: str | None

    entry_activity_score: float | None
    entry_activity_label: str | None

    entry_inflation_score: float | None
    entry_inflation_label: str | None

    entry_financial_score: float | None
    entry_financial_label: str | None

    entry_asset_close: float | None

    forward_outcomes: dict[int, float | None]

    entry_flags: tuple[str, ...]

    @property
    def is_completed(self) -> bool:
        """Return True when the episode has a known following environment."""
        return self.next_environment is not None

    def get_forward_outcome(self, horizon_months: int) -> float | None:
        """Return the episode-entry outcome for the requested horizon."""
        return self.forward_outcomes.get(horizon_months)

    def to_record(self) -> dict[str, Any]:
        """Convert the episode into a flat dictionary for DataFrames and CSVs."""
        record: dict[str, Any] = {
            "environment": self.environment,
            "start_month": self.start_month,
            "end_month": self.end_month,
            "duration_months": self.duration_months,
            "previous_environment": self.previous_environment,
            "next_environment": self.next_environment,
            "entry_confidence": self.entry_confidence,
            "entry_conviction": self.entry_conviction,
            "entry_conviction_label": self.entry_conviction_label,
            "entry_activity_score": self.entry_activity_score,
            "entry_activity_label": self.entry_activity_label,
            "entry_inflation_score": self.entry_inflation_score,
            "entry_inflation_label": self.entry_inflation_label,
            "entry_financial_score": self.entry_financial_score,
            "entry_financial_label": self.entry_financial_label,
            "entry_asset_close": self.entry_asset_close,
            "entry_flags": "|".join(self.entry_flags),
            "is_completed": self.is_completed,
        }

        for horizon, outcome in sorted(self.forward_outcomes.items()):
            record[f"forward_outcome_{horizon}m"] = outcome

        return record