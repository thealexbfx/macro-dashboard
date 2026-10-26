"""Central data validation and dated source evidence; no claim of independent verification from API success."""

import json
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.v2.expanded import SCHEDULES
from macro_engine.research.analytics import clean

EVIDENCE = json.loads(
    Path(__file__).with_name("audit_evidence.json").read_text(encoding="utf-8")
)


def validate_frame(rows, spec):
    if not rows:
        raise ValueError("No source observations returned")
    raw = pd.DataFrame(rows, columns=["date", "value"])
    dates = pd.to_datetime(raw.date, errors="raise")
    if dates.isna().any() or dates.duplicated().any():
        raise ValueError(
            "Missing or duplicate source timestamps; explicit vintage selection required"
        )
    if not dates.is_monotonic_increasing:
        raise ValueError(
            "Source dates are not strictly ordered; payload rejected, not silently sorted"
        )
    numbers = pd.to_numeric(raw.value, errors="raise")
    if np.isinf(numbers).any():
        raise ValueError("Infinite source values rejected")
    if raw.value.map(lambda v: isinstance(v, bool)).any():
        raise ValueError("Boolean source values are not economic observations")
    if spec.representation in ("index", "level") and (numbers.dropna() <= 0).any():
        raise ValueError(
            "Nonpositive price index or employment level conflicts with definition"
        )
    frame = clean(raw)
    warnings = []
    if spec.frequency in ("monthly", "quarterly"):
        alias = "M" if spec.frequency == "monthly" else "Q"
        periods = frame.date.dt.to_period(alias)
        if periods.duplicated().any():
            raise ValueError(
                "Unexpected source frequency: multiple observations in one reference period"
            )
        if (frame.date.dt.day != 1).any() or (
            spec.frequency == "quarterly"
            and not frame.date.dt.month.isin([1, 4, 7, 10]).all()
        ):
            raise ValueError(
                "Unexpected reference-date convention for registered FRED economic series"
            )
        grid = pd.period_range(periods.min(), periods.max(), freq=alias)
        missing = len(grid.difference(pd.PeriodIndex(periods))) + int(
            frame.value.isna().sum()
        )
        if missing:
            warnings.append(
                f"{missing} absent or missing reference periods; calendar lags retain gaps and never use row-count substitution."
            )
    elif spec.frequency == "weekly":
        periods = frame.date.dt.to_period("W-SUN")
        if periods.duplicated().any():
            raise ValueError("Duplicate native weekly reference periods")
        if spec.id == "initial_claims" and (frame.date.dt.day_of_week != 5).any():
            raise ValueError("Initial claims require Saturday-ending source labels")
        expected = pd.period_range(periods.min(), periods.max(), freq="W-SUN")
        missing = len(expected.difference(pd.PeriodIndex(periods))) + int(
            frame.value.isna().sum()
        )
        if missing:
            warnings.append(f"{missing} missing weekly reference periods; no filling.")
    elif len(frame) > 5 and frame.date.diff().dropna().median() > pd.Timedelta(days=7):
        warnings.append(
            "Daily series has unusually sparse observations; frequency/source coverage requires review."
        )
    if frame.value.isna().any():
        warnings.append(
            f"{int(frame.value.isna().sum())} explicit missing source observations retained. Non-trading days are not inferred to be observations."
        )
    changes = (
        frame.value.diff()
        if spec.representation in ("rate", "growth_rate")
        else frame.value.pct_change(fill_method=None) * 100
    )
    suspicious = changes.abs() > 20
    if suspicious.any():
        warnings.append(
            f"{int(suspicious.sum())} large discontinuities flagged for review; observations retained because legitimate shocks and futures rolls must not be discarded."
        )
    return frame, warnings


