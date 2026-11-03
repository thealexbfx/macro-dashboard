"""Native reference periods and source calendars; never a resampling/calendar grid."""

import calendar as month_calendar
import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from functools import cached_property
from hashlib import sha256
from zoneinfo import ZoneInfo

FREQUENCIES = frozenset(
    {"daily", "weekly", "monthly", "quarterly", "annual", "event", "irregular"}
)


def digest(value):
    return sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()


def instant(value):
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("A source timezone/offset is required")
    # Detect imaginary local times during a daylight-saving jump, not just offsets.
    if value.astimezone(UTC).astimezone(value.tzinfo).replace(fold=value.fold) != value:
        raise ValueError("Nonexistent source-local time")
    return value.astimezone(UTC)


@dataclass(frozen=True)
class SourceCalendar:
    id: str
    timezone: str = "UTC"
    week_ending: int | None = None  # Monday=0; must be explicit for weekly dates.
    weekly_labels: str = "end_date"  # or ISO week, whose end is Sunday
    year_start_month: int = 1
    year_label: str = "start"
    version: str = "1"
    holidays: tuple[str, ...] = ()
    releases: tuple[datetime, ...] = ()  # Only sourced instants, no guessed recurrence.
    evidence: str = ""

    def __post_init__(self):
        ZoneInfo(self.timezone)
        if (
            not self.id
            or len(self.id) > 128
            or len(self.version) > 64
            or isinstance(self.week_ending, bool)
            or self.week_ending not in {None, 0, 1, 2, 3, 4, 5, 6}
        ):
            raise ValueError("Invalid source calendar")
        if (
            self.weekly_labels not in {"end_date", "iso_week"}
            or not 1 <= self.year_start_month <= 12
            or self.year_label not in {"start", "end"}
        ):
            raise ValueError("Invalid period convention")
        if self.weekly_labels == "iso_week" and self.week_ending != 6:
            raise ValueError("ISO weeks must end Sunday")
        if len(self.holidays) > 1000 or len(self.releases) > 1000:
            raise ValueError("Calendar metadata exceeds bound")
        for day in self.holidays:
            date.fromisoformat(day)
        if self.releases and not self.evidence:
            raise ValueError("Release calendar needs source evidence")
        values = [instant(x) for x in self.releases]
        if values != sorted(set(values)):
            raise ValueError("Release instants must be distinct and ordered")

    def next_release(self, after):
        after = instant(after)
        return next((instant(x) for x in self.releases if instant(x) > after), None)


@dataclass(frozen=True)
class Definition:
    id: str
    provider: str
    selector: str
    units: str
    frequency: str
    adjustment: str
    calendar: SourceCalendar
    dimensions: tuple[tuple[str, str], ...] = ()
    unit_multiplier: int = 0

    def __post_init__(self):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,95}", self.id) or not re.fullmatch(
            r"[a-z][a-z0-9_]{0,31}", self.provider
        ):
            raise ValueError("Invalid dataset identity")
        if (
            self.frequency not in FREQUENCIES
            or not self.units
            or not self.adjustment
            or not self.selector
        ):
            raise ValueError("Incomplete native definition")
        if (
            len(self.units) > 256
            or len(self.adjustment) > 200
            or len(self.selector) > 4096
        ):
            raise ValueError("Definition metadata exceeds bound")
        if self.frequency == "weekly" and self.calendar.week_ending is None:
            raise ValueError("Weekly source convention must be explicit")
        if (
            len(self.dimensions) > 20
            or len(dict(self.dimensions)) != len(self.dimensions)
            or not -12 <= self.unit_multiplier <= 12
        ):
            raise ValueError("Invalid source dimensions")

    @cached_property
    def source_identity(self):
        return digest(
            {
                "provider": self.provider,
                "selector": self.selector,
                "dimensions": self.dimensions,
                "frequency": self.frequency,
            }
        )

    @cached_property
    def fingerprint(self):
        # Release-date additions do not redefine observations; calendar convention
        # changes do, and need a new explicitly reviewed definition version.
        value = asdict(self)
        value["calendar"].pop("releases")
        value["calendar"].pop("holidays")
        value["calendar"].pop("evidence")
        return digest(value)


