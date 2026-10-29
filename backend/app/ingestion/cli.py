"""Explicit local/operator CLI. No implicit production DB path, network, or public API."""

import argparse
import json
from pathlib import Path

from backend.app.ingestion.runner import Ingestion
from backend.app.ingestion.world_bank import WorldBank
from backend.app.v2.state import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        required=True,
        help="Explicit SQLite path; use a disposable local path for demonstrations",
    )
    parser.add_argument(
        "--backfill",
        action="store_true",
        help="Fetch and finish at most 12 bounded slices; never retries a failed job immediately",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="One explicit provider check (overrides next-due time)",
    )
    args = parser.parse_args()
    engine = Ingestion(Store(args.database), [WorldBank()])
    runs = []
    if args.backfill or args.update:
        for _ in range(12 if args.backfill else 1):
            result = engine.run_once(force=True)
            runs.append(result)
            if result["state"] != "backfilling":
                break
    status = engine.status()
    with engine.store.connection() as db:
        summary = []
        for spec in engine.adapters["world_bank"].series:
            rows = db.execute(
                "SELECT period,value,quality FROM ingest_observations WHERE dataset_id=? ORDER BY period",
                (spec.id,),
            ).fetchall()
            summary.append(
                {
                    "id": spec.id,
                    "stored": len(rows),
                    "missing": sum(r["value"] is None for r in rows),
                    "first": dict(rows[0]) if rows else None,
                    "last": dict(rows[-1]) if rows else None,
                }
            )
    print(
        json.dumps(
            {
                "database": str(args.database.resolve()),
                "runs": runs,
                "status": status,
                "series": summary,
            },
            indent=2,
        )
    )
    if any(r["state"] == "failed" for r in runs):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
