"""Offline, read-only research readiness audit. Never starts the application/workers."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sqlite3
import subprocess
from collections import Counter
from contextlib import closing
from datetime import UTC, date, datetime
from pathlib import Path
from time import monotonic

import pandas as pd

from backend.app.catalog import operations
from backend.app.catalog.operations import LAGS, registry, resources
from backend.app.ingestion.native import native_period
from backend.app.v2.definitions import SPECS
from backend.app.v2.integrity import assess_freshness, validate_frame
from backend.app.v2.movements import session_frame
from backend.app.v2.native_reader import NativeReader

VERSION = "1.0"
# Also supports a checksum-verified standalone script in /tmp, importing only the
# existing production libraries. No deployment is needed to execute the audit.
ROOT = Path(operations.__file__).resolve().parents[3]
MAX_POINTS = 100_000
MAX_PAYLOAD = 16 * 1024 * 1024
# Descriptive screening minima, not statistical significance guarantees. Five years
# of economic cycles is not implied by five years of data. Pair checks remain needed.
MINIMA = {
    "daily": (30, 756, 1260),
    "weekly": (13, 156, 260),
    "monthly": (12, 60, 120),
    "quarterly": (8, 32, 40),
    "annual": (5, 15, 20),
}


class AuditStopped(ValueError):
    """An incomplete audit must never be presented as a complete report."""


def timestamp(value, now):
    """Only verified, timezone-aware, nonfuture timestamps are evidence."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        parsed = datetime.fromtimestamp(value, UTC)
    else:
        parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed > now:
        raise ValueError("Invalid timestamp")
    return parsed.astimezone(UTC).isoformat()


def issue(items, code, severity, action):
    items.append({"code": code, "severity": severity, "recommended_fix": action})


