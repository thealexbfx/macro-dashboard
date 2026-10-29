"""Disposable loopback integration harness; never imports or copies production state.

python scripts/validate_phase4b.py --output ../phase4b-staging/run-01 --workbook ../wb-pilot-inspect.xlsx
Use --disabled for the release-default control run. Outputs must be new children
of work/phase4b-staging. Synthetic public histories + the supplied real WB snapshot.
No external HTTP or AI is allowed. This script is not an application entrypoint.
"""

from __future__ import annotations

import argparse
import ctypes
import itertools
import json
import os
import signal
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from threading import Event, Thread
from typing import ClassVar
from zipfile import ZIP_DEFLATED, ZipFile

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO.parent / "phase4b-staging"
sys.path.insert(0, str(REPO))


def atomic_json(path, payload):
    temporary = path.with_suffix(path.suffix + ".next")
    temporary.write_text(json.dumps(payload))
    for attempt in range(50):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 49:
                raise
            time.sleep(0.01)


def read_control(out):
    try:
        return json.loads((out / "control.json").read_text())
    except (OSError, ValueError):
        return {}


def database_bytes(out):
    total = 0
    for suffix in ["", "-wal", "-shm"]:
        try:
            total += (out / ("state.sqlite3" + suffix)).stat().st_size
        except FileNotFoundError:
            pass  # SQLite can checkpoint/remove WAL between directory reads.
    return total


def db_read(out, sql, args=()):
    with sqlite3.connect(out / "state.sqlite3", timeout=2) as db:
        db.row_factory = sqlite3.Row
        return [dict(r) for r in db.execute(sql, args)]


def db_write(out, sql, args=()):
    with sqlite3.connect(out / "state.sqlite3", timeout=2) as db:
        db.execute(sql, args)


