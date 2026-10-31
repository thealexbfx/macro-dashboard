"""Actual captured histories -> disposable SQLite -> public-reader round trips.

No production paths, external provider calls, AI or scheduled ingestion.
"""

import argparse
import json
import os
import sqlite3
import statistics
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from threading import Event, Thread

from backend.app.catalog.release_cli import ingest
from backend.app.catalog.releases import activate, candidates, migrate
from backend.app.ingestion.partition_schema import migrate as native_migrate
from backend.app.v2.native_reader import NativeReader
from backend.app.v2.state import Store
from scripts.linux_cgroup import snapshot as cgroup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--database-name", default="disposable-release.sqlite3")
    parser.add_argument("--with-backend", action="store_true")
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if not (workspace / "DISPOSABLE_EXPANSION_ONLY").is_file() or str(
        workspace
    ).startswith("/var/"):
        parser.error("Marked disposable workspace required")
    if (
        not args.database_name.startswith("disposable-")
        or Path(args.database_name).name != args.database_name
    ):
        parser.error("Disposable database filename required")
    database = workspace / args.database_name
    os.environ.update(
        MACROLENS_V2_STATE_DB=str(database),
        MACROLENS_AI_ENABLED="false",
        MACROLENS_INGESTION_ENABLED="0",
    )
    store = Store(database)
    with store.connection(True) as db:
        native_migrate(db)
        migrate(db)
        db.execute(
            "INSERT OR IGNORE INTO library VALUES('release_sentinel','Existing saved research','2026-01-01','{}','Preserve exactly')"
        )
    index = json.loads((workspace / "source-results.json").read_text(encoding="utf-8"))
    publications = candidates()
    if args.ids:
        publications = {k: publications[k] for k in args.ids}
    reader = NativeReader(database, publications)
    stop, api_results = Event(), []
    thread = None
    if args.with_backend:
        from fastapi.testclient import TestClient

        from backend.app.v2 import main as v
        from backend.app.v2.catalog_api import PublicCatalog

        v.public_catalog = PublicCatalog(v.legacy_service, v.service.reader, reader)

        def requests():
            client = TestClient(v.app)
            while not stop.is_set():
                before = time.perf_counter()
                try:
                    response = client.get("/api/v2/catalog?limit=20")
                    api_results.append(
                        {
                            "status": response.status_code,
                            "ms": (time.perf_counter() - before) * 1000,
                        }
                    )
                except Exception:  # noqa: BLE001 -- recorded user-facing request failure
                    api_results.append({"status": 0})
                stop.wait(0.2)
            client.close()

        thread = Thread(target=requests, daemon=True)
        thread.start()
    # Keep WAL visible while measuring; storage includes staging and revision evidence.
    keeper = sqlite3.connect(database)
    keeper.execute("PRAGMA journal_mode=WAL")
    started, cpu = time.perf_counter(), time.process_time()
    rows, latencies = [], []
    for key, publication in publications.items():
        before = time.perf_counter()
        result = ingest(
            store, publication, index[key]["snapshot_path"], index[key]["snapshot_hash"]
        )
        if result["state"] not in {"complete", "unchanged"}:
            print(json.dumps({"failed": key, **result}), flush=True)
            rows.append({"id": key, "state": "failed", "details": result})
            continue
        with store.connection(True) as db:
            activate(db, publication, reader, approved=True)  # Disposable only.
        query = time.perf_counter()
        page = reader.observations(
            key,
            date(1800, 1, 1),
            date.today() - timedelta(days=1),
            limit=40,
            preview=True,
        )
        latencies.append((time.perf_counter() - query) * 1000)
        actual = page["dataset"]
        assert (
            actual["observations"]
            and actual["stored_provenance"]["ai_allowed"] is False
        )
        with store.connection() as db:
            count = db.execute(
                "SELECT count(*) FROM norm_observations WHERE dataset_id=?", (key,)
            ).fetchone()[0]
            assert count == index[key]["observations"]
            snapshot = json.loads(
                Path(index[key]["snapshot_path"]).read_text(encoding="utf-8")
            )
            source_points = snapshot["points"]
            for sample in (
                source_points[0],
                source_points[len(source_points) // 2],
                source_points[-1],
            ):
                observed = db.execute(
                    "SELECT value FROM norm_observations WHERE dataset_id=? AND period_key=?",
                    (key, sample["period"]),
                ).fetchone()
                assert observed is not None and observed[0] == sample["value"]
            assert tuple(
                db.execute(
                    "SELECT public_display,ai_allowed,discovery_allowed,rights_state FROM norm_datasets WHERE id=?",
                    (key,),
                ).fetchone()
            ) == (0, 0, 0, "unreviewed")
        rows.append(
            {
                "id": key,
                "state": "validated",
                "observations": count,
                "seconds": round(time.perf_counter() - before, 3),
                "preview_ms": round(latencies[-1], 3),
            }
        )
        print(key, rows[-1]["state"], count, flush=True)
    with store.connection() as db:
        assert (
            db.execute(
                "SELECT notes FROM library WHERE id='release_sentinel'"
            ).fetchone()[0]
            == "Preserve exactly"
        )
        assert (
            db.execute(
                "SELECT count(*) FROM catalog_scope_reviews WHERE scope IN ('ai','discovery') AND approved=1"
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                "SELECT count(*) FROM norm_datasets WHERE id LIKE 'wb_%'"
            ).fetchone()[0]
            == 0
        )
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        backup = sqlite3.connect(workspace / "disposable-backup.sqlite3")
        db.backup(backup)
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        restored = sqlite3.connect(workspace / "disposable-restored.sqlite3")
        backup.backup(restored)
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert restored.execute("SELECT count(*) FROM norm_observations").fetchone()[
            0
        ] == sum(r.get("observations", 0) for r in rows)
        restored.close()
        backup.close()
    stop.set()
    if thread is not None:
        thread.join(timeout=10)
        assert not thread.is_alive() and api_results
    try:
        import resource

        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (
            1024 if sys.platform != "darwin" else 1
        )
    except ImportError:
        import ctypes
        from ctypes import wintypes

        class MemoryCounters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t)
                for name in (
                    "PeakWorkingSetSize",
                    "WorkingSetSize",
                    "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage",
                    "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage",
                    "PagefileUsage",
                    "PeakPagefileUsage",
                )
            ]

        memory = MemoryCounters()
        memory.cb = ctypes.sizeof(memory)
        ctypes.windll.kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        ctypes.windll.psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(MemoryCounters),
            wintypes.DWORD,
        ]
        ctypes.windll.psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if not ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(memory), memory.cb
        ):
            raise OSError("Windows process memory measurement failed")
        peak_rss = memory.PeakWorkingSetSize
    result = {
        "platform": sys.platform,
        "datasets": rows,
        "validated": sum(r["state"] == "validated" for r in rows),
        "observations": sum(r.get("observations", 0) for r in rows),
        "seconds": round(time.perf_counter() - started, 3),
        "cpu_seconds": round(time.process_time() - cpu, 3),
        "peak_rss_bytes": peak_rss,
        "cgroup": cgroup(),
        "preview_ms_median": statistics.median(latencies) if latencies else None,
        "preview_ms_max": max(latencies) if latencies else None,
        "storage": {
            suffix or "database": database.with_name(database.name + suffix)
            .stat()
            .st_size
            if database.with_name(database.name + suffix).exists()
            else 0
            for suffix in ("", "-wal", "-shm")
        },
        "restore_integrity": "ok",
        "backend_loaded": args.with_backend,
        "concurrent_api_requests": len(api_results),
        "concurrent_api_errors": sum(r["status"] != 200 for r in api_results),
        "concurrent_api_ms_max": max(
            (r.get("ms", 0) for r in api_results), default=None
        ),
        "public_production_activated": False,
    }
    (workspace / "validation.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "datasets"}), flush=True)
    keeper.close()
    if result["validated"] != len(publications):
        raise SystemExit(
            "Some candidates failed ingestion validation; do not count as release ready"
        )


if __name__ == "__main__":
    main()
