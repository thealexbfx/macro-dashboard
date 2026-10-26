"""Explicit horizon/basis extension. Existing native one-period calculations stay unchanged."""

from __future__ import annotations

from typing import ClassVar

import numpy as np
import pandas as pd
from pandas.tseries.holiday import (
    AbstractHolidayCalendar,
    GoodFriday,
    Holiday,
    USFederalHolidayCalendar,
    USLaborDay,
    USMartinLutherKingJr,
    USMemorialDay,
    USPresidentsDay,
    USThanksgivingDay,
    nearest_workday,
    sunday_to_monday,
)


class EquityClosures(AbstractHolidayCalendar):
    rules: ClassVar[list] = [
        Holiday("New year", month=1, day=1, observance=sunday_to_monday),
        USMartinLutherKingJr,
        USPresidentsDay,
        GoodFriday,
        USMemorialDay,
        Holiday(
            "Juneteenth",
            month=6,
            day=19,
            start_date="2022-01-01",
            observance=nearest_workday,
        ),
        Holiday("Independence Day", month=7, day=4, observance=nearest_workday),
        USLaborDay,
        USThanksgivingDay,
        Holiday("Christmas", month=12, day=25, observance=nearest_workday),
    ]


def session_frame(frame, spec):
    table = frame.copy().set_index("date").sort_index()
    if table.empty:
        return frame.copy(), {"expected_closures": 0, "unexpected_missing": 0}
    start, end = table.index.min(), table.index.max()
    calendar = (
        USFederalHolidayCalendar() if spec.provider == "fred" else EquityClosures()
    )
    holidays = set(calendar.holidays(start, end))
    # Documented exceptional full NYSE closures. Valid provider values always win.
    if spec.provider != "fred":
        holidays.update(
            pd.to_datetime(
                [
                    "2001-09-11",
                    "2001-09-12",
                    "2001-09-13",
                    "2001-09-14",
                    "2004-06-11",
                    "2007-01-02",
                    "2012-10-29",
                    "2012-10-30",
                    "2018-12-05",
                    "2025-01-09",
                ]
            )
        )
    expected = pd.DatetimeIndex(
        [d for d in pd.bdate_range(start, end) if d not in holidays]
    )
    observed = table.index[table.value.notna()]
    grid = pd.DatetimeIndex(sorted(set(expected) | set(observed)))
    result = table.reindex(grid)
    result.index.name = "date"
    closures = sum(d not in grid for d in table.index)
    return result.reset_index(), {
        "expected_closures": int(closures),
        "unexpected_missing": int(result.value.isna().sum()),
        "calendar": "Declared US market/federal scheduled closures; valid source observations retained even on a nominal closure. Unlisted closures remain unknown gaps.",
        "session_dates": list(grid.strftime("%Y-%m-%d")),
    }


def weekly_values(frame):
    s = frame.set_index("date").value
    periods = s.index.to_period("W-SUN")
    if periods.duplicated().any():
        raise ValueError("Duplicate weekly source periods")
    sources = dict(zip(periods, s.index))
    s.index = periods
    s = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq="W-SUN"))
    return s, sources


def movement(frame, spec, mode, start, transform_fn, horizon=1, basis="native"):
    if not isinstance(horizon, int) or not 1 <= horizon <= 252:
        raise ValueError("Movement horizon must be 1–252 native observations")
    if mode not in spec.allowed_transformations:
        raise ValueError(f"{mode} is incompatible with {spec.name}")
    quality = {
        "expected_closures": 0,
        "unexpected_missing": int(frame.value.isna().sum()),
    }
    if spec.frequency == "daily" and basis == "trading_sessions":
        frame, quality = session_frame(frame, spec)
    if horizon == 1:
        values, units = transform_fn(frame, spec, mode, start)
        return values, units, quality, frame
    if mode not in {"percent", "mom", "pp", "jobs"}:
        raise ValueError(
            "Multi-period horizons require a change display; annual inflation uses its own native year-over-year convention"
        )
    s = frame.set_index("date").value
    sources = {}
    if spec.frequency == "weekly":
        s, sources = weekly_values(frame)
    elif spec.frequency in {"monthly", "quarterly"}:
        alias = "M" if spec.frequency == "monthly" else "Q"
        s.index = s.index.to_period(alias)
        if s.index.duplicated().any():
            raise ValueError("Duplicate reference periods")
        s = s.reindex(pd.period_range(s.index.min(), s.index.max(), freq=alias))
    if mode in {"percent", "mom"}:
        if (s.dropna() <= 0).any():
            raise ValueError("Percentage movements require positive source values")
        values = (s / s.shift(horizon) - 1) * 100
        unit = "Percent"
    elif mode == "pp":
        values = s.diff(horizon)
        unit = "Percentage points"
    else:
        values = s.diff(horizon) * 1000
        unit = "Net jobs"
    if isinstance(values.index, pd.PeriodIndex):
        values.index = (
            pd.DatetimeIndex(
                [sources.get(p, p.end_time.normalize()) for p in values.index]
            )
            if spec.frequency == "weekly"
            else values.index.to_timestamp()
        )
    values = values.loc[values.index >= pd.Timestamp(start)].replace(
        [np.inf, -np.inf], np.nan
    )
    period = (
        "trading sessions"
        if spec.frequency == "daily" and basis == "trading_sessions"
        else "source observations"
        if spec.frequency == "daily"
        else {"weekly": "weeks", "monthly": "months", "quarterly": "quarters"}[
            spec.frequency
        ]
    )
    return values, f"{unit} over {horizon} {period}", quality, frame
