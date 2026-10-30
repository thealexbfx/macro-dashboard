"""Offline resource/restore probe. Only internally created temporary databases.

All 2,403 commodity rows and saved research here are synthetic. No database path
argument, provider, ingestion runner, application lifespan or external IO exists.
"""

import json
import sqlite3
import sys
import tempfile
import time
from contextlib import closing
from hashlib import sha256
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backend.app.catalog.manifest import Manifest
from backend.app.catalog.schema import migrate
from backend.app.ingestion.schema import SCHEMA as INGESTION_SCHEMA
from backend.app.v2.state import SCHEMA

TABLES = (
    "source_cache",
    "leases",
    "stories",
    "story_versions",
    "library",
    "reports",
    "ai_requests",
    "ai_cache",
    "counters",
    "pricing",
    "ingest_datasets",
    "ingest_jobs",
    "ingest_runs",
    "ingest_observations",
    "ingest_revisions",
)


def snapshot(db):
    return {
        table: sha256(
            json.dumps(
                sorted(
                    (tuple(row) for row in db.execute("SELECT * FROM " + table)),
                    key=repr,
                ),
                sort_keys=True,
            ).encode()
        ).hexdigest()
        for table in TABLES
    }


def seed(db):
    db.executescript(SCHEMA + INGESTION_SCHEMA)
    db.execute(
        "INSERT INTO library VALUES(?,?,?,?,?)",
        (
            "fixture_saved_research",
            "SYNTHETIC saved investigation",
            "2026-10-30",
            '{"datasets":["cpi","unemployment"],"fixture":true}',
            "Synthetic note",
        ),
    )
    for key in ("wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly"):
        db.execute(
            "INSERT INTO ingest_datasets(id,provider,metadata,updated_at) VALUES(?,?,?,?)",
            (key, "world_bank", '{"fixture":true}', "2026-10-30"),
        )
        db.executemany(
            "INSERT INTO ingest_observations VALUES(?,?,?,?,?,?,?,?)",
            (
                (
                    key,
                    f"{1960 + n // 12:04d}-{n % 12 + 1:02d}",
                    42 + n * 0.1,
                    "unit_review" if key == "wb_iron_ore_monthly" else "observed",
                    1,
                    "2026-10-30",
                    "2026-10-30",
                    "fixture_run",
                )
                for n in range(801)
            ),
        )
    db.execute(
        "INSERT INTO ingest_jobs(provider,source_hash) VALUES(?,?)",
        ("world_bank", "a" * 64),
    )
    db.execute(
        "INSERT INTO ingest_revisions VALUES(?,?,?,?,?,?,?)",
        (
            "wb_copper_monthly",
            "1960-01",
            1,
            41,
            "observed",
            "2026-10-30",
            "fixture_run",
        ),
    )
    db.commit()


def run():
    started = time.perf_counter()
    manifest = Manifest.load()
    assert manifest.page(audience="planning")["total"] == 309
    assert manifest.page()["total"] == 30
    with tempfile.TemporaryDirectory(prefix="macrolens-batch0-") as directory:
        original = Path(directory) / "synthetic.sqlite3"
        restored = Path(directory) / "restored.sqlite3"
        with closing(sqlite3.connect(original)) as db:
            seed(db)
            before = snapshot(db)
        with (
            closing(sqlite3.connect(original)) as source,
            closing(sqlite3.connect(restored)) as target,
        ):
            source.backup(target)
        baseline_bytes = restored.stat().st_size
        with closing(sqlite3.connect(restored)) as db:
            migrate(db)
            migrate(db)
            assert snapshot(db) == before
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert (
                db.execute("SELECT count(*) FROM catalog_scope_reviews").fetchone()[0]
                == 0
            )
            assert (
                db.execute(
                    "SELECT count(*) FROM catalog_dataset_completeness"
                ).fetchone()[0]
                == 0
            )
        result = {
            "fixture": "synthetic only; no production data",
            "manifest_entries": 309,
            "public_metadata_entries": 30,
            "preserved_observations": 2403,
            "baseline_database_bytes": baseline_bytes,
            "migrated_database_bytes": restored.stat().st_size,
            "migration_growth_bytes": restored.stat().st_size - baseline_bytes,
            "elapsed_seconds": round(time.perf_counter() - started, 4),
            "linux_peak_rss_mib": None,
        }
    if sys.platform == "linux":
        import resource

        result["linux_peak_rss_mib"] = round(
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 3
        )
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run()