def assess_freshness(spec, reference, today):
    evidence = EVIDENCE.get(spec.id, {})
    metadata = {}
    hint = SCHEDULES.get(spec.id)
    if hint and str(reference) == hint[0]:
        due = date.fromisoformat(hint[1])
        return (
            today > due + timedelta(days=2),
            "Prospective FRED schedule hint; no primary publication timestamp inferred.",
            {
                "next_release_date": hint[1],
                "schedule_source": spec.source_url,
                "schedule_checked_at": "2026-10-25",
                "release_date": None,
            },
        )
    if str(reference) == evidence.get("reference"):
        metadata = {
            k: evidence[k]
            for k in (
                "release_date",
                "next_release_date",
                "distributor_updated_at",
                "release_url",
                "audit_checked_at",
            )
            if k in evidence
        }
        next_date = metadata.get("next_release_date")
        if next_date:
            overdue = today > date.fromisoformat(next_date) + timedelta(days=2)
            return (
                overdue,
                (
                    "Release overdue or provider lag; dated expected release "
                    + next_date
                    if overdue
                    else "Within published release schedule; next release " + next_date
                ),
                metadata,
            )
    if spec.frequency == "daily":
        overdue = np.busday_count(reference, today) > 5
        return (
            bool(overdue),
            "Business-day age check, not a verified exchange-holiday/release calendar.",
            metadata,
        )
    if spec.frequency == "weekly":
        return (
            today > reference + timedelta(days=16),
            "Weekly reference-age check; source week labels are not release timestamps.",
            metadata,
        )
    period = pd.Period(reference, freq="M" if spec.frequency == "monthly" else "Q") + 1
    lag = (
        35
        if spec.frequency == "quarterly"
        or spec.id
        in ("pce", "core_pce", "job_openings", "real_consumption", "consumer_sentiment")
        else 7
        if spec.id == "fed_funds"
        else 15
    )
    expected = period.end_time.date() + timedelta(days=lag)
    return (
        today > expected,
        "Frequency-aware estimated next-publication bound "
        + str(expected)
        + "; exact future release date unverified.",
        metadata,
    )


def evaluate_evidence(spec, reference, value, headline):
    e = EVIDENCE.get(spec.id, {})
    result = {
        "status": "Unverified",
        "raw_status": "Unverified",
        "headline_status": "Calculation verified"
        if headline.get("value") is not None
        else "Unavailable",
        "audit_checked_at": e.get("audit_checked_at"),
        "source_url": e.get("raw_source_url", spec.source_url),
        "limitation": e.get(
            "limitation",
            "Current source vintage has not been independently reconciled to a dated publication.",
        ),
    }
    if reference != e.get("reference"):
        return result
    if e.get("expected_raw") is not None:
        if abs(value - e["expected_raw"]) <= e.get("raw_tolerance", 1e-6):
            result["raw_status"] = e["raw_status"]
            result["status"] = e["raw_status"]
        else:
            result["status"] = "Discrepancy"
            result["raw_status"] = "Discrepancy"
    if e.get("expected_headline") is not None and headline.get("value") is not None:
        actual = round(headline["value"], e.get("headline_decimals", 1))
        expected = e["expected_headline"]
        match = abs(actual - expected) <= 1e-8
        result["headline_status"] = (
            "Verified against primary source" if match else "Discrepancy"
        )
        result["headline_reconciliation"] = {
            "reference": reference,
            "release_date": e.get("release_date"),
            "published_value": expected,
            "calculated_value": headline["value"],
            "rounded_to_release_precision": actual,
            "difference_at_release_precision": actual - expected,
            "source_url": e.get("release_url"),
            "vintage_note": "Latest retrieved revised series compared with this dated release, not a claim that all historical vintages match.",
        }
        if not match:
            result["status"] = "Discrepancy"
    return result


def market_change(frame, spec):
    valid = frame.dropna(subset=["value"])
    if len(valid) < 2:
        return (
            None,
            None,
            None,
            {
                "value": None,
                "unit": "bp" if spec.representation == "rate" else "%",
                "label": "Insufficient observations",
            },
        )
    last, previous = valid.iloc[-1], valid.iloc[-2]
    absolute = float(last.value - previous.value)
    units = (
        "percentage points"
        if spec.representation in ("rate", "growth_rate")
        else spec.units
    )
    api_change = absolute
    if spec.representation == "price" and previous.value > 0:
        api_change = 100 * (float(last.value) / float(previous.value) - 1)
        units = "percent"
    if spec.frequency == "daily":
        display = (
            absolute * 100
            if spec.representation == "rate"
            else 100 * (float(last.value) / float(previous.value) - 1)
            if previous.value > 0
            else absolute
        )
        display_unit = (
            "bp"
            if spec.representation == "rate"
            else "%"
            if previous.value > 0
            else spec.units
        )
        label = (
            "Yield change; not a bond return"
            if spec.representation == "rate"
            else "Change vs previous available close"
            if previous.value > 0
            else "Absolute change (nonpositive prior price)"
        )
    else:
        display = None
        display_unit = units
        label = "Use the recommended economic headline transformation"
    return (
        api_change,
        units,
        str(previous.date.date()),
        {
            "value": display,
            "unit": display_unit,
            "label": label,
            "previous_date": str(previous.date.date()),
            "reference_date": str(last.date.date()),
            "calculation_status": "Calculation verified",
        },
    )
