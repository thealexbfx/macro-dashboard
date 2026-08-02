from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalEvidence:
    source: str
    label: str
    observations: int
    average_return: float | None
    median_return: float | None
    up_rate: float | None
    down_rate: float | None