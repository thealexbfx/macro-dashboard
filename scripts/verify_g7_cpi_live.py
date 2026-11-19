"""Validate direct CPI refreshes in a new, disposable development workspace."""

import argparse
import json
import time
from pathlib import Path

from backend.app.ingestion.catalog_refresh import CatalogRefresh
from backend.app.ingestion.g7_cpi import configuration
from scripts.g7_cpi_refresh import open_workspace, report


def run_pass(store, sources, expected_state):
    worker = CatalogRefresh(store, private_sources=sources)
    remaining = set(sources[0])
    deadline = time.monotonic() + 420
    while remaining and time.monotonic() < deadline:
        result = worker.run_once()
        print(json.dumps(result), flush=True)
        state = result["state"]
        if state == "idle":
            time.sleep(10)
        elif state == expected_state and result["id"] in remaining:
            remaining.remove(result["id"])
        elif state != "checkpointed":
            raise ValueError(f"Unexpected refresh state: {state}")
    if remaining:
        raise TimeoutError("Not all six series completed before the deadline")


def evidence(store):
    with store.connection() as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        if db.execute("SELECT count(*) FROM catalog_release_grants").fetchone()[0]:
            raise ValueError("Unexpected display grants")
        generations = dict(db.execute("SELECT dataset_id, active_generation FROM norm_dataset_state"))
        rows = db.execute(
            """SELECT dataset_id, raw_hash, content_hash, last_success, provenance
               FROM catalog_refresh_jobs ORDER BY dataset_id"""
        )
        receipts = [dict(row) for row in rows]
    for receipt in receipts:
        provenance = json.loads(receipt["provenance"])
        for field in ("source_release", "source_checked_at", "resolved_source_url"):
            if not provenance.get(field):
                raise ValueError(f"Missing source provenance: {field}")
        receipt["provenance"] = provenance
    return generations, receipts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    args = parser.parse_args()
    store = open_workspace(args.workspace, initialize=True)
    sources = configuration()
    run_pass(store, sources, "changed")
    first = report(store)
    generations, first_receipts = evidence(store)
    if len(first) != 6 or len(first_receipts) != 6:
        raise ValueError("Expected six validated CPI histories")
    # Advance due times only inside this disposable database. Recreate the
    # worker so the second pass makes new HTTP requests using saved validators.
    with store.connection(True) as db:
        db.execute("UPDATE catalog_refresh_jobs SET next_due=0")
    run_pass(store, sources, "unchanged")
    second_generations, second_receipts = evidence(store)
    if generations != second_generations or first != report(store):
        raise ValueError("Unchanged pass altered the native history")
    print(json.dumps({
        "coverage": first,
        "initial_receipts": first_receipts,
        "unchanged_receipts": second_receipts,
        "new_release_verified": False,
    }))


if __name__ == "__main__":
    main()
