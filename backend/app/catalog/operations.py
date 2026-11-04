"""One read-only reconciliation of planning, publication and operational state.

No network requests, migrations, observations, credentials or permission writes.
Planning permissions are never interpreted as runtime publication grants.
"""

import json
import shutil
import sqlite3
from collections import Counter
from contextlib import closing
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from backend.app.catalog.manifest import Manifest
from backend.app.catalog.releases import candidates
from backend.app.ingestion.catalog_refresh import CONFIG, source_entries
from backend.app.v2.definitions import SPECS
from backend.app.v2.native_reader import NativeReader

LAGS = {"daily": 10, "weekly": 28, "monthly": 120, "quarterly": 240, "annual": 550}


def registry():
    manifest = Manifest.load()
    entries = source_entries()
    pubs = candidates()
    rules = {r["id"]: r for r in json.loads(CONFIG.read_text())["datasets"]}
    rows = []
    for key in sorted(set(entries) | set(pubs) | set(SPECS)):
        entry, pub, spec = entries.get(key, {}), pubs.get(key), SPECS.get(key)
        definition = asdict(pub.definition) if pub else None
        source = entry.get("source", {})
        rows.append(
            {
                "id": key,
                "kind": entry.get("kind", "series"),
                "name": spec.name if spec else pub.name if pub else entry["name"],
                "description": spec.definition
                if spec
                else entry.get("definition_note", ""),
                "region": spec.region
                if spec
                else pub.region
                if pub
                else entry["region"],
                "category": spec.category
                if spec
                else pub.category
                if pub
                else entry["category"],
                "provider": spec.provider if spec else source.get("provider"),
                "source_owner_evidence": spec.primary_source_url
                if spec
                else source.get("endpoint"),
                "source_identifier": spec.provider_id
                if spec
                else source.get("selector"),
                "units": spec.units
                if spec
                else pub.definition.units
                if pub
                else entry["units"],
                "frequency": spec.frequency if spec else entry["frequency"],
                "adjustment": spec.seasonal_adjustment
                if spec
                else entry["seasonal_adjustment"],
                "definition_hash": pub.definition.fingerprint if pub else None,
                "native_definition": definition,
                "rights": {
                    "state": "inherited_unverified" if spec else "unreviewed",
                    "evidence": entry.get("rights", {}).get("evidence", []),
                },
                "planning_refs": entry.get("planning_refs", []),
                "legacy": key in SPECS,
                "refresh": {
                    "mechanism": "persistent_legacy_cache"
                    if spec
                    else "partitioned_native"
                    if key in rules
                    else "unsupported",
                    **rules.get(key, {}),
                },
                "observations": None,
                "publication": "runtime_grant_required"
                if pub
                else "legacy_public"
                if spec
                else entry.get("publication", {}).get("status", "planned"),
                "aliases": [],
                "source_evidence": entry.get("source_evidence", []),
            }
        )
    # Exact selector equivalence is an alias, never an automatic ID substitution.
    identities = {}
    for row in rows:
        identities.setdefault(
            (
                row["provider"],
                row["source_identifier"],
                row["region"],
                row["frequency"],
            ),
            [],
        ).append(row["id"])
    for row in rows:
        row["aliases"] = [
            k
            for k in identities[
                (
                    row["provider"],
                    row["source_identifier"],
                    row["region"],
                    row["frequency"],
                )
            ]
            if k != row["id"]
        ]
    assert set(SPECS) <= {r["id"] for r in rows}
    # Validation of the original manifest remains authoritative, even for overrides.
    assert manifest.page(limit=1, audience="planning")["total"] > 0
    return rows


def resources(database):
    path = Path(database)
    result = {
        "sqlite_bytes": {
            suffix or "database": p.stat().st_size
            if (p := Path(str(path) + suffix)).exists()
            else 0
            for suffix in ("", "-wal", "-shm")
        },
        "free_disk_bytes": shutil.disk_usage(path.parent).free,
    }
    cg = Path("/sys/fs/cgroup")
    for name in (
        "memory.current",
        "memory.peak",
        "memory.max",
        "memory.events",
        "cpu.max",
    ):
        try:
            result[name] = (cg / name).read_text().strip()
        except OSError:
            result[name] = None
    result["disk_attention"] = (
        sum(result["sqlite_bytes"].values()) >= 300 * 1024**2
        or result["free_disk_bytes"] < 150 * 1024**2
    )
    return result