def serve(out, port, disabled):
    assert out.is_relative_to(ROOT) and (out / "DISPOSABLE").exists()
    instance = uuid.uuid4().hex
    (out / "server-pid").write_text(str(os.getpid()))
    os.environ["MACROLENS_V2_STATE_DB"] = str(out / "state.sqlite3")
    os.environ["MACROLENS_INGESTION_ENABLED"] = "0" if disabled else "1"
    os.environ["MACROLENS_AI_ENABLED"] = "false"
    os.environ["MACROLENS_ADMIN_TOKEN"] = "phase4b-synthetic-local-token"
    os.environ.pop("OPENAI_API_KEY", None)
    import numpy as np
    import pandas as pd
    import requests
    import uvicorn

    from backend.app.ingestion.runner import Ingestion
    from backend.app.ingestion.world_bank import URL, WorldBank
    from backend.app.v2 import main as v
    from backend.app.v2.definitions import SPECS
    from backend.app.v2.state import dumps

    def forbidden(*args, **kwargs):
        raise AssertionError("External network and AI are prohibited in this harness")

    requests.sessions.Session.request = forbidden
    urllib.request.urlopen = forbidden
    # Public datasets are fixture observations with unchanged real definitions.
    # No local user cache/history is copied.
    with v.state_store.connection(True) as db:
        if not db.execute("SELECT 1 FROM source_cache LIMIT 1").fetchone():
            now = datetime.now(UTC)
            counts = {}
            for index, (key, spec) in enumerate(SPECS.items()):
                aliases = {
                    "daily": "B",
                    "weekly": "W-THU",
                    "monthly": "MS",
                    "quarterly": "QS",
                }
                end = now.date() - timedelta(days=1)
                if spec.frequency == "monthly":
                    end = now.date().replace(day=1) - timedelta(days=1)
                elif spec.frequency == "quarterly":
                    end = now.date().replace(
                        month=((now.month - 1) // 3) * 3 + 1, day=1
                    ) - timedelta(days=1)
                dates = pd.date_range("1990-01-01", end, freq=aliases[spec.frequency])
                t = np.arange(len(dates))
                values = 100 + index * 10 + 0.025 * t + 3 * np.sin(t / 13 + index)
                if spec.units.lower().startswith("percent"):
                    values = 3 + 0.2 * np.sin(t / 13 + index)
                if key == "unemployment":
                    # Deliberately synthetic historical shock exercises capture/reopening.
                    values[np.asarray(dates == pd.Timestamp("2020-05-01"))] = 15.0
                # A final synthetic anomaly makes the real evidence workflow non-empty.
                values[-1] *= 1.04
                observations = [
                    v.Observation(date=str(d.date()), value=float(x))
                    for d, x in zip(dates, values)
                ]
                dataset = v.Dataset(
                    **asdict(spec),
                    observations=observations,
                    status="ok",
                    message="SYNTHETIC Phase 4B load fixture; not economic evidence",
                    latest_observation_date=observations[-1].date,
                    latest_value=observations[-1].value,
                    coverage_start=observations[0].date,
                    coverage_end=observations[-1].date,
                    retrieved_at=now.isoformat(),
                    verification={
                        "status": "Calculation verified",
                        "raw_status": "Unverified",
                    },
                    quality_warnings=["Synthetic staging observations"],
                )
                db.execute(
                    "INSERT INTO source_cache VALUES (?,?,?,?,0)",
                    (
                        key,
                        dumps(dataset.model_dump()),
                        now.isoformat(),
                        (now + timedelta(days=2)).isoformat(),
                    ),
                )
                counts[key] = len(observations)
            (out / "fixture-counts.json").write_text(json.dumps(counts))
    raw = (out / "worldbank.xlsx").read_bytes()

    class Response:
        status_code = 200
        headers: ClassVar[dict] = {}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def iter_content(self, size):
            mode = read_control(out).get("fault", "normal")
            if mode == "slow":
                (out / "slow-entered").write_text("staging")
                time.sleep(3)
            data = b"<html>invalid workbook</html>" if mode == "malformed" else raw
            if mode == "revision":
                source = ZipFile(BytesIO(raw))
                target = BytesIO()
                with ZipFile(target, "w", compression=ZIP_DEFLATED) as z:
                    for name in source.namelist():
                        value = source.read(name)
                        if name == "xl/worksheets/sheet2.xml":
                            root = ET.fromstring(value)
                            ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
                            rows = root.findall(".//" + ns + "row")
                            last = rows[-1]
                            copper = next(
                                c for c in last if c.get("r", "").startswith("BM")
                            )
                            cell = copper.find(ns + "v")
                            cell.text = str(float(cell.text) + 1)
                            value = ET.tostring(root)
                        z.writestr(name, value)
                data = target.getvalue()
            for start in range(0, len(data), size):
                yield data[start : start + size]

    class SnapshotSession:
        def get(self, url, **kwargs):
            assert url == URL
            mode = read_control(out).get("fault")
            if mode == "outage":
                raise requests.Timeout("synthetic outage")
            if mode == "unexpected":
                raise RuntimeError("synthetic unexpected failure")
            return Response()

    if not disabled:
        adapter = WorldBank(
            session=SnapshotSession(), cancel_event=v.ingestion_worker._cancel
        )
        v.ingestion_worker._engine = Ingestion(
            v.state_store, [adapter], cancel_event=v.ingestion_worker._cancel
        )
    v.refresh_scheduler.interval = 1
    original_get = v.discovery_service.get

    def discovery(*args, **kwargs):
        if read_control(out).get("discovery_failure"):
            raise RuntimeError("synthetic Discovery failure")
        return original_get(*args, **kwargs)

    v.discovery_service.get = discovery
    server = uvicorn.Server(
        uvicorn.Config(
            v.app,
            host="0.0.0.0"
            if os.getenv("MACROLENS_PHASE4C_CONTAINER") == "1"
            else "127.0.0.1",
            port=port,
            access_log=False,
            log_level="warning",
        )
    )

    def own_metrics():
        while not server.should_exit:
            metrics = current_metrics()
            metrics["sampled_at"] = time.monotonic()
            metrics["instance"] = instance
            atomic_json(out / "metrics.json", metrics)
            time.sleep(0.2)

    Thread(target=own_metrics, daemon=True).start()
    last_nonce = None

    def controls():
        nonlocal last_nonce
        while not server.should_exit:
            control = read_control(out)
            v.refresh_scheduler.interval = control.get("interval", 1)
            if control.get("nonce") != last_nonce:
                last_nonce = control.get("nonce")
                engine = v.ingestion_worker._engine
                if engine is not None:
                    engine.adapters["world_bank"]._expires = 0
            if control.get("shutdown"):
                server.should_exit = True
                break
            time.sleep(0.1)

    Thread(target=controls, daemon=True).start()
    server.run()


def current_metrics():
    # Sample inside the actual ASGI interpreter, never its Windows venv launcher.
    if os.name == "nt":

        class Memory(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong)] + [
                (n, ctypes.c_size_t)
                for n in [
                    "peak",
                    "rss",
                    "peak_paged",
                    "paged",
                    "peak_nonpaged",
                    "nonpaged",
                    "commit",
                    "peak_commit",
                ]
            ]

        m = Memory()
        m.cb = ctypes.sizeof(m)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.c_void_p(-1), ctypes.byref(m), m.cb
        ):
            raise OSError("Memory sampling failed")
        return {
            "rss": m.rss,
            "peak_rss": m.peak,
            "private_commit": m.commit,
            "cpu_seconds": time.process_time(),
            "pid": os.getpid(),
        }
    status = dict(
        line.split(":", 1)
        for line in Path("/proc/self/status").read_text().splitlines()
        if ":" in line
    )
    from linux_cgroup import snapshot

    return {
        "cgroup": snapshot(),
        "rss": int(status["VmRSS"].split()[0]) * 1024,
        "peak_rss": int(status["VmHWM"].split()[0]) * 1024,
        "cpu_seconds": time.process_time(),
        "pid": os.getpid(),
    }