@dataclass(frozen=True)
class Period:
    key: str
    start: date
    end: date
    event_at: str | None = None


def native_period(key, definition, event_id=None):
    freq, cal = definition.frequency, definition.calendar
    if not isinstance(key, str) or len(key) > 100:
        raise ValueError("Invalid source period")
    if freq in {"event", "irregular"}:
        stamp = datetime.fromisoformat(key)
        utc = instant(stamp)
        if event_id is not None and (
            not isinstance(event_id, str) or not 1 <= len(event_id) <= 128
        ):
            raise ValueError("Invalid event identity")
        local_day = utc.astimezone(ZoneInfo(cal.timezone)).date()
        canonical = utc.isoformat() + ("#" + event_id if event_id else "")
        return Period(canonical, local_day, local_day, utc.isoformat())
    if event_id is not None:
        raise ValueError("Event identity on regular observation")
    if freq in {"daily", "weekly"}:
        if freq == "weekly" and cal.weekly_labels == "iso_week":
            if not re.fullmatch(r"[0-9]{4}-W[0-9]{2}", key):
                raise ValueError("Expected native ISO week")
            year, week = int(key[:4]), int(key[-2:])
            end = date.fromisocalendar(year, week, 7)
        else:
            end = date.fromisoformat(key)
            if end.isoformat() != key:
                raise ValueError("Expected canonical source date")
        if freq == "weekly" and end.weekday() != cal.week_ending:
            raise ValueError("Source week-ending mismatch")
        return Period(key, end - timedelta(days=6) if freq == "weekly" else end, end)
    if freq == "monthly":
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", key):
            raise ValueError("Expected native month")
        year, month = map(int, key.split("-"))
        start = date(year, month, 1)
        return Period(
            key, start, date(year, month, month_calendar.monthrange(year, month)[1])
        )
    if not re.fullmatch(r"[0-9]{4}" + (r"-Q[1-4]" if freq == "quarterly" else ""), key):
        raise ValueError("Expected native year or quarter")
    label_year = int(key[:4])
    year = label_year - (cal.year_label == "end" and cal.year_start_month != 1)
    offset = (int(key[-1]) - 1) * 3 if freq == "quarterly" else 0
    absolute = year * 12 + cal.year_start_month - 1 + offset
    start = date(absolute // 12, absolute % 12 + 1, 1)
    following = absolute + (3 if freq == "quarterly" else 12)
    end = date(following // 12, following % 12 + 1, 1) - timedelta(days=1)
    return Period(key, start, end)


@dataclass(frozen=True)
class Observation:
    period: str
    label: str
    value: float | None
    flags: tuple[str, ...] = ()
    release_at: datetime | None = None
    source_revision: str | None = None
    event_id: str | None = None

    def validated(self, definition, checked_at):
        period = native_period(self.period, definition, self.event_id)
        checked = instant(checked_at)
        if not isinstance(self.label, str) or not 1 <= len(self.label) <= 200:
            raise ValueError("Missing native label")
        if self.value is not None and (
            isinstance(self.value, bool)
            or not isinstance(self.value, (int, float))
            or not math.isfinite(self.value)
        ):
            raise ValueError("Invalid native value")
        if (
            not isinstance(self.flags, tuple)
            or len(self.flags) > 32
            or any(not isinstance(x, str) or len(x) > 200 for x in self.flags)
        ):
            raise ValueError("Source flags exceed bound")
        if self.source_revision is not None and (
            not isinstance(self.source_revision, str) or len(self.source_revision) > 200
        ):
            raise ValueError("Invalid revision label")
        if (
            period.start
            > checked.astimezone(ZoneInfo(definition.calendar.timezone)).date()
            or period.event_at
            and datetime.fromisoformat(period.event_at) > checked
        ):
            raise ValueError("Future reference observation")
        if (
            period.end
            > checked.astimezone(ZoneInfo(definition.calendar.timezone)).date()
            and "partial_period" not in self.flags
        ):
            raise ValueError(
                "Incomplete reference period needs an explicit source flag"
            )
        if self.release_at is not None and instant(self.release_at) > checked:
            raise ValueError("Future publication timestamp")
        return period
