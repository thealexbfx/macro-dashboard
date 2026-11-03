"""Production-readiness regressions. All state is disposable; no paid/provider calls."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from threading import Event
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.v2 import main as v
from backend.app.v2 import runtime as rt
from backend.app.v2.definitions import SPECS
from backend.app.v2.history import evidence_start, similarity
from backend.app.v2.refresh import scheduled_service_class
from backend.app.v2.request_bounds import RequestBounds
from backend.app.v2.scheduler import RefreshScheduler
from backend.app.v2.state import Store, dumps
from backend.app.v2.workload import WorkloadBusy, WorkloadLimit

NOW = datetime(2026, 10, 26, 12, tzinfo=UTC)


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    dates = pd.date_range(end="2026-09-01", periods=200, freq="MS")
    rng = np.random.default_rng(27)
    change = rng.normal(0.2, 0.15, 200)
    change[-1] = 4
    values = 100 * np.cumprod(1 + change / 100)
    d = v.Dataset(
        **asdict(SPECS["cpi"]),
        status="ok",
        message="fixture",
        observations=[
            v.Observation(date=str(t.date()), value=float(x))
            for t, x in zip(dates, values)
        ],
        latest_observation_date=str(dates[-1].date()),
        retrieved_at=NOW.isoformat(),
        verification={"status": "Calculation verified"},
    )
    store = Store(tmp_path / "state.db")
    with store.connection(True) as db:
        db.execute(
            "INSERT INTO source_cache VALUES (?,?,?,?,?)",
            (
                "cpi",
                dumps(d.model_dump()),
                NOW.isoformat(),
                (NOW + timedelta(days=1)).isoformat(),
                0,
            ),
        )

    class Offline:
        def fred_series(self, *_):
            raise AssertionError("No network")

    svc = scheduled_service_class(v.DataService, v.Dataset)(
        store, provider=Offline(), today_fn=lambda: NOW.date(), now_fn=lambda: NOW
    )
    monkeypatch.setattr(rt, "SPECS", {"cpi": SPECS["cpi"]})
    return rt.DynamicDiscovery(svc, v.transform, store, workload=WorkloadLimit())


def archive50(runtime):
    initial = runtime.get()
    with runtime.store.connection(True) as db:
        original = db.execute("SELECT * FROM stories LIMIT 1").fetchone()
        for i in range(50):
            row = list(original)
            row[0] = f"archive-{i:03d}"
            row[1] = f"archive-key-{i:03d}"
            row[6] = "Archived"
            db.execute("INSERT INTO stories VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row)
            db.execute(
                "INSERT INTO story_versions VALUES (?,?,?,?,?)",
                (row[0], row[7], row[3], "Archive fixture", row[8]),
            )
    return initial


def snapshots(runtime):
    with runtime.store.connection() as db:
        return [
            tuple(r)
            for r in db.execute(
                "SELECT id,version,snapshot,evidence_hash FROM stories ORDER BY id"
            )
        ], [
            tuple(r)
            for r in db.execute(
                "SELECT * FROM story_versions ORDER BY story_id,version"
            )
        ]


def test_50_archives_do_not_expand_main_response_or_trigger_unchanged_analysis(
    runtime, monkeypatch
):
    initial = archive50(runtime)
    original = snapshots(runtime)
    suggestions = Mock(
        side_effect=AssertionError(
            "Unchanged/archive-only change must not recalculate suggestions"
        )
    )
    monkeypatch.setattr(rt, "suggestions", suggestions)
    monkeypatch.setattr(
        rt, "scan", Mock(side_effect=AssertionError("No numerical change"))
    )
    report = runtime.get(force_check=True)
    assert report["archived"] == [] and report["archived_total"] == 50
    assert len(json.dumps(report)) <= len(json.dumps(initial)) + 512
    assert [(f["id"], f["evidence_version"]) for f in report["findings"]] == [
        (f["id"], f["evidence_version"]) for f in initial["findings"]
    ]
    assert (
        report["generated_at"] == initial["generated_at"]
        and snapshots(runtime) == original
    )
    assert runtime.get() == report and suggestions.call_count == 0


def test_archive_pagination_and_on_demand_evidence_preserve_snapshots(runtime):
    archive50(runtime)
    before = snapshots(runtime)
    ids = []
    for offset in [0, 20, 40]:
        page = runtime.summaries(limit=20, offset=offset)
        assert page["total"] == 50 and len(page["items"]) <= 20
        assert all("evidence" not in r and "snapshot" not in r for r in page["items"])
        ids.extend(r["id"] for r in page["items"])
    assert len(set(ids)) == 50
    detail = runtime.story(ids[0])
    assert detail["lifecycle"]["status"] == "Archived" and detail["suggestions"] == []
    original = json.loads(next(r[2] for r in before[0] if r[0] == ids[0]))
    assert (
        detail["evidence"] == original["evidence"]
        and detail["configuration"] == original["configuration"]
    )
    assert snapshots(runtime) == before and runtime.story("missing") is None


def test_cached_report_does_not_read_full_source_payloads(runtime, monkeypatch):
    first = runtime.get()
    monkeypatch.setattr(
        runtime.data_service,
        "get",
        Mock(side_effect=AssertionError("No source revalidation during cache TTL")),
    )
    assert runtime.get() == first and runtime.get(force_check=True) == first


def test_due_source_invalidates_short_cache_without_bypassing_due_rules(runtime):
    first = runtime.get()
    runtime._expires = 0
    with runtime.store.connection(True) as db:
        db.execute(
            "UPDATE source_cache SET next_due=?",
            ((NOW - timedelta(seconds=1)).isoformat(),),
        )
    provider = Mock()
    provider.fred_series.side_effect = RuntimeError("offline")
    runtime.data_service.provider = provider
    report = runtime.get(force_check=True)
    assert provider.fred_series.call_count == 1
    assert report["source_times"][0]["status"] == "stale"
    assert not report["findings"] and first["findings"]
    runtime.get(force_check=True)
    assert provider.fred_series.call_count == 1


def test_rejected_manual_cooldown_uses_cached_report(runtime, monkeypatch):
    runtime.manual()
    monkeypatch.setattr(
        runtime,
        "_build",
        Mock(side_effect=AssertionError("No repeated work during cooldown")),
    )
    assert not runtime.manual()["manual_refresh"]["accepted"]


def test_expensive_work_is_rejected_without_queue_and_capacity_recovers(runtime):
    with runtime.workload.enter(), pytest.raises(WorkloadBusy):
        runtime.get(force_check=True)
    assert runtime.get()["findings"]


def test_scheduler_survives_unexpected_exception_and_recovers(caplog):
    done = Event()
    calls = []

    def target():
        calls.append(1)
        if len(calls) == 1:
            raise TypeError("synthetic-sensitive-detail")
        done.set()

    scheduler = RefreshScheduler(target, interval=0.01)
    scheduler.start()
    try:
        assert done.wait(2)
        assert scheduler.status()["thread_alive"]
        # run_once completes after target returns; acquire its diagnostic lock through status.
        scheduler.run_once()
        status = scheduler.status()
        assert (
            status["last_attempt"] and status["last_success"] and status["last_failure"]
        )
        assert (
            status["heartbeat"]
            and status["consecutive_failures"] == 0
            and status["ready"]
        )
        assert (
            "TypeError" in caplog.text
            and "synthetic-sensitive-detail" not in caplog.text
        )
    finally:
        scheduler.stop()
    assert not scheduler.status()["thread_alive"]


def test_scheduler_failure_diagnostics_and_busy_skip():
    scheduler = RefreshScheduler(
        lambda: (_ for _ in ()).throw(TypeError("private")), now_fn=lambda: NOW
    )
    scheduler.run_once()
    s = scheduler.status()
    assert (
        s["error_type"] == "TypeError"
        and s["consecutive_failures"] == 1
        and s["last_success"] is None
    )
    scheduler.target = lambda: (_ for _ in ()).throw(WorkloadBusy())
    scheduler.run_once()
    assert scheduler.status()["skipped_busy"] == 1
    scheduler.target = lambda: None
    scheduler.run_once()
    assert (
        scheduler.status()["last_success"] == NOW.isoformat()
        and scheduler.status()["error_type"] is None
    )


def test_readiness_checks_database_and_scheduler_without_provider_calls(
    tmp_path, monkeypatch
):
    store = Store(tmp_path / "ready.db")
    monkeypatch.setattr(v, "state_store", store)
    scheduler = Mock()
    scheduler.status.return_value = {"ready": True, "thread_alive": True}
    monkeypatch.setattr(v, "refresh_scheduler", scheduler)
    monkeypatch.setattr(
        v.service.provider,
        "fred_series",
        Mock(side_effect=AssertionError("Readiness must not call providers")),
    )
    client = TestClient(v.app)
    assert client.get("/ready").status_code == 200
    scheduler.status.return_value = {"ready": False, "thread_alive": False}
    assert client.get("/ready").status_code == 503
    monkeypatch.setattr(
        store,
        "probe",
        Mock(side_effect=sqlite3.OperationalError("private database detail")),
    )
    r = client.get("/ready")
    assert r.status_code == 503 and "private" not in r.text
    assert client.get("/health").status_code == 200


def test_admin_headers_no_store_body_limits_and_heavy_capacity(monkeypatch):
    monkeypatch.setenv("MACROLENS_ADMIN_TOKEN", "configured-fixture")
    client = TestClient(v.app)
    fake = "Bearer synthetic-not-a-real-token"
    for method, path in [
        ("GET", "usage"),
        ("GET", "diagnostics"),
        ("POST", "generate"),
    ]:
        r = client.request(
            method, "/api/v2/discovery/admin/" + path, headers={"Authorization": fake}
        )
        assert r.status_code == 403 and r.headers["cache-control"] == "no-store"
        assert all(fake not in value for value in r.headers.values())
    r = client.post("/api/v2/compare", content=b"x" * 65537)
    assert r.status_code == 413
    with v.analytical_workload.enter():
        r = client.post(
            "/api/v2/compare",
            json={"datasets": ["gold"], "start": "2024-01-01", "end": "2024-12-31"},
        )
        assert r.status_code == 503 and r.headers["retry-after"] == "2"
        assert client.get("/health").status_code == 200


def test_stale_lease_cache_is_reassessed(tmp_path):
    store = Store(tmp_path / "lease.db")
    d = v.Dataset(
        **asdict(SPECS["unemployment"]),
        status="ok",
        message="fixture",
        latest_observation_date="2010-01-01",
        observations=[v.Observation(date="2010-01-01", value=4)],
    )
    with store.connection(True) as db:
        db.execute(
            "INSERT INTO source_cache VALUES (?,?,?,?,?)",
            (
                "unemployment",
                dumps(d.model_dump()),
                NOW.isoformat(),
                (NOW - timedelta(seconds=1)).isoformat(),
                0,
            ),
        )
    assert store.acquire("source:unemployment", "other-worker", NOW.timestamp(), 120)
    cls = scheduled_service_class(v.DataService, v.Dataset)
    svc = cls(store, today_fn=lambda: NOW.date(), now_fn=lambda: NOW)
    assert svc.get("unemployment").status == "stale"


@pytest.mark.parametrize(
    "frequency,size,shift,cycle", [("MS", 24, 12, 12), ("QS", 16, 4, 4)]
)
def test_consistent_overlapping_evidence_is_rejected(frequency, size, shift, cycle):
    rng = np.random.default_rng(18)
    data = np.tile(rng.normal(size=cycle), 10)
    dates = pd.date_range("2020-01-01", periods=len(data), freq=frequency)

    def p(start):
        return {
            "required": size,
            "observations": [
                {"date": str(t.date()), "value": float(x)}
                for t, x in zip(dates[start : start + size], data[start : start + size])
            ],
        }

    result = similarity(p(0), p(shift))
    assert not result["matches"] and "overlap" in result["reason"]


def test_nonoverlapping_monthly_pattern_can_still_match():
    rng = np.random.default_rng(8)
    x = rng.normal(size=24)

    def p(year):
        return {
            "required": 24,
            "observations": [
                {"date": str(t.date()), "value": float(v)}
                for t, v in zip(
                    pd.date_range(f"{year}-01-01", periods=24, freq="MS"), x
                )
            ],
        }

    assert similarity(p(2008), p(2024))["matches"]
    before = p(2008)
    current = p(2010)
    current["evidence_start"] = "2009-01-01"
    assert not similarity(before, current)["matches"]


def test_session_lookback_uses_actual_holiday_positions():
    d = v.Dataset(
        **asdict(SPECS["sp500"]),
        status="ok",
        message="fixture",
        latest_observation_date="2026-07-07",
        observations=[
            v.Observation(date=t, value=x)
            for t, x in [
                ("2026-07-01", 100),
                ("2026-07-02", 101),
                ("2026-07-06", 102),
                ("2026-07-07", 103),
            ]
        ],
    )
    assert evidence_start(d, 1, "percent", "2026-07-06") == "2026-07-02"


def test_public_pagination_validation_and_missing_story(runtime, monkeypatch):
    archive50(runtime)
    monkeypatch.setattr(v, "discovery_service", runtime)
    client = TestClient(v.app)
    r = client.get("/api/v2/discovery/stories?limit=20&offset=40")
    assert r.status_code == 200 and len(r.json()["items"]) == 10
    assert client.get("/api/v2/discovery/stories?limit=100").status_code == 422
    assert client.get("/api/v2/discovery/stories?offset=-1").status_code == 422
    assert client.get("/api/v2/discovery/stories?state=invalid").status_code == 422
    assert client.get("/api/v2/discovery/stories/missing").status_code == 404


def test_disabled_ai_stays_disabled_with_valid_fixture_admin(monkeypatch):
    monkeypatch.setenv("MACROLENS_ADMIN_TOKEN", "fixture-admin")
    monkeypatch.setenv("MACROLENS_AI_ENABLED", "false")
    monkeypatch.setattr(v, "discovery_service", Mock(get=lambda: {"findings": []}))
    monkeypatch.setattr(
        v.ai_guard, "send_fn", Mock(side_effect=AssertionError("No paid call"))
    )
    r = TestClient(v.app).post(
        "/api/v2/discovery/admin/generate",
        headers={"Authorization": "Bearer fixture-admin"},
    )
    assert (
        r.status_code == 200
        and r.json()["fallback"]
        and r.headers["cache-control"] == "no-store"
    )
    v.ai_guard.send_fn.assert_not_called()


def test_http_admission_limit_and_chunked_body_bound():
    async def run():
        entered = asyncio.Event()
        release = asyncio.Event()
        messages = []

        async def app(scope, receive, send):
            entered.set()
            await release.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        middleware = RequestBounds(app, max_inflight=1)
        scope = {"type": "http", "path": "/api/v2/discovery", "method": "GET"}
        first = asyncio.create_task(middleware(scope, receive, send))
        await entered.wait()
        await middleware(scope, receive, send)
        assert any(m.get("status") == 429 for m in messages)
        release.set()
        await first
        assert middleware.inflight == 0
        called = []
        messages.clear()

        async def forbidden(*_):
            called.append(1)

        chunks = iter(
            [
                {"type": "http.request", "body": b"x" * 40000, "more_body": True},
                {"type": "http.request", "body": b"x" * 40000, "more_body": False},
            ]
        )

        async def chunked():
            return next(chunks)

        await RequestBounds(forbidden)(
            {
                "type": "http",
                "path": "/api/v2/compare",
                "method": "POST",
                "headers": [],
            },
            chunked,
            send,
        )
        assert not called and any(m.get("status") == 413 for m in messages)

    asyncio.run(run())


def test_lifespan_starts_and_stops_refresh_with_persistent_state(tmp_path, monkeypatch):
    store = Store(tmp_path / "lifespan.db")
    completed = Event()
    scheduler = RefreshScheduler(completed.set, interval=0.01)
    monkeypatch.setattr(v, "state_store", store)
    monkeypatch.setattr(v, "refresh_scheduler", scheduler)
    with TestClient(v.app) as client:
        assert completed.wait(2) and scheduler.status()["thread_alive"]
        assert client.get("/ready").status_code == 200
    assert not scheduler.status()["thread_alive"]
    assert Store(store.path).probe()


def test_repeated_engine_failure_is_unready_and_success_recovers():
    from types import SimpleNamespace

    scheduler = RefreshScheduler(
        lambda: (_ for _ in ()).throw(TypeError("private")), now_fn=lambda: NOW
    )
    scheduler.thread = SimpleNamespace(is_alive=lambda: True)
    for _ in range(3):
        scheduler.run_once()
    assert (
        not scheduler.status()["ready"]
        and scheduler.status()["consecutive_failures"] == 3
    )
    # Provider unavailability represented as data is not an engine/readiness failure.
    scheduler.target = lambda: {"source_status": "unavailable"}
    scheduler.run_once()
    assert scheduler.status()["ready"]


def test_slow_body_timeout_releases_capacity():
    async def run():
        called = []
        messages = []

        async def app(*_):
            called.append(1)

        async def receive():
            await asyncio.sleep(1)

        async def send(m):
            messages.append(m)

        middleware = RequestBounds(app, body_timeout=0.01)
        await middleware(
            {
                "type": "http",
                "path": "/api/v2/compare",
                "method": "POST",
                "headers": [],
            },
            receive,
            send,
        )
        assert (
            not called
            and middleware.inflight == 0
            and any(m.get("status") == 408 for m in messages)
        )

    asyncio.run(run())


def test_weekly_lookback_retains_changed_source_weekday_labels():
    d = v.Dataset(
        **asdict(SPECS["mortgage_30y"]),
        status="ok",
        message="fixture",
        latest_observation_date="2026-01-08",
        observations=[
            v.Observation(date=t, value=4) for t in ["2026-01-02", "2026-01-08"]
        ],
    )
    assert evidence_start(d, 1, "pp", "2026-01-08") == "2026-01-02"


def test_other_worker_source_revision_invalidates_cached_analysis(runtime):
    first = runtime.get()
    runtime._expires = 0
    with runtime.store.connection(True) as db:
        row = db.execute("SELECT payload FROM source_cache WHERE id='cpi'").fetchone()
        d = json.loads(row[0])
        d["observations"][-1]["value"] *= 1.05
        db.execute(
            "UPDATE source_cache SET payload=?,checked_at=? WHERE id=?",
            (dumps(d), (NOW + timedelta(seconds=1)).isoformat(), "cpi"),
        )
    second = runtime.get(force_check=True)
    assert second["snapshot_fingerprint"] != first["snapshot_fingerprint"]
    assert runtime.get()["snapshot_fingerprint"] == second["snapshot_fingerprint"]