def inspect_disposable_container(name):
    found = subprocess.run(
        ["docker", "container", "inspect", name],
        capture_output=True,
        text=True,
        check=False,
    )
    if found.returncode:
        return None
    info = json.loads(found.stdout)[0]
    labels = info["Config"].get("Labels") or {}
    if labels.get("macrolens.phase4c") != "disposable":
        raise RuntimeError("Refuse to operate on an unrelated container")
    return info


def parent(out, workbook, disabled):
    if not out.is_relative_to(ROOT) or out == ROOT:
        raise ValueError("Output must be a new directory inside work/phase4b-staging")
    out.mkdir(parents=True, exist_ok=False)
    (out / "DISPOSABLE").write_text(
        "Phase 4B; synthetic public observations and WB snapshot only"
    )
    raw = workbook.read_bytes()
    if len(raw) > 4 * 1024 * 1024 or not raw.startswith(b"PK"):
        raise ValueError("Expected the small, previously verified official XLSX")
    (out / "worldbank.xlsx").write_bytes(raw)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    phase = ["startup_disabled" if disabled else "cold_start_backfill"]
    samples, requests_log, checks = [], [], {}
    control = {"fault": "normal", "nonce": 0, "interval": 1}
    stop_sampling = Event()
    child = None
    sampler = None
    docker_image = os.getenv("MACROLENS_PHASE4C_DOCKER_IMAGE")
    docker_name = "macrolens-phase4c"
    docker_states = []
    container_out = Path("/workspace/phase4b-staging") / out.name
    result = {
        "fixture_kind": os.getenv(
            "MACROLENS_RESOURCE_FIXTURE", "supplied_workbook_snapshot"
        ),
        "mode": "disabled" if disabled else "enabled",
        "platform": sys.platform,
        "workbook_hash": sha256(raw).hexdigest(),
        "disposable_database": str(out / "state.sqlite3"),
    }

    def emit(message):
        print(message, flush=True)

    def command(**kwargs):
        control.update(kwargs)
        control["nonce"] += 1
        atomic_json(out / "control.json", control)
        time.sleep(0.15)

    def request(path, payload=None, admin=False):
        start = time.monotonic()
        headers = {"Content-Type": "application/json"}
        if admin:
            headers["Authorization"] = "Bearer phase4b-synthetic-local-token"
        req = urllib.request.Request(
            origin + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as exc:
            status, body = exc.code, exc.read()
        elapsed = time.monotonic() - start
        requests_log.append(
            {
                "phase": phase[0],
                "path": path,
                "status": status,
                "seconds": elapsed,
                "bytes": len(body),
            }
        )
        return status, json.loads(body)

    def until(fn, seconds=90):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                value = fn()
                if value:
                    return value
            except (OSError, ValueError, sqlite3.Error):
                pass
            if child and child.poll() is not None:
                raise RuntimeError("Staging child exited; inspect server log")
            time.sleep(0.2)
        raise TimeoutError("Staging condition timed out in phase " + phase[0])

    def docker_inspect():
        return inspect_disposable_container(docker_name)

    def record_docker():
        info = docker_inspect()
        if info is None:
            return
        entry = {
            "id": info["Id"],
            "state": info["State"],
            "limits": {
                k: info["HostConfig"][k]
                for k in ["Memory", "MemorySwap", "NanoCpus", "NetworkMode"]
            },
        }
        if docker_states and docker_states[-1]["id"] == entry["id"]:
            docker_states[-1] = entry
        else:
            docker_states.append(entry)
        atomic_json(out / "docker-states.json", docker_states)

    def spawn():
        nonlocal child, sampler
        args = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--serve",
            str(out),
            "--port",
            str(port),
        ]
        if disabled:
            args += ["--disabled"]
        if docker_image:
            if sys.platform != "linux":
                raise RuntimeError("Docker backend validation requires a Linux host")
            if docker_inspect():
                subprocess.run(
                    ["docker", "rm", docker_name], check=True, capture_output=True
                )
            args = [
                "docker",
                "run",
                "--name",
                docker_name,
                "--label",
                "macrolens.phase4c=disposable",
                "--memory=512m",
                "--memory-swap=512m",
                "--cpus=0.5",
                "--network=macrolens-phase4c-internal",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "-p",
                f"127.0.0.1:{port}:{port}",
                "-v",
                f"{ROOT}:/workspace/phase4b-staging",
                "-e",
                "MACROLENS_PHASE4C_CONTAINER=1",
                docker_image,
                "python",
                "scripts/validate_phase4b.py",
                "--serve",
                str(container_out),
                "--port",
                str(port),
            ]
            if disabled:
                args += ["--disabled"]
        (out / "server-pid").unlink(missing_ok=True)
        (out / "metrics.json").unlink(missing_ok=True)
        with open(out / "server.log", "ab") as log:
            child = subprocess.Popen(
                args, cwd=REPO, stdout=log, stderr=subprocess.STDOUT
            )
        until(lambda: (out / "server-pid").exists())
        backend_pid = int((out / "server-pid").read_text())

        def sample():
            try:
                while not stop_sampling.wait(0.2) and child.poll() is None:
                    try:
                        m = json.loads((out / "metrics.json").read_text())
                    except (OSError, ValueError):
                        continue
                    assert m["pid"] == backend_pid
                    if time.monotonic() - m["sampled_at"] > (
                        10 if sys.platform == "linux" else 2
                    ):
                        raise OSError("Stale backend telemetry")
                    m.update(phase=phase[0], time=time.monotonic())
                    m["sqlite_bytes"] = database_bytes(out)
                    samples.append(m)
            except OSError:
                pass

        sampler = Thread(target=sample, daemon=True)
        sampler.start()
        until(lambda: request("/health")[0] == 200)

    def force_due():
        db_write(out, "UPDATE ingest_jobs SET next_due=0")

    def runs():
        return db_read(out, "SELECT * FROM ingest_runs ORDER BY started_at")

    def finish_backfill():
        end = time.monotonic() + 120
        while time.monotonic() < end:
            job = db_read(out, "SELECT * FROM ingest_jobs")[0]
            if job["last_success"] and not job["cursor"]:
                return
            if job["cursor"]:
                force_due()
            time.sleep(0.2)
        raise TimeoutError("Backfill incomplete")

    def stop(graceful=True):
        t = time.monotonic()
        if docker_image:
            if graceful:
                subprocess.run(
                    ["docker", "stop", "--time", "20", docker_name],
                    check=True,
                    capture_output=True,
                )
            else:
                subprocess.run(
                    ["docker", "kill", "--signal", "KILL", docker_name],
                    check=True,
                    capture_output=True,
                )
            child.wait(timeout=10)
            record_docker()
        elif graceful:
            command(shutdown=True)
            child.wait(timeout=20)
        else:
            pid = int((out / "server-pid").read_text())
            assert pid > 1
            os.kill(pid, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)
            child.wait(timeout=10)
        sampler.join(timeout=2)
        return round(time.monotonic() - t, 3)

    def workflow(index):
        paths = [
            "/ready",
            "/api/v2/discovery",
            "/api/v2/discovery/historical",
            "/api/v2/discovery/stories",
            "/api/v2/datasets",
        ]
        if index % 6 == 5:
            return request(
                "/api/v2/compare",
                {
                    "datasets": ["cpi_nsa", "unemployment"],
                    "transformations": {"cpi_nsa": "yoy", "unemployment": "pp"},
                    "start": "2020-01-01",
                    "end": "2026-09-30",
                    "alignment": "native",
                    "rolling_window": 12,
                },
            )
        if index % 6 == 1:
            return request("/api/v2/discovery/refresh", {})
        return request(paths[index % 5])

    def successful(path):
        response = request(path)
        return response if response[0] == 200 else None

    def public_check():
        _, data = until(lambda: successful("/api/v2/datasets"))
        from backend.app.v2.definitions import SPECS

        assert len(data) == 30 and {d["id"] for d in data} == set(SPECS)
        for d in data:
            for k, v in json.loads(json.dumps(asdict(SPECS[d["id"]]))).items():
                assert d[k] == v, (d["id"], k)
        assert all(not d["id"].startswith("wb_") for d in data)
        checks["public_definitions_unchanged"] = True
        for pilot_id in [
            "wb_brent_monthly",
            "wb_copper_monthly",
            "wb_iron_ore_monthly",
        ]:
            code, _ = request(
                "/api/v2/compare",
                {"datasets": [pilot_id], "start": "2020-01-01", "end": "2026-09-30"},
            )
            assert code == 422
        _, ai = request("/api/v2/discovery/admin/generate", {}, True)
        assert ai.get("generated") == 0 and ai.get("fallback")
        assert not db_read(out, "SELECT * FROM ai_requests")
        _, radar = until(lambda: successful("/api/v2/discovery"))
        assert (
            "wb_brent_monthly" not in json.dumps(radar)
            and "wb_copper_monthly" not in json.dumps(radar)
            and "wb_iron_ore_monthly" not in json.dumps(radar)
        )
        checks["pilot_public_and_ai_exclusion"] = True

    def outcome(fault, state):
        before = len(runs())
        command(fault=fault)
        force_due()

        def reached():
            rows = runs()
            return (
                rows[-1] if len(rows) > before and rows[-1]["state"] == state else None
            )

        return until(reached, 30)

    try:
        command()
        spawn()
        emit("Staging backend started on loopback; no external provider or AI traffic.")
        if not disabled:
            finish_backfill()
            assert (
                db_read(out, "SELECT COUNT(*) n FROM ingest_observations")[0]["n"]
                == 2403
            )
            checks["full_backfill_2403"] = True
        public_check()
        saved = db_read(out, "SELECT id,snapshot FROM library LIMIT 1")
        assert saved, "Synthetic historical shock must exercise persisted research"
        saved_id = saved[0]["id"]
        saved_hash = sha256(saved[0]["snapshot"].encode()).hexdigest()
        db_write(
            out,
            "UPDATE library SET notes=? WHERE id=?",
            ("Phase4B synthetic saved note", saved_id),
        )
        phase[0] = "warm_concurrent_load"
        emit("Exercising simultaneous Discovery, comparisons, catalogue and ingestion.")
        if not disabled:
            force_due()
        with ThreadPoolExecutor(max_workers=6) as pool:
            responses = list(pool.map(lambda i: workflow(i)[0], range(36)))
        assert all(code in {200, 429, 503} for code in responses)
        checks["no_unhandled_http_500"] = True
        public_check()
        if os.getenv("MACROLENS_PHASE4C_PRESSURE") == "1":
            if sys.platform != "linux":
                raise RuntimeError("Memory pressure validation requires Linux")
            phase[0] = "memory_pressure"
            command(fault="normal")
            if not disabled:
                force_due()
            probe_args = [
                sys.executable,
                str(REPO / "scripts/validate_phase4c.py"),
                "--pressure-probe",
                str(out),
            ]
            if docker_image:
                probe_args = [
                    "docker",
                    "exec",
                    docker_name,
                    "python",
                    "scripts/validate_phase4c.py",
                    "--pressure-probe",
                    str(container_out),
                ]
            probe = subprocess.Popen(probe_args)
            try:
                deadline = time.monotonic() + 15
                while (
                    not (out / "pressure-ready").exists()
                    and probe.poll() is None
                    and time.monotonic() < deadline
                ):
                    time.sleep(0.1)
                checks["pressure_probe_completed"] = (out / "pressure-ready").exists()
                statuses = [request("/health")[0], request("/ready")[0]]
                for i in range(6):
                    code, _ = workflow(i)
                    assert code in {200, 429, 503}
                checks["pressure_api_live"] = statuses == [200, 200]
                probe.wait(timeout=15)
                time.sleep(0.5)
                checks["pressure_probe_completed"] = (
                    checks["pressure_probe_completed"] and probe.returncode == 0
                )
            finally:
                if probe.poll() is None:
                    probe.terminate()
                    probe.wait(timeout=5)
        if disabled:
            assert not runs() and not db_read(out, "SELECT * FROM ingest_datasets")
            checks["disabled_no_ingestion"] = True
            phase[0] = "disabled_idle"
            time.sleep(12)
        else:
            phase[0] = "normal_updates"
            original_count = db_read(out, "SELECT COUNT(*) n FROM ingest_observations")[
                0
            ]["n"]
            for _ in range(3):
                r = outcome("normal", "unchanged")
                assert r["inserted"] == r["revised"] == 0
            revised = outcome("revision", "complete")
            assert revised["revised"] == 1
            restored = outcome("normal", "complete")
            assert restored["revised"] == 1
            checks["live_revision_capture"] = True
            phase[0] = "provider_failure_recovery"
            success = db_read(out, "SELECT last_success FROM ingest_jobs")[0][
                "last_success"
            ]
            for fault in ["outage", "malformed", "unexpected"]:
                outcome(fault, "failed")
                assert (
                    db_read(out, "SELECT last_success FROM ingest_jobs")[0][
                        "last_success"
                    ]
                    == success
                )
                assert (
                    db_read(out, "SELECT COUNT(*) n FROM ingest_observations")[0]["n"]
                    == original_count
                )
                count = len(runs())
                time.sleep(2)
                assert len(runs()) == count, "Backoff was not respected"
                outcome("normal", "unchanged")
                success = db_read(out, "SELECT last_success FROM ingest_jobs")[0][
                    "last_success"
                ]
            checks["provider_failures_preserve_last_good_and_backoff"] = True
            command(discovery_failure=True)
            time.sleep(4)
            ready, _ = request("/ready")
            assert ready == 503
            outcome("normal", "unchanged")
            command(discovery_failure=False)
            until(lambda: request("/ready")[0] == 200, 30)
            checks["scheduler_recovers_and_ingestion_is_independent"] = True
            phase[0] = "shutdown_during_fetch"
            command(fault="slow")
            force_due()
            until(lambda: (out / "slow-entered").exists(), 15)
            result["active_shutdown_seconds"] = stop()
            assert (
                db_read(out, "SELECT COUNT(*) n FROM ingest_observations")[0]["n"]
                == 2403
            )
            checks["graceful_active_shutdown"] = True
            command(shutdown=False, fault="normal")
            phase[0] = "restart_and_crash_recovery"
            spawn()
            # Restarted normal jobs still respect durable state.
            assert db_read(out, "PRAGMA integrity_check")[0]["integrity_check"] == "ok"
            # Start an incremental full reconciliation, then interrupt the next slice.
            db_write(out, "UPDATE ingest_jobs SET last_full_check=0,next_due=0")
            until(
                lambda: (
                    db_read(out, "SELECT cursor FROM ingest_jobs")[0]["cursor"]
                    is not None
                ),
                30,
            )
            (out / "slow-entered").unlink(missing_ok=True)
            command(fault="slow")
            force_due()
            until(lambda: (out / "slow-entered").exists(), 15)
            active = db_read(out, "SELECT id FROM ingest_runs WHERE state='running'")
            assert active
            interrupted = active[0]["id"]
            stop(False)
            assert db_read(out, "PRAGMA integrity_check")[0]["integrity_check"] == "ok"
            command(shutdown=False, fault="normal")
            spawn()
            time.sleep(2)
            assert (
                db_read(
                    out, "SELECT state FROM ingest_runs WHERE id=?", (interrupted,)
                )[0]["state"]
                == "running"
            )
            # Accelerate only the expired-lease clock in this disposable test.
            db_write(
                out, "UPDATE leases SET expires_at=0 WHERE name='ingestion:world_bank'"
            )
            force_due()
            until(
                lambda: (
                    db_read(
                        out, "SELECT state FROM ingest_runs WHERE id=?", (interrupted,)
                    )[0]["state"]
                    == "abandoned"
                ),
                30,
            )
            finish_backfill()
            assert (
                db_read(out, "SELECT COUNT(*) n FROM ingest_observations")[0]["n"]
                == 2403
            )
            checks["abrupt_restart_integrity_cursor_and_lease_recovery"] = True
            # Preserve a real generated historical record/note across the process restart.
            kept = db_read(
                out, "SELECT snapshot,notes FROM library WHERE id=?", (saved_id,)
            )[0]
            assert sha256(kept["snapshot"].encode()).hexdigest() == saved_hash
            assert kept["notes"] == "Phase4B synthetic saved note"
            checks["historical_snapshot_and_note_preserved"] = True
            public_check()
            phase[0] = "default_60s_idle"
            command(interval=60)
            time.sleep(2)
            attempt = request("/ready")[1]["scheduler"]["last_attempt"]
            force_due()
            time.sleep(62)
            assert request("/ready")[1]["scheduler"]["last_attempt"] != attempt
            checks["actual_60s_scheduler_tick"] = True
        phase[0] = "shutdown"
        result["final_shutdown_seconds"] = stop()
        checks["sqlite_integrity"] = (
            db_read(out, "PRAGMA integrity_check")[0]["integrity_check"] == "ok"
        )
        assert checks["sqlite_integrity"]
        result["checks"] = checks
        result["fixture_observation_counts"] = json.loads(
            (out / "fixture-counts.json").read_text()
        )
        result["runs"] = runs()
        result["requests"] = requests_log
        result["samples"] = samples
        summaries = {}
        for name in sorted({x["phase"] for x in samples}):
            part = [x for x in samples if x["phase"] == name]
            duration = part[-1]["time"] - part[0]["time"]
            cpu = sum(
                max(0, b["cpu_seconds"] - a["cpu_seconds"])
                for a, b in itertools.pairwise(part)
                if a.get("instance", a["pid"]) == b.get("instance", b["pid"])
            )
            summaries[name] = {
                "samples": len(part),
                "duration_seconds": round(duration, 3),
                "max_rss_mib": round(max(x["rss"] for x in part) / 1048576, 2),
                "max_private_commit_mib": round(
                    max(x.get("private_commit", 0) for x in part) / 1048576, 2
                ),
                "cpu_seconds": round(cpu, 3),
                "mean_one_core_cpu_percent": round(cpu / duration * 100, 2)
                if duration
                else 0,
                "max_sqlite_family_mib": round(
                    max(x["sqlite_bytes"] for x in part) / 1048576, 3
                ),
            }
        result["summary"] = summaries
        if not disabled:
            assert summaries["default_60s_idle"]["samples"] >= 200
        else:
            assert summaries["disabled_idle"]["samples"] >= 40
        result["runtime"] = {
            "python": sys.version.split()[0],
            "sqlite": sqlite3.sqlite_version,
        }
        result["telemetry_max_age_seconds"] = round(
            max(x["time"] - x["sampled_at"] for x in samples), 3
        )
        result["status_counts"] = {
            str(code): sum(r["status"] == code for r in requests_log)
            for code in sorted({r["status"] for r in requests_log})
        }
        result["sqlite_tables"] = db_read(
            out, "SELECT name FROM sqlite_master WHERE type='table'"
        )
        result["final_disk_bytes"] = database_bytes(out)
        (out / "results.json").write_text(json.dumps(result, indent=2))
        emit(
            json.dumps(
                {
                    k: result[k]
                    for k in [
                        "mode",
                        "checks",
                        "summary",
                        "status_counts",
                        "final_disk_bytes",
                        "final_shutdown_seconds",
                    ]
                },
                indent=2,
            )
        )
    except Exception as exc:
        (out / "partial-results.json").write_text(
            json.dumps(
                {
                    "failure": type(exc).__name__,
                    "phase": phase[0],
                    "samples": samples,
                    "requests": requests_log,
                    "checks": checks,
                },
                indent=2,
            )
        )
        raise
    finally:
        stop_sampling.set()
        if docker_image:
            info = docker_inspect()
            if info and info["State"]["Running"]:
                subprocess.run(
                    ["docker", "kill", docker_name], check=False, capture_output=True
                )
                if child:
                    child.wait(timeout=10)
            record_docker()
        elif child and child.poll() is None:
            pid = int((out / "server-pid").read_text())
            assert pid > 1
            os.kill(pid, signal.SIGTERM if os.name == "nt" else signal.SIGKILL)
            child.wait(timeout=10)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path)
    p.add_argument("--workbook", type=Path)
    p.add_argument("--serve", type=Path)
    p.add_argument("--port", type=int)
    p.add_argument("--disabled", action="store_true")
    args = p.parse_args()
    if args.serve:
        serve(args.serve.resolve(), args.port, args.disabled)
    elif args.output and args.workbook:
        parent(args.output.resolve(), args.workbook.resolve(), args.disabled)
    else:
        p.error("Provide --output and --workbook")


if __name__ == "__main__":
    main()
