"""Full-catalog offline HTTP/resource/browser fixture; temporary databases only."""

import argparse
import json
import os
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Thread

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def serve(port):
    with tempfile.TemporaryDirectory(prefix="batch0-catalog-") as directory:
        os.environ.update(
            MACROLENS_V2_STATE_DB=str(Path(directory) / "disposable.sqlite3"),
            MACROLENS_AI_ENABLED="false",
            MACROLENS_INGESTION_ENABLED="0",
        )
        print(
            json.dumps({"fixture_database": os.environ["MACROLENS_V2_STATE_DB"]}),
            flush=True,
        )
        from backend.app.v2 import main as v
        from backend.app.v2.catalog_api import PublicCatalog
        from scripts.batch0_catalog_fixture import seed_catalog

        reader = seed_catalog(v.state_store)
        reader.now = lambda: datetime.now(UTC)
        v.public_catalog = PublicCatalog(v.legacy_service, v.service.reader, reader)

        def forbidden(*args, **kwargs):
            raise AssertionError("External data/AI forbidden in synthetic fixture")

        v.service.provider.fred_series = forbidden
        v.service.provider.market_series = forbidden
        now = datetime.now(UTC)
        with v.state_store.connection(True) as db:
            for key, spec in v.SPECS.items():
                points = [
                    {
                        "date": f"{2020 + i // 12}-{i % 12 + 1:02d}-01",
                        "value": 100 + i / 10,
                    }
                    for i in range(60)
                ]
                d = v.Dataset(
                    **spec.__dict__,
                    status="stale",
                    message="SYNTHETIC OFFLINE BROWSER FIXTURE",
                    observations=points,
                    latest_observation_date=points[-1]["date"],
                    latest_value=points[-1]["value"],
                    retrieved_at=now.isoformat(),
                )
                db.execute(
                    "INSERT INTO source_cache VALUES(?,?,?,?,?)",
                    (
                        key,
                        d.model_dump_json(),
                        now.isoformat(),
                        (now + timedelta(days=365)).isoformat(),
                        0,
                    ),
                )
        # Keep WAL/SHM observable and prevent final-close checkpoint hiding file sizes.
        keeper = sqlite3.connect(v.state_store.path)
        keeper.execute("PRAGMA journal_mode=WAL")
        import uvicorn

        print(
            json.dumps(
                {
                    "fixture_ready": True,
                    "database": str(v.state_store.path),
                    "synthetic_native": 279,
                }
            ),
            flush=True,
        )
        try:
            uvicorn.run(
                v.app, host="127.0.0.1", port=port, workers=1, log_level="warning"
            )
        finally:
            keeper.close()


