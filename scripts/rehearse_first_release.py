"""Restore a local backup and rehearse the first batch on a NEW disposable copy.

Never reads Render, never writes the supplied backup, never prints private rows.
"""

import argparse
import hashlib
import json
import os
import sqlite3
import time
from pathlib import Path

from backend.app.catalog.release_cli import ingest
from backend.app.catalog.releases import activate, candidates, migrate
from backend.app.ingestion.native import native_period
from backend.app.ingestion.partition_schema import migrate as native_migrate
from backend.app.v2.native_reader import NativeReader
from backend.app.v2.state import Store
from scripts.smoke_first_release import SELECTION, checks


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprints(db, names):
    result = {}
    for table in names:
        quoted = '"' + table.replace('"', '""') + '"'
        digest = hashlib.sha256()
        # Ordering all columns also works for WITHOUT ROWID tables; values stay local.
        columns = [r[1] for r in db.execute(f"PRAGMA table_info({quoted})")]
        order = ",".join('"' + c.replace('"', '""') + '"' for c in columns)
        rows = db.execute(f"SELECT * FROM {quoted} ORDER BY {order}")
        for row in rows:
            digest.update(
                json.dumps(
                    tuple(row), default=lambda b: b.hex(), ensure_ascii=True
                ).encode()
            )
            digest.update(b"\n")
        result[table] = digest.hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--source-index", type=Path, required=True)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    source, workspace = args.backup.resolve(), args.workspace.resolve()
    if any(str(p).startswith(("/var/", "/mnt/")) for p in (source, workspace)):
        parser.error("Local backup and disposable workspace only")
    if not source.is_file() or source.stat().st_size > 128 * 1024 * 1024:
        parser.error("Existing local SQLite backup within rehearsal budget required")
    if any(Path(str(source) + suffix).exists() for suffix in ("-wal", "-journal")):
        parser.error(
            "A consistent standalone backup without pending journal files is required"
        )
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / "disposable-first-live.sqlite3"
    if target.exists() or source == target:
        parser.error("Refusing to overwrite a database; use a fresh workspace")
    original_sha = file_hash(source)
    if args.expected_sha256 and original_sha != args.expected_sha256.lower():
        parser.error("Backup SHA-256 differs from supplied trusted receipt")
    with sqlite3.connect(source.as_uri() + "?mode=ro&immutable=1", uri=True) as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        names = [
            r[0]
            for r in backup.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        ]
        before = fingerprints(backup, names)
        with sqlite3.connect(target) as restored:
            backup.backup(restored)
            assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert fingerprints(restored, names) == before
    os.environ.update(
        MACROLENS_V2_STATE_DB=str(target),
        MACROLENS_AI_ENABLED="false",
        MACROLENS_INGESTION_ENABLED="0",
    )
    store = Store(target)
    with store.connection(True) as db:
        native_migrate(db)
        migrate(db)
    selected = json.loads(SELECTION.read_text(encoding="utf-8"))["ids"]
    registry = candidates()
    reader = NativeReader(target, registry)
    index = json.loads(args.source_index.read_text(encoding="utf-8"))
    keeper = sqlite3.connect(target)
    keeper.execute("PRAGMA journal_mode=WAL")
    sizes = lambda: {
        s or "database": Path(str(target) + s).stat().st_size
        if Path(str(target) + s).exists()
        else 0
        for s in ("", "-wal", "-shm")
    }
    initial = sizes()
    peak = sum(initial.values())
    started = time.perf_counter()
    states = []
    for key in selected:
        row = index[key]
        assert row["state"] == "captured"
        result = ingest(
            store, registry[key], row["snapshot_path"], row["snapshot_hash"]
        )
        assert result["state"] == "complete", result
        states.append(result["state"])
        peak = max(peak, sum(sizes().values()))
    from fastapi.testclient import TestClient

    from backend.app.v2 import main as app
    from backend.app.v2.catalog_api import PublicCatalog

    app.public_catalog = PublicCatalog(app.legacy_service, app.service.reader, reader)
    client = TestClient(app.app)  # No lifespan startup or background scheduler.

    def request(method, path, body=None):
        response = (
            client.request(method, path, json=body)
            if body is not None
            else client.request(method, path)
        )
        return response.status_code, response.json()

    private_checks = checks(request, activated=False)
    with store.connection(True) as db:
        for key in selected:
            activate(db, registry[key], reader, approved=True)  # Disposable copy only.
    public_checks = checks(request, activated=True)
    with store.connection() as db:
        assert fingerprints(db, names) == before
        for key in selected:
            snapshot = json.loads(
                Path(index[key]["snapshot_path"]).read_text(encoding="utf-8")
            )
            points = [p for p in snapshot["points"] if p["value"] is not None]
            assert points
            for point in (points[0], points[len(points) // 2], points[-1]):
                period = native_period(
                    point["period"], registry[key].definition, point.get("event_id")
                )
                value = db.execute(
                    "SELECT value FROM norm_observations WHERE dataset_id=? AND period_key=?",
                    (key, period.key),
                ).fetchone()[0]
                assert value == point["value"]
        assert (
            db.execute(
                "SELECT count(*) FROM norm_datasets WHERE ai_allowed!=0 OR discovery_allowed!=0"
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                "SELECT count(*) FROM catalog_scope_reviews WHERE scope IN ('ai','discovery') AND approved=1"
            ).fetchone()[0]
            == 0
        )
        new_rows = db.execute("SELECT count(*) FROM norm_observations").fetchone()[0]
        assert new_rows == sum(index[k]["observations"] for k in selected)
        assert (
            db.execute(
                "SELECT count(*) FROM ingest_observations WHERE dataset_id LIKE 'wb_%'"
            ).fetchone()[0]
            == 2403
        )
        assert (
            db.execute(
                "SELECT count(*) FROM ingest_datasets WHERE id LIKE 'wb_%' AND (public_display!=0 OR ai_allowed!=0 OR rights_state!='unreviewed')"
            ).fetchone()[0]
            == 0
        )
    for key in selected:
        row = index[key]
        assert (
            ingest(store, registry[key], row["snapshot_path"], row["snapshot_hash"])[
                "state"
            ]
            == "unchanged"
        )
    with store.connection(True) as db:
        db.execute("UPDATE catalog_release_grants SET public_display=0")
        db.execute(
            "UPDATE catalog_scope_reviews SET approved=0 WHERE scope='public_display'"
        )
    rollback_checks = checks(request, activated=False)
    final = sizes()
    with (
        store.connection() as db,
        sqlite3.connect(
            workspace / "disposable-post-release-restore.sqlite3"
        ) as restored,
    ):
        db.backup(restored)
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert fingerprints(restored, names) == before
        assert (
            restored.execute("SELECT count(*) FROM norm_observations").fetchone()[0]
            == new_rows
        )
    assert file_hash(source) == original_sha
    receipt = {
        "local_backup": source.name,
        "backup_sha256": original_sha,
        "trusted_origin_hash_supplied": bool(args.expected_sha256),
        "freshness_against_live_db_verified": False,
        "backup_integrity": "ok",
        "restore_integrity": "ok",
        "original_tables_unchanged": True,
        "first_middle_last_nonnull_source_samples": "matched",
        "world_bank_rows_preserved": 2403,
        "datasets": len(selected),
        "new_observations": new_rows,
        "seconds": time.perf_counter() - started,
        "initial_storage": initial,
        "final_storage": final,
        "sampled_peak_database_wal_shm_bytes": peak,
        "pre_activation": private_checks,
        "post_activation": public_checks,
        "post_revoke": rollback_checks,
        "same_snapshot_rerun": "unchanged",
        "production_changed": False,
    }
    (workspace / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt))
    client.close()
    keeper.close()


if __name__ == "__main__":
    main()
