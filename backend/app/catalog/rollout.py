"""Configuration-driven, resumable catalog release. No deployment/startup hooks.

Capture off Render; apply only explicitly reviewed IDs and frozen observations.
Schema changes, public display and scheduler activation remain separate approvals.
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from backend.app.catalog.release100 import capacity, file_sha256, public_ids
from backend.app.catalog.release_cli import ingest
from backend.app.catalog.releases import activate, candidates
from backend.app.ingestion.catalog_refresh import CatalogRefresh, CONFIG, ROOT
from backend.app.ingestion.native import digest, native_period
from backend.app.v2.native_reader import NativeReader
from backend.app.v2.state import Store

PLAN = ROOT / "catalog/publication_plan.json"
PRIVATE = {"wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly"}


def load_plan(path=PLAN):
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    pubs = candidates()
    rules = {r["id"]: r for r in json.loads(CONFIG.read_text())["datasets"]}
    baseline = plan["baseline_ids"]
    rows = plan["datasets"]
    ids = [r["id"] for r in rows]
    if (
        plan["version"] != 1
        or len(set(baseline)) != len(baseline)
        or len(ids) != len(set(ids))
        or set(ids) & (set(baseline) | PRIVATE)
        or len(baseline) + len(ids) > 400
    ):
        raise ValueError("Invalid reviewed release identities")
    for row in rows:
        key = row["id"]
        pub, rule = pubs[key], rules[key]
        if (
            row["definition_hash"] != pub.definition.fingerprint
            or row["source_url"] != pub.source_url
            or row["rights_evidence"] != pub.rights_evidence
            or row["publication_approved"] is not True
            or not row["rights_review"]["basis"]
            or not row["rights_review"]["url"].startswith("https://")
            or not rule["automation_ready"]
            or not rule["ingest_approved"]
            or rule["mode"] != "refresh"
            or row["ai_allowed"] is not False
            or row["discovery_allowed"] is not False
        ):
            raise ValueError("Missing definition, source, rights or refresh approval")
    return plan


def check(database, plan, *, require_paused=True, schema_required=5):
    path = Path(database)
    if not path.is_file():
        raise ValueError("Existing database required")
    if (
        os.getenv("MACROLENS_INGESTION_ENABLED", "0") == "1"
        or os.getenv("MACROLENS_AI_ENABLED", "false").casefold()
        not in {"false", "0", ""}
        or require_paused
        and os.getenv("MACROLENS_CATALOG_REFRESH_ENABLED", "0") == "1"
    ):
        raise ValueError(
            "Pause catalog refresh for mutations; World Bank and AI remain disabled"
        )
    baseline = set(plan["baseline_ids"])
    public = public_ids(NativeReader(path))
    if not baseline <= public <= baseline | {r["id"] for r in plan["datasets"]}:
        raise ValueError("Unexpected public baseline; never revoke unrelated grants")
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Database integrity failed")
        if not db.execute(
            "SELECT 1 FROM catalog_schema_versions WHERE version=?", (schema_required,)
        ).fetchone():
            raise ValueError("Explicit additive schema 5 migration required")
        for key in PRIVATE:
            if db.execute(
                "SELECT public_display,ai_allowed,rights_state FROM ingest_datasets WHERE id=?",
                (key,),
            ).fetchone() != (0, 0, "unreviewed"):
                raise ValueError("Private World Bank baseline differs")
        for table in ("norm_datasets", "catalog_release_grants"):
            if db.execute(
                f"SELECT 1 FROM {table} WHERE ai_allowed!=0 OR discovery_allowed!=0 LIMIT 1"
            ).fetchone():
                raise ValueError("Unexpected AI/Discovery grants")
        if db.execute(
            "SELECT 1 FROM catalog_scope_reviews WHERE scope IN ('ai','discovery') AND approved!=0 LIMIT 1"
        ).fetchone():
            raise ValueError("Unexpected AI/Discovery reviews")
    return {
        "public": len(public),
        "baseline_preserved": True,
        "schema": schema_required,
    }


def bundle(directory, plan):
    root = Path(directory).resolve()
    if (
        Path(directory).is_symlink()
        or (root / "manifest.json").is_symlink()
        or (root / "snapshots").is_symlink()
    ):
        raise ValueError("Symlink bundle forbidden")
    data = json.loads((root / "manifest.json").read_text())
    age = (
        datetime.now(UTC) - datetime.fromisoformat(data["created_at"])
    ).total_seconds()
    if (
        not 0 <= age <= 7 * 86400
        or data["plan_sha256"] != digest(plan)
        or set(data["datasets"]) != {r["id"] for r in plan["datasets"]}
    ):
        raise ValueError("Stale or mismatched frozen plan")
    pubs = candidates()
    total = 0
    for key, record in data["datasets"].items():
        if not re.fullmatch("[0-9a-f]{64}", record["snapshot_hash"]):
            raise ValueError("Invalid source hash")
        path = root / "snapshots" / (record["snapshot_hash"] + ".json")
        total += record["bytes"]
        if (
            path.is_symlink()
            or path.stat().st_size != record["bytes"]
            or record["bytes"] > 16 * 1024**2
            or file_sha256(path) != record["snapshot_hash"]
        ):
            raise ValueError("Frozen file integrity failed")
        frozen = json.loads(path.read_text())
        if (
            frozen["definition_hash"] != pubs[key].definition.fingerprint
            or frozen["source_url"] != pubs[key].source_url
            or len(frozen["points"]) != record["rows"]
            or not 0 < record["rows"] <= 50000
        ):
            raise ValueError("Frozen definition/coverage differs")
        record["path"] = path
    if total > 96 * 1024**2:
        raise ValueError("Frozen input budget exceeded")
    return data["datasets"]


def prepare(directory, plan):
    if os.getenv("RENDER_SERVICE_ID") or str(Path(directory).resolve()).startswith(
        "/var/data"
    ):
        raise ValueError("Off-Render capture only")
    root = Path(directory)
    root.mkdir(exist_ok=False, parents=True)
    (root / "snapshots").mkdir()
    from backend.app.ingestion.partition_schema import migrate as native
    from backend.app.catalog.releases import migrate as releases
    from backend.app.ingestion.catalog_refresh import migrate as refresh
    from backend.app.ingestion.provider_requests import migrate as requests

    records, errors = {}, []
    with tempfile.TemporaryDirectory(prefix="catalog-capture-") as scratch:
        store = Store(Path(scratch) / "disposable.sqlite3")
        with store.connection(True) as db:
            native(db)
            releases(db)
            refresh(db)
            requests(db)
        config = Path(scratch) / "policy.json"
        wanted = {r["id"] for r in plan["datasets"]}
        rules = [
            r | {"mode": "stage"}
            for r in json.loads(CONFIG.read_text())["datasets"]
            if r["id"] in wanted
        ]
        config.write_text(json.dumps({"datasets": rules}))
        engine = CatalogRefresh(store, config=config)
        from backend.app.ingestion.catalog_refresh import endpoint

        ordered = sorted(wanted, key=lambda k: endpoint(engine.entries[k]))
        for key in ordered:
            try:
                pending, _ = engine._download(
                    key,
                    {
                        "content_hash": None,
                        "raw_hash": None,
                        "etag": None,
                        "last_modified": None,
                    },
                )
                source = Path(pending["path"])
                frozen = json.loads(source.read_text())
                shutil.copyfile(source, root / "snapshots" / source.name)
                records[key] = {
                    "snapshot_hash": pending["snapshot"],
                    "bytes": source.stat().st_size,
                    "rows": len(frozen["points"]),
                }
                source.unlink()
                print(
                    json.dumps(
                        {"id": key, "state": "captured", "rows": records[key]["rows"]}
                    ),
                    flush=True,
                )
            except (
                Exception
            ) as exc:  # independent capture; no publishable manifest on partial failure
                errors.append(
                    {
                        "id": key,
                        "code": getattr(exc, "code", "source_validation_failed"),
                    }
                )
                print(json.dumps(errors[-1]), flush=True)
    (root / "capture-results.json").write_text(
        json.dumps({"datasets": records, "errors": errors}, indent=2)
    )
    if errors:
        raise ValueError(
            "Incomplete capture; fix source or explicitly review a smaller plan"
        )
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "plan_sha256": digest(plan),
                "datasets": records,
            },
            indent=2,
        )
    )
    return {
        "captured": len(records),
        "observations": sum(r["rows"] for r in records.values()),
    }


def validate(database, directory, plan):
    records, pubs = bundle(directory, plan), candidates()
    reader = NativeReader(Path(database))
    with reader.connection() as db:
        for key, record in records.items():
            generation = db.execute(
                "SELECT g.* FROM norm_dataset_state s JOIN norm_generations g ON g.id=s.active_generation WHERE s.dataset_id=?",
                (key,),
            ).fetchone()
            reader._receipt(db, pubs[key].definition, generation)
            frozen = json.loads(record["path"].read_text())
            expected = {
                native_period(
                    p["period"], pubs[key].definition, p.get("event_id")
                ).key: p
                for p in frozen["points"]
            }
            rows = db.execute(
                "SELECT period_key,value,payload FROM norm_observations WHERE dataset_id=?",
                (key,),
            )
            count = 0
            for row in rows:
                point = expected.get(row[0])
                payload = json.loads(row[2])
                if (
                    point is None
                    or point["value"] != row[1]
                    or point["label"] != payload["period_label"]
                    or point["flags"] != payload["flags"]
                ):
                    raise ValueError("Stored history differs from frozen inputs")
                count += 1
            if count != len(expected):
                raise ValueError("Incomplete staged history")
    return {"validated": len(records)}


def stage(database, directory, plan, *, budget=5):
    if not 1 <= budget <= 5:
        raise ValueError("Five sequential dataset maximum")
    check(database, plan)
    capacity(database)
    records, pubs = bundle(directory, plan), candidates()
    store = Store(database)
    public = public_ids(NativeReader(Path(database)))
    result = []
    for key, record in sorted(records.items()):
        if key in public:
            continue
        generation = (
            "release_" + digest({"id": key, "snapshot": record["snapshot_hash"]})[:48]
        )
        with store.connection() as db:
            old = db.execute(
                "SELECT state FROM norm_generations WHERE id=?", (generation,)
            ).fetchone()
        if old and old[0] == "complete":
            continue
        capacity(database)
        state = ingest(
            store, pubs[key], record["path"], record["snapshot_hash"], page_budget=16
        )
        result.append(state)
        if state["state"] in {"failed", "busy"}:
            raise ValueError("Stage deferred; durable checkpoints retained")
        if len(result) >= budget:
            break
    return {"results": result, "complete": not result}


def publish(database, directory, plan, *, approved=False):
    if approved is not True:
        raise ValueError("Explicit publication approval required")
    check(database, plan)
    capacity(database)
    current = public_ids(NativeReader(Path(database)))
    wanted = {r["id"] for r in plan["datasets"]}
    if current == set(plan["baseline_ids"]) | wanted:
        return {"public": len(current), "state": "already_published"}
    validate(database, directory, plan)
    pubs, reader = candidates(), NativeReader(Path(database))
    with Store(database).connection(True) as db:
        for key in sorted(wanted):
            activate(db, pubs[key], reader, approved=True)
    return {
        "public": len(public_ids(NativeReader(Path(database)))),
        "published": len(wanted),
        "ai": False,
        "discovery": False,
    }


def rollback(database, plan, *, approved=False):
    if approved is not True:
        raise ValueError("Explicit rollback approval required")
    check(database, plan)
    with Store(database).connection(True) as db:
        for row in plan["datasets"]:
            db.execute(
                "UPDATE catalog_release_grants SET public_display=0 WHERE dataset_id=?",
                (row["id"],),
            )
            db.execute(
                "UPDATE catalog_scope_reviews SET approved=0 WHERE dataset_id=? AND scope='public_display'",
                (row["id"],),
            )
    return {
        "public": len(public_ids(NativeReader(Path(database)))),
        "deleted_observations": 0,
    }


def verify_backup(path, expected):
    if Path(str(path) + "-wal").exists() and Path(str(path) + "-wal").stat().st_size:
        raise ValueError("Consistent standalone backup required; WAL present")
    if file_sha256(path) != expected:
        raise ValueError("Backup checksum failed")
    with closing(
        sqlite3.connect(
            Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True
        )
    ) as source:
        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Backup integrity failed")
        with tempfile.TemporaryDirectory(prefix="catalog-restore-") as root:
            with closing(sqlite3.connect(Path(root) / "restored.sqlite3")) as restored:
                source.backup(restored)
                if restored.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Disposable restore failed")
    return {"sha256": expected, "integrity": "ok", "disposable_restore": "ok"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=(
            "prepare",
            "check",
            "migrate",
            "stage",
            "validate",
            "publish",
            "apply",
            "verify",
            "rollback",
            "verify-backup",
        ),
    )
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--expected-revision")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--backup-sha256")
    parser.add_argument("--off-render-backup-verified", action="store_true")
    parser.add_argument("--approve-production", action="store_true")
    parser.add_argument("--approve-publication", action="store_true")
    parser.add_argument("--approve-migration", action="store_true")
    parser.add_argument("--approve-rollback", action="store_true")
    parser.add_argument(
        "--max-invocations", type=int, choices=range(1, 129), default=64
    )
    args = parser.parse_args()
    if args.operation == "apply" and not args.approve_publication:
        parser.error("Explicit reviewed publication approval required for apply")
    if args.operation == "verify-backup":
        print(json.dumps(verify_backup(args.backup, args.backup_sha256)))
        return
    plan = load_plan(args.plan)
    if args.operation == "prepare":
        if not args.bundle:
            parser.error("New bundle directory required")
        print(json.dumps(prepare(args.bundle, plan)))
        return
    if not args.database or not args.database.is_file():
        parser.error("Existing explicit database required")
    production = bool(os.getenv("RENDER_SERVICE_ID")) or str(
        args.database.resolve()
    ).startswith("/var/data/")
    mutating = args.operation in {"migrate", "stage", "publish", "apply", "rollback"}
    if production:
        if (
            str(args.database.resolve()) != "/var/data/macrolens-v2.sqlite3"
            or not args.expected_revision
            or args.expected_revision != os.getenv("RENDER_GIT_COMMIT")
        ):
            parser.error("Exact approved deployed revision/database required")
        if mutating:
            if (
                not args.approve_production
                or not args.off_render_backup_verified
                or not args.backup
                or args.backup.samefile(args.database)
                or Path(str(args.backup) + "-wal").exists()
                and Path(str(args.backup) + "-wal").stat().st_size
            ):
                parser.error(
                    "Production approval and independent consistent backup required"
                )
            verify_backup(args.backup, args.backup_sha256)
            if not set(plan["baseline_ids"]) <= public_ids(NativeReader(args.backup)):
                raise ValueError("Backup predates the current public baseline")
            with (
                closing(
                    sqlite3.connect(
                        args.backup.resolve().as_uri() + "?mode=ro&immutable=1",
                        uri=True,
                    )
                ) as backup,
                closing(
                    sqlite3.connect(
                        args.database.resolve().as_uri() + "?mode=ro", uri=True
                    )
                ) as live,
            ):
                # Research changed after backup? Stop and take a fresh independent backup.
                if digest(
                    backup.execute("SELECT * FROM library ORDER BY id").fetchall()
                ) != digest(
                    live.execute("SELECT * FROM library ORDER BY id").fetchall()
                ):
                    raise ValueError(
                        "Research changed since backup; renew independent backup"
                    )
    if (
        args.operation == "migrate"
        or args.operation == "apply"
        and args.approve_migration
    ):
        if not args.approve_migration:
            parser.error("Explicit additive migration approval required")
        if os.getenv("MACROLENS_CATALOG_REFRESH_ENABLED", "0") == "1":
            parser.error("Pause refresh before migration")
        from backend.app.ingestion.provider_requests import migrate

        check(args.database, plan, schema_required=4)
        capacity(args.database)
        with Store(args.database).connection(True) as db:
            migrate(db)
        result = {"schema": 5, "publications_changed": 0}
        if args.operation == "migrate":
            print(json.dumps(result), flush=True)
            return
    if args.operation in {"check", "verify"}:
        result = check(args.database, plan, require_paused=args.operation == "check")
        if args.operation == "verify" and result["public"] != len(
            plan["baseline_ids"]
        ) + len(plan["datasets"]):
            raise ValueError("Incomplete public release")
    elif args.operation == "rollback":
        result = rollback(args.database, plan, approved=args.approve_rollback)
    elif args.operation in {"stage", "apply"}:
        if args.operation == "apply" and not args.approve_publication:
            parser.error("Explicit reviewed publication approval required for apply")
        for _ in range(args.max_invocations):
            result = stage(args.database, args.bundle, plan)
            print(json.dumps(result), flush=True)
            if args.operation == "stage" and args.max_invocations == 1:
                return
            if result["complete"]:
                break
        else:
            if args.max_invocations == 1 and args.operation == "stage":
                return  # One bounded checkpoint, not a false completeness claim.
            raise SystemExit("Budget reached; rerun identical inputs to resume")
        result = (
            publish(args.database, args.bundle, plan, approved=True)
            if args.operation == "apply"
            else validate(args.database, args.bundle, plan)
        )
    elif args.operation == "validate":
        result = validate(args.database, args.bundle, plan)
    else:
        result = publish(
            args.database, args.bundle, plan, approved=args.approve_publication
        )
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