def probe():
    from scripts.linux_cgroup import snapshot

    port = 8139
    with tempfile.TemporaryDirectory(prefix="batch0-probe-") as out:
        logpath = Path(out) / "server.log"
        with logpath.open("w") as log:
            child = subprocess.Popen(
                [sys.executable, "-B", __file__, "--serve", "--port", str(port)],
                stdout=log,
                stderr=log,
            )
            peak_files = {suffix: 0 for suffix in ("", "-wal", "-shm")}
            stop = Event()

            def sample_files():
                while not stop.wait(0.1):
                    try:
                        with logpath.open() as stream:
                            first = json.loads(stream.readline())
                        path = first["fixture_database"]
                        for suffix, previous_peak in peak_files.items():
                            file = Path(path + suffix)
                            peak_files[suffix] = max(
                                previous_peak,
                                file.stat().st_size if file.exists() else 0,
                            )
                    except (OSError, ValueError, KeyError):
                        pass

            sampler = Thread(target=sample_files, daemon=True)
            sampler.start()

            def request(path):
                start = time.perf_counter()
                try:
                    with urllib.request.urlopen(
                        urllib.request.Request(
                            f"http://127.0.0.1:{port}" + path,
                            data=json.dumps(
                                {
                                    "datasets": [
                                        "fixture_catalog_002",
                                        "fixture_catalog_016",
                                    ],
                                    "start": "2000-01-01",
                                    "end": "2009-12-31",
                                }
                            ).encode()
                            if path == "/api/v2/compare"
                            else None,
                            headers={"Content-Type": "application/json"},
                        ),
                        timeout=30,
                    ) as r:
                        payload = r.read()
                        return (
                            r.status,
                            (time.perf_counter() - start) * 1000,
                            len(payload),
                            json.loads(payload),
                            path,
                            r.headers.get("Retry-After"),
                        )
                except urllib.error.HTTPError as exc:
                    body = exc.read(4096).decode(errors="replace")
                    return (
                        exc.code,
                        (time.perf_counter() - start) * 1000,
                        0,
                        {"error": body},
                        path,
                        exc.headers.get("Retry-After"),
                    )

            try:
                for _ in range(240):
                    if child.poll() is not None:
                        raise AssertionError(logpath.read_text())
                    try:
                        if request("/health")[0] == 200:
                            break
                    except OSError:
                        pass
                    time.sleep(0.5)
                else:
                    raise AssertionError("Fixture startup timeout")
                cold = request("/api/v2/catalog?limit=12")
                assert cold[0] == 200 and cold[3]["total"] == 309
                paths = [
                    "/api/v2/catalog?limit=12&offset=12",
                    "/api/v2/catalog?frequency=monthly&limit=12",
                    "/api/v2/observations/fixture_catalog_002?start=2000-01-01&end=2010-01-01&limit=40",
                    "/api/v2/observations/cpi?start=2020-01-01&end=2023-01-01&limit=40",
                    "/ready",
                    "/api/v2/discovery",
                    "/api/v2/compare",
                ]
                interactive = [request(path) for path in paths[:5] * 3]
                assert all(r[0] == 200 for r in interactive), interactive
                samples = []
                with ThreadPoolExecutor(max_workers=4) as pool:
                    samples = list(pool.map(request, paths * 12))
                with ThreadPoolExecutor(max_workers=24) as pool:
                    overload = list(pool.map(request, [paths[2]] * 96))
                unexpected = [
                    {"path": r[4], "status": r[0], "response": r[3]}
                    for r in samples + overload
                    if r[0] not in {200, 429, 503}
                ]
                assert not unexpected, {
                    "unexpected": unexpected,
                    "server_log_tail": logpath.read_text()[-12000:],
                }
                assert all(
                    r[5] == "2" for r in samples + overload if r[0] in {429, 503}
                )
                assert request("/api/v2/catalog/wb_copper_monthly")[0] == 404
                assert request("/api/v2/observations/wb_copper_monthly")[0] == 404
                ready = request("/ready")
                for _ in range(30):
                    if ready[0] == 200:
                        break
                    time.sleep(0.2)
                    ready = request("/ready")
                assert ready[0] == 200
                info = json.loads(
                    next(
                        line
                        for line in logpath.read_text().splitlines()
                        if '"fixture_ready"' in line
                    )
                )
                dbpath = Path(info["database"])
                with (
                    closing(sqlite3.connect(dbpath)) as db,
                    closing(sqlite3.connect(Path(out) / "restored.sqlite3")) as restored,
                ):
                    db.backup(restored)
                    assert (
                        restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                    )
                    assert (
                        restored.execute(
                            "SELECT count(*) FROM norm_datasets WHERE ai_allowed!=0 OR discovery_allowed!=0"
                        ).fetchone()[0]
                        == 0
                    )
                    observations = restored.execute(
                        "SELECT count(*) FROM norm_observations"
                    ).fetchone()[0]
                status = (
                    Path(f"/proc/{child.pid}/status").read_text()
                    if sys.platform == "linux"
                    else ""
                )
                process_memory = {
                    line.split(":")[0]: line.split(":")[1].strip()
                    for line in status.splitlines()
                    if line.startswith(("VmRSS:", "VmHWM:"))
                }
                successful = sorted(r[1] for r in samples if r[0] == 200)
                interactive_times = sorted(r[1] for r in interactive)
                result = {
                    "synthetic_only": True,
                    "public_catalog_size": 309,
                    "native_observations": observations,
                    "backend_memory": process_memory,
                    "cgroup": snapshot(),
                    "cold_page_ms": round(cold[1], 2),
                    "page_bytes": cold[2],
                    "latency_ms_p50": round(statistics.median(successful), 2),
                    "latency_ms_p95": round(successful[int(len(successful) * 0.95)], 2),
                    "interactive_status": {"200": len(interactive), "503": 0},
                    "interactive_latency_ms_p50": round(
                        statistics.median(interactive_times), 2
                    ),
                    "interactive_latency_ms_p95": round(
                        interactive_times[int(len(interactive_times) * 0.95)], 2
                    ),
                    "concurrent_mixed_status": {
                        str(c): sum(r[0] == c for r in samples) for c in (200, 429, 503)
                    },
                    "overload_status": {
                        str(c): sum(r[0] == c for r in overload)
                        for c in (200, 429, 503)
                    },
                    "sqlite_bytes": {
                        suffix or "db": Path(str(dbpath) + suffix).stat().st_size
                        if Path(str(dbpath) + suffix).exists()
                        else 0
                        for suffix in ("", "-wal", "-shm")
                    },
                    "sampled_peak_sqlite_bytes": dict(peak_files),
                    "backup_restore_and_privacy": True,
                }
                child.terminate()
                child.wait(timeout=25)
                if sys.platform == "linux":
                    assert child.returncode in (0, -15)
                result["graceful_shutdown"] = sys.platform == "linux"
                print(json.dumps(result, indent=2))
            finally:
                stop.set()
                sampler.join(timeout=2)
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8139)
    args = parser.parse_args()
    serve(args.port) if args.serve else probe()
