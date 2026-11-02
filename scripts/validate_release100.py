"""Actual approved frozen histories, bounded CLI subprocesses and loaded backend.

Disposable SQLite only. No production backup/data is read. All activation and
rollback operations below affect a new temporary database, never Render.
"""

import argparse
import json
import os
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from collections import Counter
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Thread

from scripts.linux_cgroup import snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="release100-disposable-") as directory:
        exercise(Path(directory), args.bundle.resolve(), args.output)


def exercise(root, bundle, output):
    from backend.app.catalog import release100 as release
    from backend.app.catalog.release_cli import ingest
    from backend.app.catalog.releases import activate, candidates, migrate as releases
    from backend.app.ingestion.catalog_refresh import migrate as refresh_migrate
    from backend.app.ingestion.partition_schema import migrate as native
    from backend.app.v2.native_reader import NativeReader

    database = root / "disposable.sqlite3"
    os.environ.update(
        MACROLENS_V2_STATE_DB=str(database),
        MACROLENS_CATALOG_REFRESH_ENABLED="0",
        MACROLENS_INGESTION_ENABLED="0",
        MACROLENS_AI_ENABLED="false",
    )
    import numpy as np
    import pandas as pd
    from fastapi.testclient import TestClient
    from backend.app.v2 import main as v

    plan, records, pubs = (
        release.load_plan(),
        release.bundle_index(bundle),
        candidates(),
    )
    store, reader = v.state_store, NativeReader(database)
    with store.connection(True) as db:
        native(db)
        releases(db)
        refresh_migrate(db)
        db.execute(
            "INSERT INTO library VALUES('sentinel','Saved research','2020-01-01',?, 'preserve')",
            (
                json.dumps(
                    {"finding": {"datasets": ["retired_fixture"], "configuration": {}}}
                ),
            ),
        )
        for key in release.PRIVATE:
            db.execute(
                "INSERT INTO ingest_datasets(id,provider,metadata,updated_at) VALUES(?,'world_bank','{}','2020-01-01')",
                (key,),
            )
            for i in range(801):
                year, month = divmod(1960 * 12 + i, 12)
                db.execute(
                    "INSERT INTO ingest_observations VALUES(?,?,?,'fixture',1,'2020-01-01','2020-01-01','fixture')",
                    (key, f"{year:04d}-{month + 1:02d}", float(i)),
                )
    for key in plan["existing_native_ids"]:
        record = records[key]
        assert (
            ingest(store, pubs[key], record["snapshot_path"], record["snapshot_hash"])[
                "state"
            ]
            == "complete"
        )
        with store.connection(True) as db:
            activate(db, pubs[key], reader, approved=True)
    now, legacy_rows = datetime.now(UTC), 0
    with store.connection(True) as db:
        for i, (key, spec) in enumerate(v.SPECS.items()):
            end = now.date() - timedelta(days=1)
            if spec.frequency == "monthly":
                end = now.date().replace(day=1) - timedelta(days=1)
            if spec.frequency == "quarterly":
                end = now.date().replace(
                    month=((now.month - 1) // 3) * 3 + 1, day=1
                ) - timedelta(days=1)
            dates = pd.date_range(
                "1990-01-01",
                end,
                freq={
                    "daily": "B",
                    "weekly": "W-THU",
                    "monthly": "MS",
                    "quarterly": "QS",
                }[spec.frequency],
            )
            t = np.arange(len(dates))
            values = 100 + i * 10 + 0.025 * t + 3 * np.sin(t / 13 + i)
            if spec.units.lower().startswith("percent"):
                values = 3 + 0.2 * np.sin(t / 13 + i)
            history = [
                {"date": str(d.date()), "value": float(x)}
                for d, x in zip(dates, values)
            ]
            legacy_rows += len(history)
            dataset = v.Dataset(
                **spec.__dict__,
                status="ok",
                message="SYNTHETIC LEGACY LOAD FIXTURE",
                verification={
                    "status": "Calculation verified",
                    "raw_status": "Unverified",
                },
                observations=history,
                latest_value=history[-1]["value"],
                latest_observation_date=history[-1]["date"],
                retrieved_at=now.isoformat(),
            )
            db.execute(
                "INSERT INTO source_cache VALUES(?,?,?,?,0)",
                (
                    key,
                    dataset.model_dump_json(),
                    now.isoformat(),
                    (now + timedelta(days=365)).isoformat(),
                ),
            )

    def forbidden(*a, **kw):
        raise AssertionError("External legacy providers forbidden in offline rehearsal")

    v.service.provider.fred_series = forbidden
    v.service.provider.market_series = forbidden
    v.refresh_scheduler.interval = 1
    stop, timings, status = Event(), [], Counter()
    peaks = {"db": 0, "wal": 0, "shm": 0}
    keeper = sqlite3.connect(database)
    keeper.execute("PRAGMA journal_mode=WAL")
    started, cpu = time.perf_counter(), time.process_time()
    cli_peak = [0]

    def cli(operation, *flags):
        command = [
            sys.executable,
            "-B",
            "-m",
            "backend.app.catalog.release100",
            operation,
            "--database",
            str(database),
            "--bundle",
            str(bundle),
            *flags,
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)),
        )
        sample_stop = Event()

        def sample_child():
            while not sample_stop.wait(0.005):
                try:
                    proc = Path(f"/proc/{process.pid}")
                    if (
                        b"backend.app.catalog.release100"
                        not in (proc / "cmdline").read_bytes()
                    ):
                        continue  # Exclude the fork's inherited pre-exec backend footprint.
                    for line in (proc / "status").read_text().splitlines():
                        if line.startswith("VmHWM:"):
                            cli_peak[0] = max(cli_peak[0], int(line.split()[1]) * 1024)
                except (OSError, ValueError):
                    pass

        sampling = Thread(target=sample_child, daemon=True)
        sampling.start()
        try:
            stdout, stderr = process.communicate(timeout=180)
        finally:
            sample_stop.set()
            sampling.join(timeout=2)
            if process.poll() is None:
                process.kill()
                process.wait()
        assert process.returncode == 0, stderr[-3000:]
        return json.loads(stdout.splitlines()[-1])

    def traffic(client):
        paths = [
            "/api/v2/catalog?limit=20",
            "/api/v2/discovery",
            "/ready",
            f"/api/v2/observations/{plan['existing_native_ids'][0]}?start=2020-01-01&end=2025-01-01&limit=40",
        ]
        while not stop.is_set():
            for path in paths:
                before = time.perf_counter()
                try:
                    response = client.get(path)
                    status[(path.split("?")[0], response.status_code)] += 1
                    if response.status_code == 200:
                        timings.append((time.perf_counter() - before) * 1000)
                except Exception:
                    status[(path, 0)] += 1
            for label, suffix in (("db", ""), ("wal", "-wal"), ("shm", "-shm")):
                path = Path(str(database) + suffix)
                peaks[label] = max(
                    peaks[label], path.stat().st_size if path.exists() else 0
                )
            stop.wait(0.15)

    with TestClient(v.app) as client:
        for _ in range(120):
            if client.get("/api/v2/discovery").status_code == 200:
                break
            time.sleep(0.1)
        baseline = release.check(database)
        assert baseline["public"] == 43
        bg = Thread(target=traffic, args=(client,), daemon=True)
        bg.start()
        invocations = 0
        for _ in range(100):
            result = cli("stage")
            invocations += 1
            assert result["public"] == 43
            if not result["results"]:
                break
        else:
            raise AssertionError("Bounded stage failed to converge")
        assert cli("validate")["validated"] == 57
        assert cli("publish", "--approve-publication")["public"] == 100
        assert cli("publish", "--approve-publication")["state"] == "already_published"
        assert cli("verify")["public"] == 100
        from scripts.smoke_release100 import checks

        def request(method, path, body=None):
            response = (
                client.request(method, path, json=body)
                if body is not None
                else client.request(method, path)
            )
            return response.status_code, response.json()

        smoke = checks(request)
        assert cli("rollback", "--approve-rollback")["public"] == 43
        assert cli("rollback", "--approve-rollback")["public"] == 43
        assert cli("publish", "--approve-publication")["public"] == 100
        stop.set()
        bg.join(timeout=30)
        assert not bg.is_alive()
    with store.connection() as db:
        assert (
            db.execute("SELECT count(*) FROM ingest_observations").fetchone()[0] == 2403
        )
        assert (
            db.execute("SELECT notes FROM library WHERE id='sentinel'").fetchone()[0]
            == "preserve"
        )
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        with closing(sqlite3.connect(root / "backup.sqlite3")) as backup:
            db.backup(backup)
            with closing(sqlite3.connect(root / "restored.sqlite3")) as restored:
                backup.backup(restored)
                assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert (
                    restored.execute(
                        "SELECT count(*) FROM ingest_observations"
                    ).fetchone()[0]
                    == 2403
                )
    assert all(code in {200, 429, 503} for _, code in status), status
    try:
        import resource

        child_peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss * 1024
    except ImportError:
        child_peak = None  # Windows is not Linux resource evidence.
    memory = (
        {
            line.split(":")[0]: line.split(":")[1].strip()
            for line in Path("/proc/self/status").read_text().splitlines()
            if line.startswith(("VmRSS:", "VmHWM:"))
        }
        if Path("/proc/self/status").exists()
        else {}
    )
    result = {
        "actual_native_observations": sum(r["rows"] for r in records.values()),
        "synthetic_legacy_observations": legacy_rows,
        "public": 100,
        "stage_invocations": invocations,
        "seconds": time.perf_counter() - started,
        "backend_cpu_seconds": time.process_time() - cpu,
        "backend_memory": memory,
        "cli_peak_rss_bytes": cli_peak[0] or None,
        "child_rusage_peak_rss_bytes_including_pre_exec": child_peak,
        "cgroup": snapshot(),
        "sqlite_peaks": peaks,
        "api_status": {f"{p}:{c}": n for (p, c), n in status.items()},
        "p95_ms": sorted(timings)[int(len(timings) * 0.95)],
        "median_ms": statistics.median(timings),
        "smoke": smoke,
        "rollback_and_restore_passed": True,
        "production_access": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    keeper.close()


if __name__ == "__main__":
    main()
