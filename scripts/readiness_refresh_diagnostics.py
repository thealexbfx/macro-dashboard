"""Read-only, offline, bounded diagnostics for six reported legacy exceptions.

Standalone stdlib script: no app imports, credentials, writes or repairs.
Offline by default; explicit optional public CSV comparison, at most two GETs.
Prints allowlisted diagnostic facts, never arbitrary warnings/errors/payloads.
"""

import argparse
import csv
import io
import json
import math
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from urllib.request import HTTPRedirectHandler, Request, build_opener

IDS = (
    "high_yield_spread",
    "investment_grade_spread",
    "consumer_sentiment",
    "fed_funds",
    "industrial_production",
    "retail_sales",
)


def safe_time(value):
    try:
        stamp = datetime.fromisoformat(value)
        return stamp.isoformat() if stamp.tzinfo else None
    except (ValueError, TypeError):
        return None


def diagnostics(database, *, compare_public_csv=False, fetch_csv=None):
    path = Path(database).resolve(strict=True)
    started = monotonic()
    with closing(
        sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        allowed = {
            sqlite3.SQLITE_SELECT,
            sqlite3.SQLITE_READ,
            sqlite3.SQLITE_FUNCTION,
            sqlite3.SQLITE_TRANSACTION,
        }
        db.set_authorizer(
            lambda op, *_: sqlite3.SQLITE_OK if op in allowed else sqlite3.SQLITE_DENY
        )
        db.set_progress_handler(lambda: int(monotonic() - started > 10), 1000)
        db.execute("BEGIN")
        rows, coverage_inputs = [], {}
        for key in IDS:
            record = db.execute(
                "SELECT checked_at,next_due,failures,json_valid(payload) valid,length(CAST(payload AS BLOB)) bytes FROM source_cache WHERE id=?",
                (key,),
            ).fetchone()
            if not record or not record["valid"] or record["bytes"] > 16 * 1024 * 1024:
                rows.append(
                    {"id": key, "state": "missing_invalid_or_over_budget_cache"}
                )
                continue
            # Six bounded cached records only. Observations are never exported.
            payload = json.loads(
                db.execute(
                    "SELECT payload FROM source_cache WHERE id=?", (key,)
                ).fetchone()[0]
            )
            if not isinstance(payload, dict):
                rows.append({"id": key, "state": "invalid_cache_shape"})
                continue
            if key in CREDIT_SERIES:
                coverage_inputs[key] = payload
            meta = payload.get("release_metadata") or {}
            if not isinstance(meta, dict):
                rows.append({"id": key, "state": "invalid_refresh_metadata"})
                continue
            warnings = payload.get("quality_warnings") or []
            warnings = warnings if isinstance(warnings, list) else []
            text = " ".join(w for w in warnings if isinstance(w, str))
            rows.append(
                {
                    "id": key,
                    "last_attempt": safe_time(record["checked_at"]),
                    "next_due": safe_time(record["next_due"]),
                    "failures": record["failures"],
                    "cached_status": payload.get("status")
                    if payload.get("status") in {"ok", "stale", "unavailable"}
                    else "unknown",
                    "source_check_succeeded": meta.get("source_check_succeeded")
                    if type(meta.get("source_check_succeeded")) is bool
                    else None,
                    "last_source_success_at": safe_time(
                        meta.get("last_source_success_at")
                    ),
                    "legacy_telemetry_fields_absent": "source_check_succeeded"
                    not in meta
                    and not meta.get("last_source_success_at"),
                    "retrieved_at": safe_time(payload.get("retrieved_at")),
                    "latest_reference": safe_date(
                        payload.get("latest_observation_date")
                    ),
                    "error_present": bool(meta.get("source_error_code")),
                    "history_truncation_guard_recorded": "Provider history omitted previously observed values"
                    in text,
                    "provider_unavailable_recorded": "Provider unavailable" in text,
                    "interpretation": "Snapshot only. Missing success telemetry is not a failed request; success then failures is not proof of a transient outage. No provider request made.",
                }
            )
    # Close the SQLite read transaction before any optional public-source GET.
    if compare_public_csv:
        for row in rows:
            if row["id"] in coverage_inputs:
                try:
                    raw = (fetch_csv or public_csv)(CREDIT_SERIES[row["id"]])
                    row["coverage_comparison"] = compare_coverage(
                        coverage_inputs[row["id"]], raw, CREDIT_SERIES[row["id"]]
                    )
                except (OSError, ValueError, TypeError, KeyError):
                    row["coverage_comparison"] = {
                        "state": "public_response_unavailable_or_invalid"
                    }
    return {
        "as_of": datetime.now(UTC).isoformat(),
        "production_mutations": 0,
        "public_comparison_requested": compare_public_csv,
        "source_request_limit": 2 if compare_public_csv else 0,
        "source_requests": sum(r["id"] in coverage_inputs for r in rows)
        if compare_public_csv
        else 0,
        "datasets": rows,
    }


CREDIT_SERIES = {
    "high_yield_spread": "BAMLH0A0HYM2",
    "investment_grade_spread": "BAMLC0A0CM",
}


def public_csv(series_id):
    """At most two explicit GETs, no redirects/auth, 8s socket/128KiB bounds."""
    if series_id not in CREDIT_SERIES.values():
        raise ValueError("Unsupported diagnostic source")

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    request = Request(
        f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}",
        headers={"User-Agent": "MacroLens-read-only-coverage-diagnostic"},
    )
    with build_opener(NoRedirect).open(request, timeout=8) as response:
        raw = response.read(131073)
    if len(raw) > 131072:
        raise ValueError("Diagnostic response budget exceeded")
    return raw


