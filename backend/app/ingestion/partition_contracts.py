"""Bounded transport boundary. No live transports are installed or scheduled."""

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from urllib.parse import parse_qsl, urlsplit

from backend.app.ingestion.formats import parse_payload
from backend.app.ingestion.native import Definition, Observation


@dataclass(frozen=True)
class Bounds:
    records: int = 250
    response_bytes: int = 524288
    seconds: int = 20

    def __post_init__(self):
        if (
            any(
                type(x) is not int
                for x in (self.records, self.response_bytes, self.seconds)
            )
            or not 1 <= self.records <= 1000
            or not 1 <= self.response_bytes <= 524288
            or not 1 <= self.seconds <= 30
        ):
            raise ValueError("Unsafe provider bounds")


DEFAULT_BOUNDS = Bounds()


@dataclass(frozen=True)
class Window:
    start: date
    end: date

    def __post_init__(self):
        if (
            type(self.start) is not date
            or type(self.end) is not date
            or self.start > self.end
        ):
            raise ValueError("Reversed source window")


def windows(start, end, *, span_days=366, maximum=32):
    """Partition REQUEST ranges, never generate observation dates or values.

    Ownership is the native reference-period START date. An adapter may need
    wider source queries for week-ending or fiscal labels, then filter exactly.
    """
    from datetime import timedelta

    if start > end or not 1 <= span_days <= 3660 or not 1 <= maximum <= 32:
        raise ValueError("Unsafe partition plan")
    result = []
    while start <= end:
        finish = min(end, start + timedelta(days=span_days - 1))
        result.append(Window(start, finish))
        if len(result) > maximum:
            raise ValueError("Partition plan exceeds bound; submit a smaller range")
        start = finish + timedelta(days=1)
    return tuple(result)


@dataclass(frozen=True)
class Page:
    points: tuple[Observation, ...]
    content_hash: str
    snapshot_hash: str  # Verified source/vintage snapshot, same across all partitions.
    source_url: str  # Credential-free provenance only.
    checked_at: datetime
    next_cursor: str | None = None

    def __post_init__(self):
        if not isinstance(self.points, tuple) or any(
            not isinstance(x, Observation) for x in self.points
        ):
            raise TypeError("Immutable native observation tuple required")
        if any(
            not re.fullmatch(r"[0-9a-f]{64}", x)
            for x in (self.content_hash, self.snapshot_hash)
        ):
            raise ValueError("Source content and snapshot hashes are required")
        url = urlsplit(self.source_url)
        if (
            len(self.source_url) > 2048
            or url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or any(
                k.lower() in {"api_key", "apikey", "token", "access_token", "password"}
                for k, _v in parse_qsl(url.query)
            )
        ):
            raise ValueError("Unsafe source provenance")
        if self.next_cursor is not None and (
            not isinstance(self.next_cursor, str)
            or not 1 <= len(self.next_cursor) <= 1024
            or "://" in self.next_cursor
        ):
            raise ValueError("Invalid unauthenticated checkpoint")


class Adapter(Protocol):
    def fetch(
        self, definition: Definition, window: Window, cursor: str | None, bounds: Bounds
    ) -> Page:
        """Enforce transport byte/deadline limits before parsing; no inline retries."""
        ...


def parsed_page(
    definition,
    body,
    *,
    snapshot_hash,
    source_url,
    checked_at,
    bounds=DEFAULT_BOUNDS,
    next_cursor=None,
):
    import json
    from hashlib import sha256

    points = parse_payload(
        definition, body, max_rows=bounds.records, max_bytes=bounds.response_bytes
    )
    if definition.provider in {"fred", "eia"}:
        metadata = json.loads(body)
        metadata = (
            metadata.get("response", {}) if definition.provider == "eia" else metadata
        )
        total = metadata.get("total" if definition.provider == "eia" else "count")
        if total is not None:
            offset = int(metadata.get("offset", 0))
            total = int(total)
            if (
                total < 0
                or offset < 0
                or (offset + len(points) < total) != (next_cursor is not None)
            ):
                raise ValueError("Source pagination is incomplete or inconsistent")
    return Page(
        points,
        sha256(body).hexdigest(),
        snapshot_hash,
        source_url,
        checked_at,
        next_cursor,
    )
