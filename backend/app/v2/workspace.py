"""Observation-date workspace alignment and optional, sourced historical context."""

from datetime import date
from threading import Lock
from time import monotonic

import pandas as pd
import requests


def prepare_series(
    values, frequency, alignment, start, end, shift=0, source_labels=None
):
    """Retain source labels while sampling, then shift analytical labels, never values.

    The caller transforms at native frequency first. Inputs AND analytical labels
    must lie inside the selected window. Missing calendar periods remain missing.
    Daily shifts are calendar days, not a fabricated trading calendar.
    """
    originals = set(source_labels) if source_labels is not None else set(values.index)
    table = pd.DataFrame(
        {
            "value": values,
            "source_date": [d if d in originals else pd.NaT for d in values.index],
        }
    )
    if alignment == "period_end" and frequency != "daily" and not table.empty:
        alias = (
            "W-SUN" if frequency == "weekly" else "M" if frequency == "monthly" else "Q"
        )
        table = table.groupby(table.index.to_period(alias)).tail(1)
        table.index = table.index.to_period(alias).to_timestamp(how="end").normalize()
        grid = pd.period_range(table.index.min(), table.index.max(), freq=alias)
        table = table.reindex(grid.to_timestamp(how="end").normalize())
    if shift:
        if frequency in ("daily", "weekly"):
            table.index = table.index + pd.Timedelta(
                days=shift * (7 if frequency == "weekly" else 1)
            )
        else:
            alias = (
                "W-SUN"
                if frequency == "weekly"
                else "M"
                if frequency == "monthly"
                else "Q"
            )
            periods = table.index.to_period(alias) + shift
            table.index = periods.to_timestamp(
                how="end" if alignment == "period_end" else "start"
            ).normalize()
    table = table.loc[
        (table.index >= pd.Timestamp(start)) & (table.index <= pd.Timestamp(end))
    ]
    sources = {
        str(k.date()): None if pd.isna(v) else str(v.date())
        for k, v in table.source_date.items()
    }
    return table.value, sources


def source_at(sources, label, frequency):
    if frequency in ("daily", "weekly"):
        return sources.get(str(label.date()))
    alias = "W-SUN" if frequency == "weekly" else "M" if frequency == "monthly" else "Q"
    period = label.to_period(alias)
    return next(
        (v for k, v in sources.items() if pd.Timestamp(k).to_period(alias) == period),
        None,
    )


def recession_periods(rows, start, end):
    """FRED USREC: month AFTER peak through trough month, inclusive.

    Unknown/missing months interrupt a span; they are never assigned a regime.
    """
    seen = set()
    previous = None
    spans = []
    for reference, value in rows:
        day = pd.Timestamp(reference)
        period = day.to_period("M")
        if (
            day.day != 1
            or period in seen
            or (previous is not None and period <= previous)
        ):
            raise ValueError("Invalid USREC monthly reference ordering or duplicates")
        seen.add(period)
        if value is not None and value not in (0, 1):
            raise ValueError("USREC must contain only zero, one or missing")
        if value == 1:
            a, b = period.start_time.date(), period.end_time.date()
            if (
                spans
                and previous == period - 1
                and spans[-1][1] == (period - 1).end_time.date()
            ):
                spans[-1][1] = b
            else:
                spans.append([a, b])
        previous = period
    return [
        {
            "id": f"usrec-{a}",
            "start": str(max(a, start)),
            "end": str(min(b, end)),
            "original_start": str(a),
            "original_end": str(b),
            "label": "US recession (FRED USREC / NBER)",
        }
        for a, b in spans
        if b >= start and a <= end
    ]


class RecessionContext:
    def __init__(self, provider, today_fn, ttl=900):
        self.provider, self.today_fn, self.ttl = provider, today_fn, ttl
        self.cached = None
        self.lock = Lock()

    def get(self, start: date, end: date):
        if start < date(1990, 1, 1) or end < start or end >= self.today_fn():
            raise ValueError(
                "Choose a completed context range from 1990 through yesterday"
            )
        with self.lock:
            stale = False
            error = None
            try:
                if self.cached is None or monotonic() - self.cached[0] >= self.ttl:
                    rows = self.provider.fred_series(
                        "USREC", date(1990, 1, 1), self.today_fn()
                    )
                    if not rows or not any(v is not None for _, v in rows):
                        raise ValueError("USREC observations unavailable")
                    recession_periods(rows, date(1990, 1, 1), end)
                    self.cached = (
                        monotonic(),
                        rows,
                        pd.Timestamp.now(tz="UTC").isoformat(),
                    )
            except (
                ValueError,
                RuntimeError,
                requests.RequestException,
                KeyError,
                TypeError,
                OverflowError,
            ):
                if self.cached is None:
                    raise RuntimeError(
                        "US recession source unavailable; no shading substituted"
                    ) from None
                stale, error = True, "Previous context retained; source refresh failed"
            _, rows, retrieved = self.cached
            latest = max(pd.Timestamp(d).date() for d, v in rows if v is not None)
            # A chronology can be retrospective: this is only distributor coverage.
            stale = stale or (self.today_fn() - latest).days > 75
            return {
                "kind": "us_recession",
                "source_id": "USREC",
                "source": "FRED / Federal Reserve Bank of St. Louis, based on NBER chronology",
                "source_url": "https://fred.stlouisfed.org/series/USREC",
                "status": "stale" if stale else "ok",
                "message": error,
                "latest_reference": str(latest),
                "retrieved_at": retrieved,
                "coverage_start": str(min(pd.Timestamp(d).date() for d, _ in rows)),
                "coverage_end": str(
                    pd.Timestamp(latest).to_period("M").end_time.date()
                ),
                "periods": recession_periods(rows, start, end),
                "methodology": "Monthly NSA binary indicator; month following peak through trough inclusive. Retrospective US context, not causation or real-time recession detection. Missing months are not filled.",
            }
