"""Explicit, resumable release-100 operations. Never an application startup hook.

Preparation is off-Render only. Production operations always require an explicit
database, reviewed revision, disabled workers and verified independent backup.
No operation enables a scheduler, migrates schemas or replaces a database.
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import tempfile
import time
from contextlib import closing
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from backend.app.catalog.manifest import LEGACY_PUBLIC_SOURCES
from backend.app.catalog.release_cli import ingest
from backend.app.catalog.releases import (
    activate,
    candidates,
    migrate as release_migrate,
)
from backend.app.ingestion.catalog_refresh import (
    CONFIG,
    CatalogRefresh,
    migrate as refresh_migrate,
)
from backend.app.ingestion.native import digest, native_period
from backend.app.ingestion.partition_schema import migrate as native_migrate
from backend.app.v2.native_reader import NativeReader
from backend.app.v2.state import Store

ROOT = Path(__file__).resolve().parents[3]
PLAN = ROOT / "research/releases/release-100/selection.json"
PRIVATE = ("wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly")
MIB = 1024 * 1024


def file_sha256(path):
    hasher = sha256()
    with Path(path).open("rb") as source:
        while block := source.read(MIB):
            hasher.update(block)
    return hasher.hexdigest()


def load_plan():
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    pubs = candidates()
    old, new = plan["existing_native_ids"], plan["additional_ids"]
    if len(old) != 13 or len(new) != 57 or len(set(old + new)) != 70:
        raise ValueError("Exact 13 + 57 release required")
    rows = {r["id"]: r for r in plan["datasets"]}
    rules = {r["id"]: r for r in json.loads(CONFIG.read_text())["datasets"]}
    if set(rows) != set(old + new) or {
        k for k, r in rules.items() if r["ingest_approved"]
    } != set(rows):
        raise ValueError("Release/config approvals differ")
    for key, row in rows.items():
        p = pubs[key]
        if (
            row["definition_hash"] != p.definition.fingerprint
            or row["rights_evidence"] != p.rights_evidence
            or row["source_url"] != p.source_url
            or row["license_url"] != p.license_url
            or row["attribution"] != list(p.attribution)
            or row["publication_approved"] is not (key in new)
            or row["refresh_approved"] is not True
            or row["ai_allowed"] is not False
            or row["discovery_allowed"] is not False
            or not rules[key]["automation_ready"]
            or rules[key]["mode"] != "refresh"
        ):
            raise ValueError("Definition, rights or independent scope approval differs")
    return plan


def plan_hash():
    # Canonical JSON, independent of Windows checkout line endings.
    return digest(load_plan())


def bundle_index(directory):
    if (
        Path(directory).is_symlink()
        or (Path(directory) / "snapshots").is_symlink()
        or (Path(directory) / "manifest.json").is_symlink()
    ):
        raise ValueError("Bundle paths must not be symlinks")
    directory = Path(directory).resolve()
    if directory.is_symlink():
        raise ValueError("Bundle directory must not be a symlink")
    manifest = json.loads((directory / "manifest.json").read_text())
    captured = datetime.fromisoformat(manifest["created_at"])
    if captured.tzinfo is None:
        raise ValueError("Capture timezone required")
    age = (datetime.now(UTC) - captured).total_seconds()
    if captured.tzinfo is None or not 0 <= age <= 7 * 86400:
        raise ValueError("Capture must be timezone-aware and no older than seven days")
    plan = load_plan()
    if manifest["plan_sha256"] != plan_hash():
        raise ValueError("Bundle belongs to another reviewed plan")
    records = manifest["datasets"]
    if set(records) != set(plan["existing_native_ids"] + plan["additional_ids"]):
        raise ValueError("Exact 70 snapshots required")
    if sum(r["bytes"] for r in records.values()) > 96 * MIB:
        raise ValueError("Bundle exceeds storage bound")
    pubs = candidates()
    for key, record in records.items():
        path = directory / "snapshots" / (record["snapshot_hash"] + ".json")
        if (
            path.is_symlink()
            or path.resolve().parent != (directory / "snapshots").resolve()
        ):
            raise ValueError("Unsafe snapshot path")
        body = path.read_bytes()
        if (
            len(body) != record["bytes"]
            or len(body) > 16 * MIB
            or sha256(body).hexdigest() != record["snapshot_hash"]
        ):
            raise ValueError("Snapshot checksum/size differs")
        snapshot = json.loads(body)
        pub = pubs[key]
        if (
            snapshot["definition_hash"] != pub.definition.fingerprint
            or snapshot["source_url"] != pub.source_url
        ):
            raise ValueError("Snapshot identity differs")
        if (
            len(snapshot["points"]) != record["rows"]
            or not 1 <= record["rows"] <= 50000
        ):
            raise ValueError("Snapshot count differs")
        record["snapshot_path"] = str(path)
    return records


def prepare(directory):
    if os.getenv("RENDER_SERVICE_ID") or str(Path(directory).resolve()).startswith(
        "/var/data"
    ):
        raise ValueError("Capture and audit off-Render; never prepare on production")
    plan = load_plan()
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    (directory / "snapshots").mkdir()
    pubs = candidates()
    rules = json.loads(CONFIG.read_text())["datasets"]
    captures, audit = {}, []
    with tempfile.TemporaryDirectory(prefix="release100-capture-") as scratch:
        scratch = Path(scratch)
        store = Store(scratch / "disposable.sqlite3")
        with store.connection(True) as db:
            native_migrate(db)
            release_migrate(db)
            refresh_migrate(db)
        config = scratch / "policy.json"
        config.write_text(
            json.dumps(
                {
                    "datasets": [
                        r | {"ingest_approved": True, "mode": "stage"}
                        for r in rules
                        if r["automation_ready"]
                    ]
                }
            )
        )
        engine = CatalogRefresh(store, config=config)
        selected = set(plan["existing_native_ids"] + plan["additional_ids"])
        from backend.app.ingestion.catalog_refresh import endpoint

        ordered = sorted(
            rules,
            key=lambda r: (
                not r["automation_ready"],
                endpoint(engine.entries[r["id"]]),
            ),
        )
        cooled = set()
        for rule in ordered:
            key, p = rule["id"], pubs[rule["id"]]
            record = {
                "id": key,
                "name": p.name,
                "provider": p.definition.provider,
                "region": p.region,
                "units": p.definition.units,
                "frequency": p.definition.frequency,
                "adjustment": p.definition.adjustment,
                "selector": p.definition.selector,
                "definition_hash": p.definition.fingerprint,
                "source_url": p.source_url,
                "license_url": p.license_url,
                "rights_evidence": p.rights_evidence,
                "selected": key in selected,
                "publication_approved": key in plan["additional_ids"],
                "rights_review": "Prior dataset-specific evidence retained; only selected IDs approved by this release",
                "ai_allowed": False,
                "discovery_allowed": False,
            }
            if not rule["automation_ready"]:
                record.update(
                    state="technical_hold",
                    reason=rule["blocker"],
                    availability="not certified current; prior capture is not refresh eligibility",
                )
            else:
                try:
                    if p.definition.provider in cooled:
                        raise ValueError("provider cooldown")
                    pending, _ = engine._download(
                        key,
                        {
                            "content_hash": None,
                            "raw_hash": None,
                            "etag": None,
                            "last_modified": None,
                        },
                    )
                    path = Path(pending["path"])
                    frozen = json.loads(path.read_text())
                    record.update(
                        state="source_validated",
                        rows=len(frozen["points"]),
                        source_hash=frozen["source_hash"],
                    )
                    if key in selected:
                        shutil.copyfile(path, directory / "snapshots" / path.name)
                        captures[key] = {
                            "snapshot_hash": pending["snapshot"],
                            "bytes": path.stat().st_size,
                            "rows": len(frozen["points"]),
                        }
                    path.unlink()
                except Exception as exc:  # noqa: BLE001 -- independent source failure, no implicit approval
                    code = getattr(exc, "code", "source_validation_failed")
                    if code == "http_429":
                        cooled.add(p.definition.provider)
                    record.update(state="source_hold", reason=code)
                time.sleep(0.2)
            audit.append(record)
            print(json.dumps({"id": key, "state": record["state"]}), flush=True)
        (directory / "audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    if set(captures) != selected:
        raise ValueError("Selected source failed; no complete release manifest written")
    manifest = {
        "release": plan["release"],
        "created_at": datetime.now(UTC).isoformat(),
        "plan_sha256": plan_hash(),
        "datasets": captures,
    }
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    bundle_index(directory)
    return {
        "captured": len(captures),
        "audited": len(audit),
        "production_access": False,
    }


def public_ids(reader):
    return set(LEGACY_PUBLIC_SOURCES) | {r["id"] for r in reader.catalogue()}


def check(database, *, allow_refresh=False):
    plan = load_plan()
    if not Path(database).is_file():
        raise ValueError("Existing explicit database required")
    for flag in ("MACROLENS_INGESTION_ENABLED", "MACROLENS_AI_ENABLED"):
        if os.getenv(flag, "0").lower() not in {"0", "false", ""}:
            raise ValueError("World Bank ingestion and AI must remain disabled")
    if not allow_refresh and os.getenv(
        "MACROLENS_CATALOG_REFRESH_ENABLED", "0"
    ).lower() not in {"0", "false", ""}:
        raise ValueError("Pause catalog refresh before release operations")
    reader = NativeReader(Path(database))
    current = public_ids(reader)
    old = set(LEGACY_PUBLIC_SOURCES) | set(plan["existing_native_ids"])
    if not old <= current or current - old - set(plan["additional_ids"]):
        raise ValueError("Existing public IDs missing or unrelated grants present")
    with closing(
        sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    ) as db:
        if db.execute(
            "SELECT name FROM catalog_schema_versions WHERE version=4"
        ).fetchone() != ("catalog_refresh_jobs",):
            raise ValueError(
                "Explicit schema 4 migration required; release never migrates"
            )
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity failed")
        for key in PRIVATE:
            row = db.execute(
                "SELECT public_display,ai_allowed,rights_state FROM ingest_datasets WHERE id=?",
                (key,),
            ).fetchone()
            if row and row != (0, 0, "unreviewed"):
                raise ValueError("Private World Bank permissions differ")
        for table in ("norm_datasets", "catalog_release_grants"):
            if db.execute(
                f"SELECT 1 FROM {table} WHERE ai_allowed!=0 OR discovery_allowed!=0 LIMIT 1"
            ).fetchone():
                raise ValueError("Unexpected AI/Discovery permission")
        if db.execute(
            "SELECT 1 FROM catalog_scope_reviews WHERE scope IN ('ai','discovery') AND approved!=0 LIMIT 1"
        ).fetchone():
            raise ValueError("Unexpected AI/Discovery scope review")
    return {"public": len(current), "existing_43_preserved": True, "schema": 4}


def capacity(database):
    total = sum(
        p.stat().st_size
        for suffix in ("", "-wal", "-shm")
        if (p := Path(str(database) + suffix)).exists()
    )
    if total >= 384 * MIB or shutil.disk_usage(Path(database).parent).free < 150 * MIB:
        raise ValueError("Release disk headroom failed")
    cg = Path("/sys/fs/cgroup")
    if (cg / "memory.max").is_file() and (
        cg / "memory.max"
    ).read_text().strip() != "max":
        limit = int((cg / "memory.max").read_text())
        current = int((cg / "memory.current").read_text())
        stats = dict(
            line.split() for line in (cg / "memory.stat").read_text().splitlines()
        )
        if limit - (current - int(stats.get("inactive_file", 0))) < 128 * MIB:
            raise ValueError("Release working-memory headroom below 128 MiB")
    return total


def validate(database, directory):
    check(database)
    records, plan, pubs = bundle_index(directory), load_plan(), candidates()
    reader = NativeReader(Path(database))
    with reader.connection() as db:
        for key in plan["additional_ids"]:
            p, record = pubs[key], records[key]
            generation = db.execute(
                "SELECT g.* FROM norm_generations g JOIN norm_dataset_state s ON s.active_generation=g.id WHERE s.dataset_id=?",
                (key,),
            ).fetchone()
            reader._receipt(db, p.definition, generation)
            rows = db.execute(
                "SELECT period_key,value,payload FROM norm_observations WHERE dataset_id=? ORDER BY period_key",
                (key,),
            ).fetchall()
            source = json.loads(Path(record["snapshot_path"]).read_text())
            points = {
                native_period(r["period"], p.definition, r.get("event_id")).key: r
                for r in source["points"]
            }
            if len(rows) != len(points):
                raise ValueError("Incomplete private history")
            for row in rows:
                expected = points.get(row[0])
                payload = json.loads(row[2])
                if (
                    expected is None
                    or row[1] != expected["value"]
                    or payload["period_label"] != expected["label"]
                    or payload["flags"] != expected["flags"]
                ):
                    raise ValueError("Stored/source observations differ")
    return {"validated": 57, "rights_bound": True}


def stage(database, directory, *, max_datasets=5):
    check(database)
    capacity(database)
    if not 1 <= max_datasets <= 5:
        raise ValueError("Stage at most five datasets per invocation")
    records, pubs, plan = bundle_index(directory), candidates(), load_plan()
    reader, store = NativeReader(Path(database)), Store(database)
    current = public_ids(reader)
    results = []
    for key in plan["additional_ids"]:
        if key in current:
            continue  # Never overwrite a published/updated history with an old bundle.
        record = records[key]
        generation = (
            "release_" + digest({"id": key, "snapshot": record["snapshot_hash"]})[:48]
        )
        with store.connection() as db:
            completed = db.execute(
                "SELECT state FROM norm_generations WHERE id=?", (generation,)
            ).fetchone()
        if completed and completed[0] == "complete":
            continue
        capacity(database)
        result = ingest(
            store,
            pubs[key],
            record["snapshot_path"],
            record["snapshot_hash"],
            page_budget=16,
        )
        results.append(result)
        if result["state"] in {"failed", "busy"}:
            raise ValueError(
                "Stage deferred/failed; checkpoint retained; stop and inspect"
            )
        if len(results) >= max_datasets:
            break
    return {
        "results": results,
        "public": len(public_ids(reader)),
        "repeat_until_empty": bool(results),
    }


def publish(database, directory, *, approved=False):
    if not approved:
        raise ValueError("Separate explicit publication approval required")
    check(database)
    plan, pubs, reader = load_plan(), candidates(), NativeReader(Path(database))
    if len(public_ids(reader)) == 100:
        return {"public": 100, "state": "already_published"}
    validate(database, directory)
    capacity(database)
    with Store(database).connection(True) as db:
        for key in plan["additional_ids"]:
            activate(db, pubs[key], reader, approved=True)
    return {
        "public": len(public_ids(reader)),
        "published": 57,
        "ai": False,
        "discovery": False,
    }


def rollback(database, *, approved=False):
    if not approved:
        raise ValueError("Separate rollback approval required")
    check(database)
    with Store(database).connection(True) as db:
        for key in load_plan()["additional_ids"]:
            db.execute(
                "UPDATE catalog_release_grants SET public_display=0 WHERE dataset_id=?",
                (key,),
            )
            db.execute(
                "UPDATE catalog_scope_reviews SET approved=0 WHERE dataset_id=? AND scope='public_display'",
                (key,),
            )
    return {"public": len(public_ids(NativeReader(Path(database)))), "data_deleted": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=(
            "prepare",
            "check",
            "stage",
            "validate",
            "publish",
            "verify",
            "rollback",
        ),
    )
    parser.add_argument("--database", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--approve-publication", action="store_true")
    parser.add_argument("--approve-rollback", action="store_true")
    parser.add_argument("--approve-production", action="store_true")
    parser.add_argument("--expected-revision")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--backup-sha256")
    parser.add_argument("--off-render-backup-verified", action="store_true")
    parser.add_argument("--max-invocations", type=int, choices=range(1, 65), default=1)
    args = parser.parse_args()
    if args.operation == "prepare":
        if not args.bundle:
            parser.error("New off-Render bundle directory required")
        print(json.dumps(prepare(args.bundle)))
        return
    if not args.database:
        parser.error("Explicit existing database required")
    production = str(args.database.resolve()).startswith("/var/data/") or bool(
        os.getenv("RENDER_SERVICE_ID")
    )
    mutating = args.operation in {"stage", "publish", "rollback"}
    if production:
        if (
            str(args.database.resolve()) != "/var/data/macrolens-v2.sqlite3"
            or not args.expected_revision
            or os.getenv("RENDER_GIT_COMMIT") != args.expected_revision
        ):
            parser.error(
                "Exact production database/reviewed deployed revision required"
            )
        if mutating:
            if (
                not args.approve_production
                or not args.off_render_backup_verified
                or not args.backup
                or not re.fullmatch(r"[0-9a-f]{64}", args.backup_sha256 or "")
            ):
                parser.error(
                    "Separate production approval and verified independent backup required"
                )
            if (
                args.backup.samefile(args.database)
                or file_sha256(args.backup) != args.backup_sha256
                or Path(str(args.backup) + "-wal").exists()
                and Path(str(args.backup) + "-wal").stat().st_size != 0
            ):
                parser.error("Backup checksum/path failed")
            with closing(
                sqlite3.connect(
                    args.backup.resolve().as_uri() + "?mode=ro&immutable=1", uri=True
                )
            ) as backup:
                if backup.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    parser.error("Backup integrity failed")
    if args.operation in {"check", "verify"}:
        result = check(args.database, allow_refresh=args.operation == "verify")
        if args.operation == "verify" and result["public"] != 100:
            raise ValueError("Expected 100 public datasets")
    elif args.operation == "rollback":
        result = rollback(args.database, approved=args.approve_rollback)
    else:
        if not args.bundle:
            parser.error("Verified bundle required")
        if args.operation == "stage":
            for _ in range(args.max_invocations):
                result = stage(args.database, args.bundle)
                print(json.dumps(result), flush=True)
                if not result["results"]:
                    return
            if args.max_invocations > 1:
                raise SystemExit(
                    "Budget reached; rerun the same immutable bundle to resume"
                )
            return
        result = {
            "stage": stage,
            "validate": validate,
            "publish": lambda d, b: publish(d, b, approved=args.approve_publication),
        }[args.operation](args.database, args.bundle)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
