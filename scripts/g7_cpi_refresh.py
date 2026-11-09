"""Run the six-series CPI refresh in a dedicated development directory only."""

import argparse
import json
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--initialize", action="store_true")
    args = parser.parse_args()
    store = open_workspace(args.workspace, args.initialize)
    worker = CatalogRefresh(store, private_sources=configuration(), fetch=download)
    for _ in range(16):
        result = worker.run_once()
        print(json.dumps(result))
        if result["state"] in {"idle", "busy"}:
            break
    print(json.dumps(report(store), indent=2))
    return int(any(job["failures"] for job in worker.status()))


if __name__ == "__main__":
    raise SystemExit(main())