def health(
    database,
    *,
    scheduler=None,
    refresh=None,
    now=None,
    offset=0,
    limit=100,
    public_only=True,
):
    """Bounded metadata report; only indexed endpoint dates, never full histories."""
    if not 0 <= offset <= 100000 or not 1 <= limit <= 400:
        raise ValueError("Invalid health page")
    now = now or datetime.now(UTC)
    reader = NativeReader(Path(database))
    rows = registry()
    with closing(
        sqlite3.connect(
            Path(database).resolve().as_uri() + "?mode=ro", uri=True, timeout=2
        )
    ) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        tables = {
            r[0]
            for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        legacy = {
            r["id"]: dict(r)
            for r in db.execute(
                "SELECT id,checked_at,next_due,failures,json_array_length(payload,'$.observations') observation_count,json_extract(payload,'$.retrieved_at') retrieved_at,json_extract(payload,'$.latest_observation_date') latest,json_extract(payload,'$.status') status,json_extract(payload,'$.release_metadata') metadata FROM source_cache"
            )
        }
        jobs = (
            {
                r["dataset_id"]: dict(r)
                for r in db.execute(
                    "SELECT dataset_id,last_attempt,last_check,last_success,last_change,failures,error_code,next_due FROM catalog_refresh_jobs"
                )
            }
            if "catalog_refresh_jobs" in tables
            else {}
        )
        for row in rows:
            key = row["id"]
            public = key in SPECS
            if key in reader.publications:
                try:
                    reader._permission(db, key)
                    public = True
                except ValueError:
                    pass
            row["public_display"] = public
            # No rights are upgraded because a name exists in a configuration file.
            row["ai_allowed"] = False
            row["discovery_allowed"] = (
                False if key not in SPECS else "existing_legacy_policy_unchanged"
            )
            row["last_success"] = row["last_check"] = row["next_check"] = row[
                "latest_observation_date"
            ] = None
            row["failures"] = 0
            row["error_code"] = None
            row["automatic_refresh"] = False
            if not public:
                row["health"] = "private_or_unpublished"
                continue
            if key in SPECS:
                cache = legacy.get(key, {})
                meta = json.loads(cache.get("metadata") or "{}")
                row.update(
                    observation_count=cache.get("observation_count"),
                    last_check=cache.get("checked_at"),
                    last_success=meta.get("last_source_success_at")
                    or (
                        cache.get("retrieved_at")
                        if meta.get("source_check_succeeded") is True
                        else None
                    ),
                    next_check=cache.get("next_due"),
                    latest_observation_date=cache.get("latest"),
                    failures=cache.get("failures", 0),
                    error_code=meta.get("source_error_code"),
                )
                row["automatic_refresh"] = bool((scheduler or {}).get("ready"))
            else:
                row["rights"] = {
                    "state": "permitted",
                    "evidence": reader.publications[key].rights_evidence,
                    "license_url": reader.publications[key].license_url,
                    "attribution": reader.publications[key].attribution,
                }
                row["observation_count"] = db.execute(
                    "SELECT SUM(x.point_count) FROM norm_dataset_state s JOIN norm_partitions p ON p.generation_id=s.active_generation JOIN norm_pages x ON x.partition_id=p.id WHERE s.dataset_id=?",
                    (key,),
                ).fetchone()[0]
                job = jobs.get(key, {})
                latest = db.execute(
                    "SELECT reference_start FROM norm_observations WHERE dataset_id=? AND value IS NOT NULL ORDER BY reference_start DESC,period_key DESC LIMIT 1",
                    (key,),
                ).fetchone()
                row.update(
                    last_check=job.get("last_check"),
                    last_success=job.get("last_success"),
                    next_check=datetime.fromtimestamp(job["next_due"], UTC).isoformat()
                    if job.get("next_due")
                    else None,
                    latest_observation_date=latest[0] if latest else None,
                    failures=job.get("failures", 0),
                    error_code=job.get("error_code"),
                )
                row["automatic_refresh"] = bool(
                    (refresh or {}).get("enabled")
                    and not (refresh or {}).get("error_code")
                    and row["refresh"].get("ingest_approved")
                    and row["refresh"].get("automation_ready")
                    and (scheduler or {}).get("ready")
                )
            row["expected_frequency"] = row["frequency"]
            row["observation_attention"] = bool(
                row["latest_observation_date"]
                and (
                    now.date()
                    - datetime.fromisoformat(row["latest_observation_date"]).date()
                ).days
                > LAGS.get(row["frequency"], 550)
            )
            age = (
                (now - datetime.fromisoformat(row["last_success"])).total_seconds()
                if row["last_success"]
                else None
            )
            budget = row["refresh"].get("check_seconds", 86400) * 2 + 3600
            row["health"] = (
                "refresh_disabled"
                if not row["automatic_refresh"]
                else "source_failure"
                if row["failures"]
                else "never_verified"
                if age is None
                else "check_overdue"
                if age > budget
                else "source_lag_review"
                if row["observation_attention"]
                else "healthy"
            )
            row["freshness_note"] = (
                "A successful source check is distinct from a new observation; lag thresholds are review triggers, not invented release calendars."
            )
    public = [r for r in rows if r["public_display"]]
    filtered = public if public_only else rows
    states = Counter(r["health"] for r in public)
    return {
        "as_of": now.isoformat(),
        "summary": {
            "registered": len(rows),
            "public": len(public),
            "automatic_refresh": sum(r["automatic_refresh"] for r in public),
            "verified_automatic_refresh": sum(
                bool(r["automatic_refresh"] and r["last_success"] and not r["failures"])
                for r in public
            ),
            "healthy": states["healthy"],
            "needs_attention": len(public) - states["healthy"],
            "states": dict(states),
        },
        "items": filtered[offset : offset + limit],
        "total": len(filtered),
        "next_offset": offset + limit if offset + limit < len(filtered) else None,
        "resources": resources(database),
        "production_mutations": 0,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--registry", action="store_true")
    args = parser.parse_args()
    if args.registry:
        print(json.dumps({"datasets": registry()}, indent=2))
    elif args.database and args.database.is_file():
        print(json.dumps(health(args.database, public_only=False, limit=400), indent=2))
    else:
        parser.error(
            "Existing database or --registry required; CLI never assumes scheduler liveness"
        )


if __name__ == "__main__":
    main()
