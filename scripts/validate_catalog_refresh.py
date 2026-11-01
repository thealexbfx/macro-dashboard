"""Offline disposable combined backend/Discovery/refresh capacity experiment.

Synthetic observations match committed actual-capture row counts and definitions.
Transport/parser injection is confined to this test script; no test mode exists in
the production worker. Never opens existing or production databases.
"""

import argparse
import json
import os
import sqlite3
import statistics
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from threading import Event, Thread

from scripts.linux_cgroup import snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--datasets", type=int, choices=(20, 50, 70, 100, 150), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(
        prefix="macrolens-refresh-disposable-"
    ) as directory:
        run(Path(directory), args.datasets, args.output)


def run(root, count, output):
    database = root / "disposable.sqlite3"
    os.environ.update(
        MACROLENS_V2_STATE_DB=str(database),
        MACROLENS_AI_ENABLED="false",
        MACROLENS_INGESTION_ENABLED="0",
        MACROLENS_CATALOG_REFRESH_ENABLED="0",
    )
    from fastapi.testclient import TestClient
    from backend.app.catalog.release_cli import ingest
    from backend.app.catalog.releases import activate, candidates, migrate as releases
    from backend.app.ingestion.catalog_refresh import (
        CatalogRefresh,
        CONFIG,
        migrate,
        PARSERS,
    )
    from backend.app.ingestion.native import Observation
    from backend.app.ingestion.official_snapshots import freeze
    from backend.app.ingestion.partition_schema import migrate as native
    from backend.app.v2 import main as v
    from backend.app.v2.native_reader import NativeReader

    pubs = candidates()
    rows = json.loads(CONFIG.read_text())["datasets"]
    live = json.loads(
        (
            CONFIG.parent.parent / "research/releases/first-live/selection.json"
        ).read_text()
    )["ids"]
    selected = live + [
        r["id"] for r in rows if r["automation_ready"] and r["id"] not in live
    ]
    selected = selected[:count]
    profiles = {
        r["id"]: r
        for r in json.loads((CONFIG.parent / "release_candidates.json").read_text())[
            "datasets"
        ]
    }

    def points(key, version=1):
        d = pubs[key].definition
        n = profiles[key]["validation"]["observations"]
        end = date(datetime.now(UTC).year - 1, 12, 31)
        if d.frequency == "weekly":
            end -= timedelta(days=(end.weekday() - d.calendar.week_ending) % 7)
        result = []
        for i in range(n):
            back = n - 1 - i
            if d.frequency in {"daily", "weekly"}:
                period = (
                    end - timedelta(days=back * (7 if d.frequency == "weekly" else 1))
                ).isoformat()
            elif d.frequency == "monthly":
                month = (end.year * 12 + end.month - 1) - back
                period = f"{month // 12:04d}-{month % 12 + 1:02d}"
            elif d.frequency == "quarterly":
                quarter = end.year * 4 + (end.month - 1) // 3 - back
                period = f"{quarter // 4:04d}-Q{quarter % 4 + 1}"
            else:
                period = str(end.year - back)
            value = None if i % 97 == 0 else float(i % 500 - 100)
            if version >= 2 and i == n // 2:
                value = float(-320 - version)
            result.append(Observation(period, period, value))
        return tuple(result)

    store = v.state_store
    reader = NativeReader(database)
    with store.connection(True) as db:
        native(db)
        releases(db)
        migrate(db)
        db.execute(
            "INSERT INTO library VALUES('sentinel','Existing saved research','2020-01-01',?, 'keep')",
            (
                json.dumps(
                    {"finding": {"datasets": ["retired_fixture"], "configuration": {}}}
                ),
            ),
        )
        for key in ("wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly"):
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
    for key in selected:
        pub = pubs[key]
        path, hashed = freeze(
            root / "seed",
            pub.definition,
            points(key),
            b"SYNTHETIC CAPACITY FIXTURE",
            pub.source_url,
        )
        assert ingest(store, pub, path, hashed)["state"] == "complete"
        path.unlink()
        with store.connection(True) as db:
            activate(db, pub, reader, approved=True)  # Disposable fixture only.
    now = datetime.now(UTC)
    with store.connection(True) as db:
        for key, spec in v.SPECS.items():
            history = [
                {
                    "date": f"{2010 + i // 12}-{i % 12 + 1:02d}-01",
                    "value": 100.0 + i / 20,
                }
                for i in range(190)
            ]
            dataset = v.Dataset(
                **spec.__dict__,
                status="ok",
                message="SYNTHETIC resource fixture",
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
        for key in selected:
            db.execute(
                "INSERT INTO catalog_refresh_jobs(dataset_id,next_due) VALUES(?,0)",
                (key,),
            )
    config = root / "policy.json"
    config.write_text(
        json.dumps(
            {
                "datasets": [
                    r | {"ingest_approved": True, "mode": "refresh"}
                    for r in rows
                    if r["id"] in selected
                ]
            }
        )
    )
    phase, fetches = [1], [0]

    def fetch(url, **kwargs):
        fetches[0] += 1
        version = phase[0]
        etag = f'"synthetic-{version}"'
        if kwargs.get("validators", {}).get("etag") == etag:
            return None, {"not_modified": True, "etag": etag}
        return json.dumps(
            {"SYNTHETIC_CAPACITY_FIXTURE": True, "version": version}
        ).encode(), {"etag": etag}

    def parse(entry, raw):
        d = pubs[entry["id"]].definition
        return d, points(d.id, json.loads(raw)["version"]), {"unit_label": d.units}

    for provider in {pubs[k].definition.provider for k in selected}:
        PARSERS[provider] = parse
    # ONS workbook dispatch has its own reviewed parser reference.
    import backend.app.ingestion.catalog_refresh as refresh_module

    refresh_module.parse_ons_construction = parse
    engine = CatalogRefresh(store, config=config, fetch=fetch)
    v.catalog_refresh_worker.engine = engine
    v.refresh_scheduler.interval = (
        0.05  # Test acceleration, not a proposed production cadence.
    )

    def forbidden(*a, **kw):
        raise AssertionError("External provider access forbidden in resource fixture")

    v.service.provider.fred_series = forbidden
    v.service.provider.market_series = forbidden
    stop, latencies = Event(), []
    sizes = {"db": 0, "wal": 0, "shm": 0}
    keeper = sqlite3.connect(database)
    keeper.execute("PRAGMA journal_mode=WAL")
    started, cpu = time.perf_counter(), time.process_time()

    def sample():
        while not stop.wait(0.05):
            for label, suffix in (("db", ""), ("wal", "-wal"), ("shm", "-shm")):
                p = Path(str(database) + suffix)
                sizes[label] = max(sizes[label], p.stat().st_size if p.exists() else 0)

    def traffic(client):
        paths = [
            "/api/v2/catalog?limit=20",
            "/api/v2/catalog?frequency=monthly&limit=20",
            "/api/v2/discovery",
            "/ready",
            f"/api/v2/observations/{selected[0]}?start=2000-01-01&end=2026-01-01&limit=40",
        ]
        while not stop.is_set():
            for path in paths:
                before = time.perf_counter()
                try:
                    response = client.get(path)
                except Exception:
                    latencies.append((0, 0))
                    return
                latencies.append(
                    (response.status_code, (time.perf_counter() - before) * 1000)
                )
            response = client.post(
                "/api/v2/compare",
                json={
                    "datasets": [selected[0], selected[1]],
                    "start": "2000-01-01",
                    "end": "2026-01-01",
                },
            )
            latencies.append((response.status_code, 0))
            stop.wait(0.1)

    def await_success():
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            with store.connection() as db:
                pending = db.execute(
                    "SELECT count(*) FROM catalog_refresh_jobs WHERE last_success IS NULL OR next_due < ?",
                    (time.time(),),
                ).fetchone()[0]
                failed = db.execute(
                    "SELECT dataset_id,error_code FROM catalog_refresh_jobs WHERE failures>0"
                ).fetchall()
            assert not failed, [tuple(r) for r in failed]
            if not pending:
                return
            time.sleep(0.1)
        raise AssertionError("Refresh completion budget exceeded")

    sampler = Thread(target=sample, daemon=True)
    sampler.start()
    with TestClient(v.app) as client:
        control = []
        for _ in range(10):
            before_control = time.perf_counter()
            assert client.get("/api/v2/catalog?limit=20").status_code == 200
            control.append((time.perf_counter() - before_control) * 1000)
        baseline_memory = {}
        if Path("/proc/self/status").exists():
            baseline_memory = {
                line.split(":")[0]: line.split(":")[1].strip()
                for line in Path("/proc/self/status").read_text().splitlines()
                if line.startswith(("VmRSS:", "VmHWM:"))
            }
        v.catalog_refresh_worker.enabled = True
        api = Thread(target=traffic, args=(client,), daemon=True)
        api.start()
        await_success()  # Identical normalized data, initial hash bootstrap.
        with store.connection() as db:
            before = db.execute("SELECT count(*) FROM norm_generations").fetchone()[0]
        with store.connection(True) as db:
            db.execute("UPDATE catalog_refresh_jobs SET next_due=0")
        await_success()  # Conditional unchanged check: no generation.
        with store.connection() as db:
            assert (
                db.execute("SELECT count(*) FROM norm_generations").fetchone()[0]
                == before
            )
        engine.cache = None
        phase[0] = 2
        with store.connection(True) as db:
            db.execute("UPDATE catalog_refresh_jobs SET next_due=0")
        await_success()  # Full-history revision reconciliation.
        for version in (
            3,
            4,
        ):  # Repeated releases exercise proof compaction and storage reuse.
            engine.cache = None
            phase[0] = version
            with store.connection(True) as db:
                db.execute("UPDATE catalog_refresh_jobs SET next_due=0")
            await_success()
        # Simultaneous explicit Discovery refresh and bounded overload.
        from backend.app.v2.workload import WorkloadBusy

        try:
            v.discovery_service.get(force_check=True)
        except WorkloadBusy:
            pass  # The simultaneous scheduled scan owns the bounded analysis slot.
        with ThreadPoolExecutor(16) as pool:
            burst = list(
                pool.map(
                    lambda _: client.get("/api/v2/catalog?limit=20").status_code,
                    range(48),
                )
            )
        stop.set()
        api.join(timeout=30)
        assert not api.is_alive() and len(latencies) >= 20
        assert v.refresh_scheduler.status()["consecutive_failures"] == 0
        assert client.get("/api/v2/catalog?limit=20").json()["total"] == count + 30
        for key in ("wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly"):
            assert client.get(f"/api/v2/catalog/{key}").status_code == 404
            assert (
                client.get(
                    f"/api/v2/observations/{key}?start=1960-01-01&end=2026-01-01"
                ).status_code
                == 404
            )
    sampler.join(timeout=2)
    with store.connection() as db:
        assert (
            db.execute("SELECT count(*) FROM ingest_observations").fetchone()[0] == 2403
        )
        assert (
            db.execute("SELECT notes FROM library WHERE id='sentinel'").fetchone()[0]
            == "keep"
        )
        assert (
            db.execute(
                "SELECT count(*) FROM norm_datasets WHERE ai_allowed!=0 OR discovery_allowed!=0"
            ).fetchone()[0]
            == 0
        )
        assert (
            db.execute(
                "SELECT count(*) FROM catalog_release_grants WHERE ai_allowed!=0 OR discovery_allowed!=0"
            ).fetchone()[0]
            == 0
        )
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        observations = db.execute("SELECT count(*) FROM norm_observations").fetchone()[
            0
        ]
        revisions = db.execute("SELECT count(*) FROM norm_revisions").fetchone()[0]
    assert all(s in {200, 429, 503} for s, _ in latencies), Counter(
        s for s, _ in latencies
    )
    assert all(s in {200, 429, 503} for s in burst)
    successful = sorted(ms for s, ms in latencies if s == 200 and ms)
    memory = {}
    if Path("/proc/self/status").exists():
        memory = {
            line.split(":")[0]: line.split(":")[1].strip()
            for line in Path("/proc/self/status").read_text().splitlines()
            if line.startswith(("VmRSS:", "VmHWM:"))
        }
    result = {
        "fixture": "SYNTHETIC observations, actual captured row-count profiles and reviewed definitions; offline transport/parser injection",
        "native_datasets": count,
        "public_datasets": count + 30,
        "observations": observations,
        "revisions": revisions,
        "seconds": time.perf_counter() - started,
        "cpu_seconds": time.process_time() - cpu,
        "backend_memory": memory,
        "baseline_worker_disabled_memory": baseline_memory,
        "baseline_catalog_p95_ms": sorted(control)[-1],
        "cgroup": snapshot(),
        "sampled_sqlite_peaks": sizes,
        "api_status": dict(Counter(s for s, _ in latencies)),
        "overload_status": dict(Counter(burst)),
        "api_p50_ms": statistics.median(successful),
        "api_p95_ms": successful[int(len(successful) * 0.95)],
        "api_max_ms": max(successful),
        "requests": len(latencies),
        "source_requests": fetches[0],
        "unchanged_generations": 0,
        "private_wb_rows": 2403,
        "saved_research_preserved": True,
        "graceful_shutdown": not v.catalog_refresh_worker.future
        or v.catalog_refresh_worker.future.done(),
        "production_access": False,
    }
    if result["cgroup"]["available"]:
        cg = result["cgroup"]
        assert cg["memory_max"] == 512 * 1024 * 1024 and cg["swap_max"] == 0
        assert cg["cpu_max"] == "50000 100000"
        assert cg["memory_events"].get("oom_kill", 0) == 0
        result["capacity_headroom_bytes"] = cg["memory_max"] - cg["memory_peak"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    keeper.close()


if __name__ == "__main__":
    main()
