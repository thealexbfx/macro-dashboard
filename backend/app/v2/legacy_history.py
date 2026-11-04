"""Lossless reconciliation for two documented bounded FRED source histories.

This is a source coverage contract, not permission, a dataset registry or an
exception allowing historical data loss. The unchanged completeness guard runs
over the reconciled candidate. Source omissions/nulls inside its returned range
remain failures. Retained older values are explicitly not reverified/revised.
"""

from datetime import date, timedelta

import pandas as pd

FRED_ROLLING_THREE_YEAR = frozenset({"BAMLH0A0HYM2", "BAMLC0A0CM"})


def reconcile_rolling_prefix(frame, previous, spec, today):
    if (
        spec.provider != "fred"
        or spec.provider_id not in FRED_ROLLING_THREE_YEAR
        or spec.frequency != "daily"
        or frame.empty
        or not previous
    ):
        return frame, {}
    first = frame.date.min().date()
    prefix = [o for o in previous if date.fromisoformat(o.date) < first]
    if not prefix:
        return frame, {}
    # FRED documents a three-year window, not an arbitrary returned prefix. A
    # seven-calendar-day boundary envelope covers weekends/holidays and provider
    # date rollover, not missing interior observations or a shorter feed.
    try:
        anniversary = today.replace(year=today.year - 3)
    except ValueError:  # February 29 -> February 28, same calendar-year convention.
        anniversary = date(today.year - 3, 2, 28)
    if not anniversary - timedelta(days=7) <= first <= anniversary + timedelta(days=7):
        # No reconciliation: the original guard rejects any lost valid prefix.
        return frame, {}
    archived = pd.DataFrame(
        {
            "date": pd.to_datetime([o.date for o in prefix]),
            "value": [o.value for o in prefix],
        }
    )
    combined = (
        pd.concat([archived, frame], ignore_index=True)
        .sort_values("date")
        .reset_index(drop=True)
    )
    return combined, {
        "source_history_contract": "FRED documented rolling three-calendar-year history",
        "source_history_contract_url": f"https://fred.stlouisfed.org/series/{spec.provider_id}",
        "source_available_start": first.isoformat(),
        "source_available_end": frame.date.max().date().isoformat(),
        "retained_before_source_start_count": len(prefix),
        "retained_before_source_start_note": "Previously observed values retained unchanged; outside current provider coverage and not reverified for revisions. Source overlap is revalidated; internal losses still fail.",
    }
