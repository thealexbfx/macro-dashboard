"""Local-only readiness benchmark. Originals are opened read-only; never reset a DB."""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from backend.app.v2.main import DataService, Dataset, transform
from backend.app.v2.refresh import scheduled_service_class
from backend.app.v2.runtime import DynamicDiscovery
from backend.app.v2.state import Store


class OfflineProvider:
    def fred_series(self, *_):
        raise AssertionError("Benchmark must not contact providers")

    def market_series(self, *_):
        raise AssertionError("Benchmark must not contact providers")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--database", required=True)
    p.add_argument("--source-db")
    p.add_argument("--output", required=True)
    p.add_argument("--label", required=True)
    a = p.parse_args()
    target = Path(a.database).resolve()
    if a.source_db:
        if target.exists():
            raise FileExistsError(
                "Refusing to overwrite an existing benchmark database"
            )
        source = Path(a.source_db).resolve()
        if source == target:
            raise ValueError("Benchmark destination must differ from source")
        with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True) as db:
            rows = db.execute(
                "SELECT id,payload,checked_at,failures FROM source_cache"
            ).fetchall()
        if not rows:
            raise ValueError("Source cache is empty")
        now = datetime.now(UTC)
        store = Store(target)
        with store.connection(True) as db:
            db.execute("CREATE TABLE benchmark_metadata(clock TEXT)")
            db.execute("INSERT INTO benchmark_metadata VALUES (?)", (now.isoformat(),))
            for key, payload, checked, failures in rows:
                db.execute(
                    "INSERT INTO source_cache VALUES (?,?,?,?,?)",
                    (
                        key,
                        payload,
                        checked,
                        (now + timedelta(days=2)).isoformat(),
                        failures,
                    ),
                )
        service = scheduled_service_class(DataService, Dataset)(
            store,
            provider=OfflineProvider(),
            today_fn=lambda: now.date(),
            now_fn=lambda: now,
        )
        DynamicDiscovery(service, transform, store).get()
        with store.connection(True) as db:
            original = db.execute(
                "SELECT * FROM stories WHERE status!='Archived' LIMIT 1"
            ).fetchone()
            if not original:
                raise ValueError("Expected a real-source finding for archive fixture")
            for i in range(50):
                row = list(original)
                row[0] = f"benchmark-archive-{i:03d}"
                row[1] = f"benchmark-key-{i:03d}"
                row[6] = "Archived"
                db.execute("INSERT INTO stories VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row)
                db.execute(
                    "INSERT INTO story_versions VALUES (?,?,?,?,?)",
                    (row[0], row[7], row[3], "Synthetic archive fixture", row[8]),
                )
    with sqlite3.connect(target.as_uri() + "?mode=ro", uri=True) as db:
        now = datetime.fromisoformat(
            db.execute("SELECT clock FROM benchmark_metadata").fetchone()[0]
        )
    store = Store(target)
    service = scheduled_service_class(DataService, Dataset)(
        store,
        provider=OfflineProvider(),
        today_fn=lambda: now.date(),
        now_fn=lambda: now,
    )
    runtime = DynamicDiscovery(service, transform, store)
    result = {
        "label": a.label,
        "platform": "Local host; not a Render memory or load measurement",
        "database": str(target),
        "synthetic_archived_records": 50,
        "requests": [],
    }
    with store.connection() as db:
        before = [
            tuple(r)
            for r in db.execute(
                "SELECT id,version,evidence_hash FROM stories ORDER BY id"
            )
        ]
    for i in range(3):
        start = time.perf_counter()
        report = runtime.get()
        body = json.dumps(report, ensure_ascii=False).encode()
        elapsed = time.perf_counter() - start
        row = {
            "request": i + 1,
            "seconds": round(elapsed, 6),
            "decoded_response_bytes": len(body),
            "archived_in_main_response": len(report.get("archived", [])),
            "current_count": len(report["findings"]),
        }
        result["requests"].append(row)
        print(json.dumps(row), flush=True)
    with store.connection() as db:
        after = [
            tuple(r)
            for r in db.execute(
                "SELECT id,version,evidence_hash FROM stories ORDER BY id"
            )
        ]
    result["identities_versions_evidence_preserved"] = before == after
    Path(a.output).write_text(json.dumps(result, indent=2), encoding="utf8")


if __name__ == "__main__":
    main()
