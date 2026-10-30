"""Provider-neutral contracts; values are native observations, never interpolated."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class Series:
    id: str
    provider: str
    selector: str
    name: str
    source_unit: str
    units: str
    frequency: str = "monthly"
    adjustment: str = "Not seasonally adjusted"


@dataclass(frozen=True)
class Point:
    dataset_id: str
    period: str  # Native monthly YYYY-MM, not a fabricated publication date.
    value: float | None
    quality: str = "observed"


@dataclass(frozen=True)
class Batch:
    points: tuple[Point, ...]
    metadata: dict
    source_hash: str
    source_url: str
    checked_at: datetime
    byte_count: int


class ProviderError(Exception):
    """Safe code only; never persist provider URLs, bodies, or credentials in errors."""

    def __init__(self, code, retry_after=0):
        self.code = code
        self.retry_after = min(86400, max(0, retry_after))
        super().__init__(code)


class Adapter(Protocol):
    id: str
    series: tuple[Series, ...]

    def fetch(self) -> Batch: ...