def compare_coverage(payload, raw, series_id):
    """Counts/dates only; never export observation values or install responses."""
    if len(raw) > 131072 or payload.get("provider_id") != series_id:
        raise ValueError("Unexpected diagnostic series/budget")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if not reader.fieldnames or series_id not in reader.fieldnames:
        raise ValueError("Response identity mismatch")
    source = {}
    for point in reader:
        label = safe_date(point.get("observation_date") or point.get("DATE"))
        if label is None or label in source:
            raise ValueError("Invalid source dates")
        value = point[series_id]
        source[label] = None if value in ("", ".", ". ") else float(value)
        if source[label] is not None and not math.isfinite(source[label]):
            raise ValueError("Nonfinite source")
    if not source or list(source) != sorted(source):
        raise ValueError("Empty/unordered source")
    cached = {
        o["date"]: o["value"] for o in payload["observations"] if o["value"] is not None
    }
    first = min(source)
    missing = [d for d in cached if d not in source or source[d] is None]
    leading = [d for d in missing if d < first]
    others = [d for d in missing if d >= first]
    revisions = sum(
        source[d] is not None and abs(source[d] - value) > 1e-9
        for d, value in cached.items()
        if d in source
    )
    return {
        "state": "compared_read_only",
        "checked_at": datetime.now(UTC).isoformat(),
        "cached_first_valid": min(cached) if cached else None,
        "cached_last_valid": max(cached) if cached else None,
        "source_first_row": first,
        "source_last_row": max(source),
        "source_rows": len(source),
        "missing_cached_valid_values": len(missing),
        "missing_before_source_start": len(leading),
        "missing_within_or_after_source_range": len(others),
        "leading_missing_date_examples": sorted(leading)[:5],
        "other_missing_date_examples": sorted(others)[:5],
        "overlap_revision_count": revisions,
        "interpretation": "Only a left-boundary difference supports a rolling-window explanation. This is a diagnostic, not acceptance of data, a source substitution or a permission grant.",
    }


def safe_date(value):
    try:
        from datetime import date

        return date.fromisoformat(value).isoformat()
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument(
        "--compare-public-csv",
        action="store_true",
        help="Opt in to at most two bounded public FRED GETs; no cached observations are modified",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            diagnostics(args.database, compare_public_csv=args.compare_public_csv),
            indent=2,
        )
    )
