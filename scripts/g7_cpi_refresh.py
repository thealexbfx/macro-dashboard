"""Run the six-series CPI refresh in a dedicated development directory only."""

import argparse
import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from backend.app.catalog.releases import migrate as migrate_releases
from backend.app.ingestion.catalog_refresh import CatalogRefresh, migrate
from backend.app.ingestion.g7_cpi import configuration
from backend.app.ingestion.official_snapshots import download
from backend.app.ingestion.partition_schema import migrate as migrate_native
from backend.app.v2.state import Store

MARKER = "MacroLens private G7 CPI development workspace v1\n"


def open_workspace(path, initialize=False):
    root = Path(path).resolve()
    if initialize:
        root.mkdir()
        (root / ".g7-cpi-development").write_text(MARKER, encoding="utf-8")
    marker = root / ".g7-cpi-development"
    database = root / "g7-cpi-development.sqlite3"
    if marker.is_symlink() or not marker.is_file() or marker.read_text(encoding="utf-8") != MARKER:
        raise ValueError("A dedicated initialized G7 CPI workspace is required")
    if database.is_symlink() or (database.exists() and database.stat().st_nlink != 1):
        raise ValueError("The development database must not link to another file")
    store = Store(database)
    if initialize:
        with store.connection(True) as db:
            migrate_native(db)
            migrate_releases(db)
            migrate(db)
    return store


def report(store):
    with store.connection() as db:
        rows = db.execute("""
            SELECT dataset_id, count(*) AS periods, count(value) AS observations,
                   min(period_key) AS first_period, max(period_key) AS last_period,
                   min(CASE WHEN value IS NOT NULL THEN period_key END) AS first_observation
            FROM norm_observations GROUP BY dataset_id ORDER BY dataset_id
        """).fetchall()
        result = []
        for row in rows:
            key = row["dataset_id"]
            result.append(dict(row) | {
                "missing": [p[0] for p in db.execute(
                    "SELECT period_key FROM norm_observations WHERE dataset_id=? AND value IS NULL ORDER BY period_key",
                    (key,))],
                "revisions": db.execute("SELECT count(*) FROM norm_revisions WHERE dataset_id=?", (key,)).fetchone()[0],
                "latest": db.execute("SELECT value FROM norm_observations WHERE dataset_id=? ORDER BY period_key DESC LIMIT 1", (key,)).fetchone()[0],
            })
        return result


def observation_state(store, key):
    with store.connection() as db:
        rows = db.execute(
            """SELECT period_key, payload, value, revision, artifact_hash
               FROM norm_observations WHERE dataset_id=? ORDER BY period_key""",
            (key,),
        ).fetchall()
        revisions = db.execute(
            "SELECT count(*) FROM norm_revisions WHERE dataset_id=?", (key,)
        ).fetchone()[0]
    digest = sha256(json.dumps([tuple(row) for row in rows]).encode()).hexdigest()
    return {"periods": len(rows), "revisions": revisions, "observation_hash": digest}


def run_series(worker, key, phase):
    for _ in range(16):
        result = worker.run_once()
        print(json.dumps(result | {"audit_dataset_id": key, "phase": phase}), flush=True)
        if result["state"] != "checkpointed":
            break
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument(
        "--all-series-once", action="store_true",
        help="Stage each publisher series independently and immediately in this disposable workspace",
    )
    parser.add_argument(
        "--verify-repeat", action="store_true",
        help="Recheck all six sources in the same isolated workspace after advancing the audit clock",
    )
    args = parser.parse_args()
    if args.verify_repeat and not args.all_series_once:
        parser.error("--verify-repeat requires --all-series-once")
    store = open_workspace(args.workspace, args.initialize)
    sources = configuration()
    failures = False
    if args.all_series_once:
        # Each scoped worker registers only its own series, avoiding the
        # normal cross-series 60-second stagger while keeping network reads
        # sequential, bounded, and strictly development-only.
        rules, publications, entries = sources
        for key in sorted(rules):
            scoped = ({key: rules[key]}, {key: publications[key]}, {key: entries[key]})
            clock_offset = timedelta()
            worker = CatalogRefresh(
                store, private_sources=scoped, fetch=download,
                now=lambda: datetime.now(UTC) + clock_offset,
            )
            result = run_series(worker, key, "initial")
            if result["state"] not in {"changed", "unchanged"}:
                failures = True
                continue
            if not args.verify_repeat:
                continue
            before = observation_state(store, key)
            clock_offset = timedelta(seconds=max(0, result["next_due"] - datetime.now(UTC).timestamp()) + 1)
            repeated = run_series(worker, key, "repeat")
            after = observation_state(store, key)
            stable = before == after
            valid = (
                repeated["state"] == "unchanged" and stable
                or repeated["state"] == "changed" and not stable
            )
            print(json.dumps({
                "dataset_id": key, "repeat_state": repeated["state"],
                "before": before, "after": after, "repeat_consistent": valid,
            }), flush=True)
            failures = failures or not valid
    else:
        worker = CatalogRefresh(store, private_sources=sources, fetch=download)
        for _ in range(16):
            result = worker.run_once()
            print(json.dumps(result))
            if result["state"] in {"idle", "busy"}:
                break
        failures = any(job["failures"] for job in worker.status())
    summary = report(store)
    print(json.dumps(summary, indent=2), flush=True)
    if args.all_series_once:
        print(json.dumps({
            "series_expected": len(sources[0]),
            "series_staged": len(summary),
            "observations_staged": sum(row["observations"] for row in summary),
            "explicit_publisher_nulls": sum(len(row["missing"]) for row in summary),
            "production_approved": False,
            "commercial_rights": "PENDING",
        }), flush=True)
        failures = failures or len(summary) != len(sources[0])
    return int(failures)


if __name__ == "__main__":
    raise SystemExit(main())
