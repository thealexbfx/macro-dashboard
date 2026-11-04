"""Read-only, offline, bounded diagnostics for six reported legacy exceptions.

Standalone stdlib script: no app imports, providers, credentials, writes or repairs.
Prints allowlisted diagnostic facts, never arbitrary warnings/errors/payloads.
"""

import argparse
import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

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


def diagnostics(database):
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
        rows = []
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
    return {
        "as_of": datetime.now(UTC).isoformat(),
        "production_mutations": 0,
        "source_requests": 0,
        "datasets": rows,
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
    args = parser.parse_args()
    print(json.dumps(diagnostics(args.database), indent=2))