def summarize_history(points, frequency, now, *, spec=None, definition=None):
    """Assess stored rows without repairing, filling or silently deduplicating them."""
    issues, parsed, seen = [], [], set()
    invalid = duplicates = nulls = revisions = 0
    for point in points:
        try:
            day = date.fromisoformat(point["date"])
            value = point["value"]
            if day > now.date() or day.year < 1800:
                raise ValueError("Outside supported audit calendar")
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
            ):
                raise ValueError("Invalid value")
            identity = point.get("key", point["date"])
            if definition:
                period = native_period(identity, definition)
                if period.start != day or point.get("end") != period.end.isoformat():
                    raise ValueError("Native period mismatch")
            if frequency == "monthly":
                identity = (day.year, day.month)
            elif frequency == "quarterly":
                identity = (day.year, (day.month - 1) // 3)
            elif frequency == "annual":
                identity = day.year
            elif frequency == "weekly" and spec:
                identity = pd.Timestamp(day).to_period("W-SUN")
            if identity in seen:
                duplicates += 1
            seen.add(identity)
            nulls += value is None
            revisions += max(0, int(point.get("revision", 1)) - 1)
            parsed.append((day, value))
        except (ValueError, TypeError, KeyError, OverflowError):
            invalid += 1
    parsed.sort()
    if invalid:
        issue(
            issues,
            "invalid_observations",
            "critical",
            "Reconcile invalid values/dates with stored source evidence; do not auto-repair.",
        )
    if duplicates:
        issue(
            issues,
            "duplicate_periods",
            "critical",
            "Resolve duplicate analytical periods using explicit source/vintage conventions.",
        )
    if spec and points and not invalid:
        try:
            validate_frame([(p["date"], p["value"]) for p in points], spec)
        except (ValueError, TypeError):
            issue(
                issues,
                "legacy_definition_validation_failed",
                "critical",
                "Reconcile stored history with the existing frequency/date/unit validation contract.",
            )
            invalid += 1
    valid = [(d, v) for d, v in parsed if v is not None]
    result = {
        "row_count": len(points),
        "valid_value_count": len(valid),
        "null_value_count": nulls,
        "invalid_count": invalid,
        "duplicate_period_count": duplicates,
        "first_observation": parsed[0][0].isoformat() if parsed else None,
        "last_observation": parsed[-1][0].isoformat() if parsed else None,
        "first_valid_observation": valid[0][0].isoformat() if valid else None,
        "last_valid_observation": valid[-1][0].isoformat() if valid else None,
        "coverage_days": (parsed[-1][0] - parsed[0][0]).days + 1 if parsed else 0,
        "expected_periods": None,
        "absent_periods": None,
        "completeness": None,
        "longest_complete_run": 0,
        "calendar_basis": "unknown",
        "stored_revision_increments": revisions,
        "suspicious_jump_count": 0,
        "constant_series": False,
    }
    if not parsed:
        issue(
            issues,
            "no_observations",
            "critical",
            "Inspect the existing ingestion/completeness evidence; this audit cannot ingest.",
        )
        return result, issues
    # Never calculate descriptive diagnostics over duplicate or invalid rows.
    if invalid or duplicates:
        return result, issues
    values = pd.Series(
        [v for _, v in parsed],
        index=pd.to_datetime([d for d, _ in parsed]),
        dtype=float,
    )
    if frequency in {"monthly", "quarterly", "annual"}:
        alias = {"monthly": "M", "quarterly": "Q", "annual": "Y"}[frequency]
        values.index = values.index.to_period(alias)
        grid = pd.period_range(values.index.min(), values.index.max(), freq=alias)
        result["calendar_basis"] = (
            "Native calendar periods between stored endpoints; no assumed prehistory or future releases"
        )
    elif frequency == "weekly":
        if spec:
            values.index = values.index.to_period("W-SUN")
            grid = pd.period_range(values.index.min(), values.index.max(), freq="W-SUN")
        else:
            grid = pd.date_range(values.index.min(), values.index.max(), freq="7D")
        result["calendar_basis"] = "Native weekly convention; no daily interpolation"
    elif frequency == "daily" and spec:
        frame, _ = session_frame(
            values.rename_axis("date").reset_index(name="value"), spec
        )
        grid = pd.DatetimeIndex(frame.date)
        result["calendar_basis"] = (
            "Existing US market/federal calendar approximation; unlisted closures remain review gaps"
        )
        issue(
            issues,
            "approximate_daily_calendar",
            "limitation",
            "Verify exchange/source-specific exceptional closures before event or gap-sensitive research.",
        )
    elif frequency == "daily":
        holidays = set(definition.calendar.holidays) if definition else set()
        # Native calendars do not declare every weekend rule. A weekday envelope
        # is a diagnostic only; actual supplied weekend values are retained.
        expected = {
            d
            for d in pd.bdate_range(values.index.min(), values.index.max())
            if d.date().isoformat() not in holidays
        }
        grid = pd.DatetimeIndex(sorted(expected | set(values.index)))
        result["calendar_basis"] = (
            "Weekday envelope plus declared holidays and actual source dates; unverified source session calendar"
        )
        issue(
            issues,
            "unverified_daily_calendar",
            "limitation",
            "Review source-specific sessions/publication calendar; missing weekdays are not proven data loss.",
        )
    else:
        issue(
            issues,
            "irregular_calendar",
            "limitation",
            "Use an explicit event/irregular-series method; regular-period research screens are unsupported.",
        )
        return result, issues
    result["expected_periods"] = len(grid)
    result["absent_periods"] = len(grid.difference(values.index))
    aligned = values.reindex(grid)
    result["completeness"] = float(aligned.notna().mean())
    run = best = 0
    for present in aligned.notna():
        run = run + 1 if present else 0
        best = max(best, run)
    result["longest_complete_run"] = best
    if result["absent_periods"] or nulls:
        issue(
            issues,
            "history_gaps",
            "review",
            "Reconcile gaps with source reporting schedules, sparse early history and legitimate closures; never fill automatically.",
        )
    differences = aligned.diff().dropna()
    if len(differences) >= 20:
        median = differences.median()
        mad = (differences - median).abs().median()
        if mad > 0:
            result["suspicious_jump_count"] = int(
                ((differences - median).abs() > 12 * 1.4826 * mad).sum()
            )
            if result["suspicious_jump_count"]:
                issue(
                    issues,
                    "large_changes_review",
                    "review",
                    "Inspect extreme changes against source revisions, units and real economic events; robust outliers are not proven errors.",
                )
    result["constant_series"] = values.dropna().nunique() <= 1
    if result["constant_series"]:
        issue(
            issues,
            "constant_values",
            "limitation",
            "Check whether a constant policy/administrative series is legitimate; variance-based methods are unavailable.",
        )
    return result, issues


def capabilities(history, frequency, metadata_ok, blocked=False):
    minima = MINIMA.get(frequency)
    result = {}
    for index, name in enumerate(
        ("comparisons", "anomaly_detection", "historical_relationships")
    ):
        reasons = []
        minimum = minima[index] if minima else None
        if not minimum:
            reasons.append("No regular-frequency method defined")
        if (
            blocked
            or history["invalid_count"]
            or history["duplicate_period_count"]
            or not metadata_ok
        ):
            reasons.append("Integrity/publication/metadata checks incomplete or failed")
        if minimum and history["longest_complete_run"] < minimum:
            reasons.append(
                f"Requires {minimum} consecutive nonmissing native periods; stored maximum is {history['longest_complete_run']}"
            )
        if name != "comparisons" and history["constant_series"]:
            reasons.append("No variation for variance-based screening")
        result[name] = {
            "status": "insufficient_or_unsupported"
            if reasons
            else "eligible_with_limitations",
            "minimum_complete_periods": minimum,
            "reasons": reasons,
            "conditions": "Descriptive data sufficiency only. Check actual transformations, pair overlap, compatible units/frequency, stationarity, effective samples and multiple screening. Does not grant AI/Discovery permission.",
        }
    return result


def public_ids(db, tables):
    """Enumerate grants before reader validation: broken public IDs cannot vanish."""
    ids = set(SPECS)
    for table, column in (
        ("norm_datasets", "id"),
        ("catalog_release_grants", "dataset_id"),
    ):
        if table in tables:
            ids.update(
                r[0]
                for r in db.execute(
                    f"SELECT {column} FROM {table} WHERE public_display=1"
                )
            )
    return sorted(ids)


def read_points(db, key, legacy):
    if legacy:
        record = db.execute(
            "SELECT checked_at,next_due,failures,length(CAST(payload AS BLOB)) size FROM source_cache WHERE id=?",
            (key,),
        ).fetchone()
        if record is None:
            return [], {}, {}
        if record["size"] > MAX_PAYLOAD:
            raise ValueError("Payload budget exceeded")
        payload = json.loads(
            db.execute(
                "SELECT payload FROM source_cache WHERE id=?", (key,)
            ).fetchone()[0]
        )
        points = payload.get("observations", [])
        if not isinstance(points, list) or len(points) > MAX_POINTS:
            raise ValueError("Observation budget exceeded")
        return points, dict(record), payload
    rows = db.execute(
        "SELECT period_key,reference_start,reference_end,value,revision FROM norm_observations WHERE dataset_id=? ORDER BY reference_start,period_key LIMIT ?",
        (key, MAX_POINTS + 1),
    ).fetchall()
    if len(rows) > MAX_POINTS:
        raise ValueError("Observation budget exceeded")
    return (
        [
            {"key": r[0], "date": r[1], "end": r[2], "value": r[3], "revision": r[4]}
            for r in rows
        ],
        {},
        {},
    )


def refresh_evidence(db, tables, row, cache, payload, now, issues):
    legacy, rule = row.get("legacy", False), row.get("refresh", {})
    result = {
        "configured": bool(
            legacy
            or rule.get("ingest_approved")
            and rule.get("automation_ready")
            and rule.get("mode") == "refresh"
        ),
        "registered_job": bool(cache) if legacy else False,
        "interval_seconds": {"daily": 21600, "weekly": 43200}.get(
            row.get("frequency"), 86400
        )
        if legacy
        else rule.get("check_seconds"),
        "runtime_worker_active": "unknown_offline_audit",
        "last_attempt": None,
        "last_successful_source_check": None,
        "last_completed_source_check": None,
        "last_observed_change": None,
        "next_scheduled_check": None,
        "failure_count": 0,
        "error_present": False,
        "new_observations_ingested": "not_separately_recorded",
        "historical_revisions_observed": None,
        "revision_processing": "Legacy refresh compares and retains revised latest-vintage history"
        if legacy
        else "Native reconciliation retains observation revisions; this is code support, not proof of a revision in this dataset",
    }
    meta = payload.get("release_metadata", {})
    if not isinstance(meta, dict):
        raise TypeError("Invalid release metadata")
    if legacy:
        raw = {
            "last_attempt": cache.get("checked_at"),
            "last_completed_source_check": cache.get("checked_at"),
            "last_successful_source_check": meta.get("last_source_success_at")
            or (
                payload.get("retrieved_at")
                if meta.get("source_check_succeeded") is True
                else None
            ),
            "next_scheduled_check": cache.get("next_due"),
        }
        result["failure_count"] = cache.get("failures", 0)
        result["error_present"] = bool(meta.get("source_error_code"))
        result["historical_revisions_observed"] = payload.get("revision_count")
    else:
        job = (
            db.execute(
                "SELECT last_attempt,last_check,last_success,last_change,next_due,failures,error_code FROM catalog_refresh_jobs WHERE dataset_id=?",
                (row["id"],),
            ).fetchone()
            if "catalog_refresh_jobs" in tables
            else None
        )
        result["registered_job"] = job is not None
        raw = (
            dict(
                zip(
                    (
                        "last_attempt",
                        "last_completed_source_check",
                        "last_successful_source_check",
                        "last_observed_change",
                        "next_scheduled_check",
                    ),
                    tuple(job)[:5],
                )
            )
            if job
            else {}
        )
        if job:
            result["failure_count"], result["error_present"] = job[5], bool(job[6])
        if "norm_revisions" in tables:
            result["historical_revisions_observed"] = db.execute(
                "SELECT COUNT(*) FROM norm_revisions WHERE dataset_id=?", (row["id"],)
            ).fetchone()[0]
    for name, value in raw.items():
        try:
            # Future next-check times are legitimate, unlike success timestamps.
            result[name] = timestamp(
                value,
                datetime.max.replace(tzinfo=UTC)
                if name == "next_scheduled_check"
                else now,
            )
        except (ValueError, TypeError, OverflowError, OSError):
            issue(
                issues,
                "invalid_refresh_timestamp",
                "review",
                "Reconcile malformed/future source-check timestamps; unknown is not success.",
            )
    result["successful_source_check_verified"] = (
        result["last_successful_source_check"] is not None
    )
    if not result["configured"] or not result["registered_job"]:
        issue(
            issues,
            "refresh_configuration_incomplete",
            "review",
            "Review existing policy and job registration without changing either during audit.",
        )
    if not result["successful_source_check_verified"]:
        issue(
            issues,
            "source_check_unverified",
            "review",
            "Review the existing refresh worker/source evidence; configuration alone is not verification.",
        )
    if result["failure_count"] or result["error_present"]:
        issue(
            issues,
            "refresh_failure",
            "review",
            "Use protected Data Health diagnostics to investigate source failures; retain last-good observations.",
        )
    success = result["last_successful_source_check"]
    if (
        success
        and (now - datetime.fromisoformat(success)).total_seconds()
        > (result["interval_seconds"] or 86400) * 2 + 3600
    ):
        issue(
            issues,
            "source_check_overdue",
            "review",
            "Review runtime Data Health and source backoff; offline configuration does not prove worker liveness.",
        )
    # Do not export arbitrary provider errors/provenance, which may contain secrets.
    result["error_classification"] = (
        "source_failure_review" if result["error_present"] else None
    )
    return result


def dataset_report(db, tables, row, reader, now):
    key, issues = row["id"], []
    spec = SPECS.get(key)
    publication = reader.publications.get(key)
    definition = publication.definition if publication else None
    publication_ok = spec is not None
    if not spec:
        try:
            reader._permission(
                db, key
            )  # Same snapshot, existing deny-by-default validator.
            publication_ok = True
        except (ValueError, KeyError, TypeError, sqlite3.DatabaseError):
            issue(
                issues,
                "publication_evidence_invalid",
                "critical",
                "Reconcile grant, definition-bound rights and active-generation completeness. Dataset remains in this audit; no permissions are changed.",
            )
    metadata = {
        name: row.get(name)
        for name in (
            "name",
            "provider",
            "source_identifier",
            "description",
            "region",
            "frequency",
            "units",
            "adjustment",
            "definition_hash",
        )
    }
    metadata["unit_multiplier"] = definition.unit_multiplier if definition else 0
    metadata["observation_convention"] = (
        definition.calendar.id
        if definition
        else spec.observation_type
        if spec
        else None
    )
    metadata["source_url"] = (
        publication.source_url if publication else spec.source_url if spec else None
    )
    metadata["allowed_transformations"] = (
        list(spec.allowed_transformations)
        if spec
        else reader._metadata(publication, db)["allowed_transformations"]
        if publication_ok
        else []
    )
    metadata["revision_behavior"] = (
        "Latest revised observations; not point-in-time vintages"
    )
    metadata["publication_schedule"] = (
        "Declared release instants in native calendar; reference periods are not publication timestamps"
        if definition and definition.calendar.releases
        else "No complete verified release calendar in stored definition; release lag requires source-specific review"
    )
    required = (
        "name",
        "provider",
        "source_identifier",
        "region",
        "frequency",
        "units",
        "adjustment",
        "observation_convention",
        "source_url",
    )
    missing = [name for name in required if metadata.get(name) in (None, "", "unknown")]
    metadata["missing_fields"] = missing
    if missing:
        issue(
            issues,
            "metadata_missing",
            "review",
            "Review missing definition metadata: " + ", ".join(missing),
        )
    if not metadata["description"]:
        issue(
            issues,
            "description_missing",
            "limitation",
            "Add a reviewed economic definition beyond a provider selector.",
        )
    limitations = (
        list(spec.known_limitations)
        if spec
        else list(publication.limitations)
        if publication
        else []
    )
    # Reuse the existing reviewed suitability artifact; it is dated documentary
    # evidence, explicitly not a numerical production audit.
    reviewed_path = (
        ROOT
        / "research/audits/2026-10-30-dataset-suitability/PUBLIC_DATASET_MATRIX.json"
    )
    reviewed = next(
        (
            r
            for r in json.loads(reviewed_path.read_text(encoding="utf-8"))["datasets"]
            if r["id"] == key
        ),
        None,
    )
    suitability_review = (
        {
            k: reviewed[k]
            for k in (
                "suitable_for",
                "unsuitable_for",
                "revision_methodology",
                "continuity_and_presentation_risks",
                "evidence",
            )
        }
        if reviewed
        else None
    )
    if reviewed:
        metadata["revision_behavior"] = reviewed["revision_methodology"]
        limitations.append(reviewed["continuity_and_presentation_risks"])
    points, cache, payload = [], {}, {}
    try:
        # Do not inspect observations for unknown/invalid publication boundaries.
        if publication_ok:
            points, cache, payload = read_points(db, key, spec is not None)
        history, findings = summarize_history(
            points, row.get("frequency"), now, spec=spec, definition=definition
        )
        issues.extend(findings)
    except (ValueError, TypeError, KeyError, OverflowError):
        history, _ = summarize_history([], row.get("frequency"), now)
        issue(
            issues,
            "stored_history_unreadable_or_over_budget",
            "critical",
            "Inspect malformed stored observations or reduce an independently reviewed audit scope/budget; no truncated history is certified.",
        )
    try:
        refresh = refresh_evidence(db, tables, row, cache, payload, now, issues)
    except (ValueError, TypeError, KeyError):
        refresh = {
            "successful_source_check_verified": False,
            "configured": False,
            "runtime_worker_active": "unknown_offline_audit",
        }
        issue(
            issues,
            "refresh_evidence_invalid",
            "review",
            "Reconcile malformed refresh evidence without inferring success.",
        )
    freshness = {
        "status": "unknown",
        "next_release_date": None,
        "method": "No claim of a missing future release",
    }
    last = history["last_valid_observation"]
    if last and spec:
        stale, reason, release = assess_freshness(
            spec, date.fromisoformat(last), now.date()
        )
        freshness = {
            "status": "source_lag_review" if stale else "within_existing_expectation",
            "method": reason,
            "next_release_date": release.get("next_release_date"),
        }
    elif last:
        next_release = definition.calendar.next_release(now) if definition else None
        freshness = {
            "status": "awaiting_declared_release"
            if next_release
            else "source_lag_review"
            if (now.date() - date.fromisoformat(last)).days
            > LAGS.get(row.get("frequency"), 550)
            else "within_coarse_review_threshold",
            "next_release_date": next_release.isoformat() if next_release else None,
            "method": "Declared future release if available; otherwise existing Data Health age threshold is a review trigger, not a stale-data verdict",
        }
    if freshness["status"] == "source_lag_review":
        issue(
            issues,
            "observation_lag_review",
            "review",
            "Check actual producer release/publication schedule before declaring the dataset stale.",
        )
    caps = capabilities(history, row.get("frequency"), not missing, not publication_ok)
    history["status"] = (
        "integrity_failure"
        if any(x["severity"] == "critical" for x in issues)
        else "review_gaps_or_extremes"
        if any(x["code"] in {"history_gaps", "large_changes_review"} for x in issues)
        else "stored_structure_checked"
    )
    if caps["comparisons"]["status"] != "eligible_with_limitations":
        issue(
            issues,
            "insufficient_comparison_history",
            "review",
            "Review native coverage and complete runs for the intended research use; never apply a universal history requirement.",
        )
    critical = any(x["severity"] == "critical" for x in issues)
    review = any(x["severity"] in {"review", "limitation"} for x in issues)
    classification = (
        "Needs attention"
        if critical
        else "Usable with limitations"
        if review
        or limitations
        or any(c["status"] != "eligible_with_limitations" for c in caps.values())
        else "Research ready"
    )
    return {
        "id": key,
        "classification": classification,
        "metadata": metadata,
        "historical_quality": history,
        "research_suitability": caps,
        "existing_documentary_suitability_review": suitability_review,
        "refresh": refresh,
        "freshness": freshness,
        "known_limitations": limitations,
        "issues": issues,
        "permissions": {
            "audit_grants_nothing": True,
            "ai_and_discovery": "unchanged; analytical eligibility is not authorization",
        },
    }


def audit(database, *, expected_public=194, evidence_origin, now=None, max_seconds=90):
    path = Path(database).resolve(strict=True)
    if not path.is_file() or not 1 <= max_seconds <= 120:
        raise ValueError("Existing database and 1..120 second budget required")
    if evidence_origin not in {"production", "production-backup", "fixture", "local"}:
        raise ValueError("Explicit evidence origin required")
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("Timezone-aware audit time required")
    started = monotonic()
    rows = {r["id"]: r for r in registry()}
    reader = NativeReader(path, now_fn=lambda: now)
    with closing(
        sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        # Defense in depth: the connection cannot write even if a reused reader regresses.
        allowed = {
            sqlite3.SQLITE_SELECT,
            sqlite3.SQLITE_READ,
            sqlite3.SQLITE_FUNCTION,
            sqlite3.SQLITE_TRANSACTION,
        }
        db.set_authorizer(
            lambda action, *_: (
                sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY
            )
        )
        db.set_progress_handler(lambda: int(monotonic() - started > max_seconds), 1000)
        db.execute("BEGIN")
        tables = {
            r[0]
            for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if "source_cache" not in tables:
            raise AuditStopped(
                "Required legacy storage schema absent; no migration attempted"
            )
        ids = public_ids(db, tables)
        if len(ids) > 1000:
            raise AuditStopped("Public scope exceeds reviewed audit bound")
        datasets = []
        for key in ids:
            if monotonic() - started > max_seconds:
                raise AuditStopped("Time budget exceeded; no complete report produced")
            datasets.append(
                dataset_report(db, tables, rows.get(key, {"id": key}), reader, now)
            )
        schema = (
            [
                r[0]
                for r in db.execute(
                    "SELECT version FROM catalog_schema_versions ORDER BY version"
                )
            ]
            if "catalog_schema_versions" in tables
            else []
        )
    counts = Counter(r["classification"] for r in datasets)
    codes = Counter(x["code"] for r in datasets for x in r["issues"])
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unknown"
    return {
        "audit_version": VERSION,
        "as_of": now.isoformat(),
        "code_revision": revision,
        "audit_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "evidence_origin": evidence_origin,
        "origin_note": "Operator-declared origin; not independently attested by the tool",
        "database_schema_versions": schema,
        "snapshot": "Single read-only SQLite transaction; no source requests",
        "elapsed_seconds": round(monotonic() - started, 3),
        "production_mutations": 0,
        "scope": {
            "expected_public": expected_public,
            "actual_public": len(ids),
            "matches_expected": len(ids) == expected_public,
            "all_enumerated_public_ids_evaluated": True,
        },
        "summary": {
            "classifications": {
                c: counts[c]
                for c in (
                    "Research ready",
                    "Usable with limitations",
                    "Needs attention",
                )
            },
            "issue_counts": dict(sorted(codes.items())),
            "configured_refresh": sum(
                r["refresh"].get("configured", False) for r in datasets
            ),
            "verified_successful_source_checks": sum(
                r["refresh"]["successful_source_check_verified"] for r in datasets
            ),
            "eligible_by_use": {
                name: [
                    r["id"]
                    for r in datasets
                    if r["research_suitability"][name]["status"]
                    == "eligible_with_limitations"
                ]
                for name in (
                    "comparisons",
                    "anomaly_detection",
                    "historical_relationships",
                )
            },
        },
        "methodology": {
            "minimum_complete_periods": MINIMA,
            "capabilities_are_permissions": False,
            "production_audit_passed": "No blanket pass: inspect classifications, limitations and scope reconciliation",
            "limits": "No live source revalidation, pairwise certification, point-in-time vintage certification, per-row cryptographic provenance rehash or automated repairs. Daily calendars approximate sessions. Change timestamps do not distinguish inserts from revisions. Original 30 legacy IDs remain public by existing code policy.",
        },
        "resources": resources(path),
        "datasets": datasets,
    }


def markdown(report):
    scope = report["scope"]
    lines = [
        "# Data Quality and Research Readiness Audit",
        "",
        f"As of: {report['as_of']} · evidence: {report['evidence_origin']} (operator declared)",
        f"Code: `{report['code_revision']}` · schema: {report['database_schema_versions']}",
        "",
        f"Public datasets: **{scope['actual_public']} / expected {scope['expected_public']}**. Scope match: **{scope['matches_expected']}**.",
        "All enumerated public IDs evaluated. No source requests, ingestion, migrations, permission changes or deployments.",
        "",
    ]
    lines += [
        f"- {name}: **{count}**"
        for name, count in report["summary"]["classifications"].items()
    ]
    lines += [
        "",
        f"Refresh configured: {report['summary']['configured_refresh']}; stored successful source checks verified: {report['summary']['verified_successful_source_checks']}. Worker activity is unknown in an offline audit.",
        "New ingestion and historical revisions are distinct; last change is not an insert count. Zero revisions does not prove revisions were checked.",
        "",
        "## Recommended fixes by severity",
        "",
    ]
    for severity in ("critical", "review", "limitation"):
        grouped = {}
        for row in report["datasets"]:
            for item in row["issues"]:
                if item["severity"] == severity:
                    group = grouped.setdefault(
                        item["code"], {"ids": [], "fix": item["recommended_fix"]}
                    )
                    group["ids"].append(row["id"])
        for code, group in sorted(grouped.items()):
            lines += [
                f"- **{severity}: {code}** ({len(group['ids'])}): {', '.join(group['ids'])}. {group['fix']}"
            ]
    lines += [
        "",
        "## Dataset results",
        "",
        "| Dataset | Classification | Valid / rows | First / last valid | Comparisons | Anomalies | Relationships |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in report["datasets"]:
        h, c = row["historical_quality"], row["research_suitability"]
        lines.append(
            f"| {row['id']} | {row['classification']} | {h['valid_value_count']} / {h['row_count']} | {h['first_valid_observation']} / {h['last_valid_observation']} | "
            + " | ".join(
                c[k]["status"]
                for k in (
                    "comparisons",
                    "anomaly_detection",
                    "historical_relationships",
                )
            )
            + " |"
        )
    lines += [
        "",
        "## Interpretation and Data Health",
        "",
        "Eligibility is descriptive sufficiency, not statistical validity, permission or causal evidence. Pair overlap, transformations and effective samples still require investigation-specific checks. Research ready is scoped to these checks, not independent source certification.",
        "Keep operational Data Health unchanged. A future dashboard can link these readiness findings separately from configured refresh and verified source checks. Inspect gap calendars, metadata and use-specific history before broadening Discovery or AI.",
        report["methodology"]["limits"],
        "",
    ]
    return "\n".join(lines)


def flatten(value, prefix=""):
    result = {}
    for key, item in value.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            result.update(flatten(item, name))
        else:
            result[name] = (
                json.dumps(item, ensure_ascii=False) if isinstance(item, list) else item
            )
    return result


def write_reports(report, output, database):
    output, database = Path(output).resolve(), Path(database).resolve()
    if output == database.parent or database.parent in output.parents:
        raise ValueError("Reports must be outside the database directory")
    output.mkdir(parents=True, exist_ok=False)  # Never overwrite a report or database.
    (output / "audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output / "summary.md").write_text(markdown(report), encoding="utf-8")
    records = [flatten(row) for row in report["datasets"]]
    fields = sorted({key for row in records for key in row})
    with (output / "datasets.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        # Spreadsheet formula injection protection, without changing JSON evidence.
        for row in records:
            writer.writerow(
                {
                    k: "'" + v
                    if isinstance(v, str)
                    and v.startswith(("=", "+", "-", "@", "\t", "\r"))
                    else v
                    for k, v in row.items()
                }
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="New directory outside the database directory",
    )
    parser.add_argument("--expected-public", type=int, default=194)
    parser.add_argument(
        "--evidence-origin",
        choices=("production", "production-backup", "fixture", "local"),
        required=True,
    )
    parser.add_argument("--max-seconds", type=int, default=90)
    args = parser.parse_args()
    try:
        report = audit(
            args.database,
            expected_public=args.expected_public,
            evidence_origin=args.evidence_origin,
            max_seconds=args.max_seconds,
        )
        write_reports(report, args.output, args.database)
    except (OSError, ValueError, sqlite3.DatabaseError):
        parser.exit(
            1,
            "Audit stopped: unreadable schema/history, resource/time budget, or unsafe output path. No complete audit certified. No database writes attempted.\n",
        )
    print(
        f"Reports: {args.output.resolve()} · public={report['scope']['actual_public']} · scope_match={report['scope']['matches_expected']}"
    )
    if not report["scope"]["matches_expected"]:
        parser.exit(
            2,
            "Public count mismatch: reports retained for reconciliation; not a successful scope check.\n",
        )


if __name__ == "__main__":
    main()
