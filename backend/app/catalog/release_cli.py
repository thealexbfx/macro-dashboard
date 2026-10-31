"""Explicit release operations; never a server/scheduler startup dependency.

Each operation is separate. No environment-derived database paths, network access
or implicit migration/publication. Production use requires operator approval.
"""

import argparse
import json
from pathlib import Path

from backend.app.catalog.releases import activate, candidates, migrate
from backend.app.ingestion.native import digest, native_period
from backend.app.ingestion.official_snapshots import SnapshotAdapter
from backend.app.ingestion.partition_contracts import Bounds, windows
from backend.app.ingestion.partition_schema import migrate as native_migrate
from backend.app.ingestion.partitioned import PartitionedIngestion
from backend.app.v2.native_reader import NativeReader
from backend.app.v2.state import Store


def ingest(store, publication, snapshot_path, snapshot_hash):
    adapter = SnapshotAdapter(snapshot_path, snapshot_hash)
    # Verify complete snapshot and identity before registering or queuing a job.
    if Path(snapshot_path).stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Snapshot size check failed")
    body = Path(snapshot_path).read_bytes()
    from hashlib import sha256

    if len(body) > 16 * 1024 * 1024 or sha256(body).hexdigest() != snapshot_hash:
        raise ValueError("Snapshot integrity/size check failed")
    data = json.loads(body)
    d = publication.definition
    if (
        data["definition_hash"] != d.fingerprint
        or data["source_url"] != publication.source_url
    ):
        raise ValueError("Snapshot source differs from reviewed candidate")
    starts = [
        native_period(p["period"], d, p.get("event_id")).start for p in data["points"]
    ]
    engine = PartitionedIngestion(
        store,
        [d],
        {d.provider: adapter},
        bounds=Bounds(records=250),
        max_generation_rows=50000,
        compact_completed_staging=True,
        max_storage_bytes=384 * 1024 * 1024,
    )
    key = "release_" + digest({"id": d.id, "snapshot": snapshot_hash})[:48]
    with store.connection() as db:
        previous = db.execute(
            "SELECT state FROM norm_generations WHERE id=?", (key,)
        ).fetchone()
    if previous and previous[0] == "complete":
        return {"id": d.id, "state": "unchanged", "generation": key}
    engine.create_generation(
        d.id, windows(min(starts), max(starts), span_days=3660), generation_id=key
    )
    for _ in range(2048):
        result = engine.run_once()
        if result["state"] in {"failed", "busy"}:
            return {"id": d.id, "generation": key, **result}
        if result["state"] == "idle":
            with store.connection() as db:
                state = db.execute(
                    "SELECT state FROM norm_generations WHERE id=?", (key,)
                ).fetchone()[0]
            return {"id": d.id, "generation": key, "state": state}
    raise RuntimeError("Page budget exceeded; checkpoint retained")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument(
        "--operation",
        choices=("migrate", "ingest", "activate", "revoke"),
        required=True,
    )
    parser.add_argument("--ids", nargs="+", default=[])
    parser.add_argument("--source-index", type=Path)
    parser.add_argument("--approve-display", action="store_true")
    args = parser.parse_args()
    if not args.database.is_file() or len(args.ids) > 16:
        parser.error("Existing explicit database and at most 16 IDs required")
    store = Store(args.database)
    if args.operation == "migrate":
        with store.connection(True) as db:
            native_migrate(db)
            migrate(db)
        print(json.dumps({"schema": 3, "ingestion_enabled": False, "published": 0}))
        return
    publications = candidates()
    if not args.ids or any(k not in publications for k in args.ids):
        parser.error("Exact reviewed candidate IDs required")
    reader = NativeReader(store.path, publications)
    if args.operation == "ingest":
        if args.source_index is None:
            parser.error("A verified snapshot index is required")
        index = json.loads(args.source_index.read_text(encoding="utf-8"))
        failed = False
        for key in args.ids:
            record = index[key]
            result = ingest(
                store,
                publications[key],
                record["snapshot_path"],
                record["snapshot_hash"],
            )
            print(json.dumps(result), flush=True)
            failed |= result["state"] not in {"complete", "unchanged"}
        if failed:
            raise SystemExit(1)
    else:
        if args.operation == "activate" and not args.approve_display:
            parser.error("Separate explicit display approval is required")
        with store.connection(True) as db:
            for key in args.ids:
                if args.operation == "activate":
                    activate(db, publications[key], reader, approved=True)
                else:
                    db.execute(
                        "UPDATE catalog_release_grants SET public_display=0 WHERE dataset_id=?",
                        (key,),
                    )
                    db.execute(
                        "UPDATE catalog_scope_reviews SET approved=0 WHERE dataset_id=? AND scope='public_display'",
                        (key,),
                    )
        print(
            json.dumps(
                {
                    "operation": args.operation,
                    "datasets": args.ids,
                    "ai": False,
                    "discovery": False,
                }
            )
        )


if __name__ == "__main__":
    main()
