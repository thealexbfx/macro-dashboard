"""Phase 4B lifecycle regressions; disposable state only."""

from datetime import UTC, datetime
from hashlib import sha256
from threading import Event

from backend.app.ingestion.contracts import Batch, Point
from backend.app.ingestion.runner import Ingestion, IngestionWorker
from backend.app.ingestion.world_bank import PILOT
from backend.app.v2.state import Store


class ControlledAdapter:
    id = "world_bank"
    series = PILOT

    def __init__(self, entered=None, release=None):
        self.entered, self.release = entered, release

    def fetch(self):
        if self.entered:
            self.entered.set()
        if self.release:
            assert self.release.wait(3)
        return Batch(
            tuple(Point(s.id, "2026-01", 10.0) for s in PILOT),
            {
                s.id: {
                    "first_period": "2026-01",
                    "last_period": "2026-01",
                    "coverage_gaps": False,
                }
                for s in PILOT
            },
            sha256(b"fixture").hexdigest(),
            "https://example.invalid/fixture",
            datetime.now(UTC),
            100,
        )


def test_shutdown_does_not_commit_a_provider_result_after_stop(tmp_path):
    entered, release = Event(), Event()
    store = Store(tmp_path / "disposable.db")
    worker = IngestionWorker(store, enabled=True)
    worker._engine = Ingestion(store, [ControlledAdapter(entered, release)])
    worker.tick()
    try:
        assert entered.wait(2)
        worker.stop()
    finally:
        release.set()
        worker._future.result(timeout=3)
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM ingest_observations").fetchone()[0] == 0


def test_ingestion_dispatch_is_not_delayed_by_discovery_scan(monkeypatch):
    from backend.app.v2 import main

    dispatched = []
    monkeypatch.setattr(main.ingestion_worker, "tick", lambda: dispatched.append(True))

    def scan(**kwargs):
        assert dispatched, "Ingestion must start before potentially slow Discovery"

    monkeypatch.setattr(main.discovery_service, "get", scan)
    main.background_refresh()


def test_adapter_cancellation_precedes_cache_and_workbook_parsing():
    from unittest.mock import Mock

    import pytest

    from backend.app.ingestion.contracts import ProviderError
    from backend.app.ingestion.world_bank import WorldBank

    cancelled = Event()
    response = Mock(status_code=200, headers={})
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)

    def chunks(_size):
        cancelled.set()
        yield b"not a workbook"

    response.iter_content = chunks
    session = Mock()
    session.get.return_value = response
    provider = WorldBank(session=session, cancel_event=cancelled)
    with pytest.raises(ProviderError, match="cancelled"):
        provider.fetch()
    provider._cached = object()
    provider._expires = float("inf")
    with pytest.raises(ProviderError, match="cancelled"):
        provider.fetch()


def test_optional_dispatch_failure_does_not_break_discovery(monkeypatch):
    from unittest.mock import Mock

    from backend.app.v2 import main

    monkeypatch.setattr(
        main.ingestion_worker, "tick", Mock(side_effect=RuntimeError("synthetic"))
    )
    discovery = Mock(return_value={"ok": True})
    monkeypatch.setattr(main.discovery_service, "get", discovery)
    assert main.background_refresh() == {"ok": True}
    discovery.assert_called_once_with(force_check=True)


def test_database_write_contention_is_bounded_and_worker_recovers(tmp_path):
    import time

    store = Store(tmp_path / "contention.db")
    worker = IngestionWorker(store, enabled=True)
    worker._engine = Ingestion(store, [ControlledAdapter()])
    try:
        with store.connection(True) as db:
            db.execute("INSERT INTO counters VALUES ('uncommitted-fixture',1)")
            start = time.monotonic()
            worker.tick()
            worker._future.result(timeout=5)
            assert time.monotonic() - start < 4
            assert worker.error_code == "worker_error"
            # WAL readers remain usable while the other writer is held.
            with store.connection(timeout=1) as reader:
                assert (
                    reader.execute(
                        "SELECT COUNT(*) FROM ingest_observations"
                    ).fetchone()[0]
                    == 0
                )
        worker.tick()
        worker._future.result(timeout=3)
        assert worker.error_code is None
        assert worker._engine.status()["observations"] == 3
    finally:
        worker.stop()


def test_worker_restart_uses_a_fresh_cancellation_token(tmp_path, monkeypatch):
    from backend.app.ingestion import world_bank

    monkeypatch.setattr(world_bank, "WorldBank", lambda **kwargs: ControlledAdapter())
    worker = IngestionWorker(Store(tmp_path / "restart.db"), enabled=True)
    try:
        worker.tick()
        worker._future.result(timeout=3)
        old = worker._cancel
        worker.stop()
        assert old.is_set()
        worker.start()
        worker.tick()
        worker._future.result(timeout=3)
        assert worker._cancel is not old and not worker._cancel.is_set()
        assert worker.error_code is None
    finally:
        worker.stop()


def test_all_three_pilot_ids_rejected_by_public_compare_and_ai_stays_off(
    tmp_path, monkeypatch
):
    from unittest.mock import Mock

    from fastapi.testclient import TestClient

    from backend.app.v2 import ai_guard, main
    from backend.app.v2.ai_guard import AIGuard
    from backend.app.v2.definitions import SPECS

    monkeypatch.setenv("MACROLENS_AI_ENABLED", "false")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    send = Mock(side_effect=AssertionError("No AI call permitted"))
    monkeypatch.setattr(ai_guard, "send", send)
    store = Store(tmp_path / "denied.db")
    guard = AIGuard(store)
    client = TestClient(main.app)
    for spec in PILOT:
        assert spec.id not in SPECS
        response = client.post(
            "/api/v2/compare",
            json={"datasets": [spec.id], "start": "2020-01-01", "end": "2025-01-01"},
        )
        assert response.status_code == 422
        assert guard.generate([{"datasets": [spec.id]}])["generated"] == 0
    send.assert_not_called()
    with store.connection() as db:
        assert db.execute("SELECT COUNT(*) FROM ai_requests").fetchone()[0] == 0


def test_additive_upgrade_and_old_queries_preserve_all_existing_research(tmp_path):
    import sqlite3

    from backend.app.v2.state import SCHEMA

    path = tmp_path / "legacy.sqlite3"
    legacy = sqlite3.connect(path)
    legacy.executescript(SCHEMA)
    legacy.execute(
        "INSERT INTO source_cache VALUES (?,?,?,?,?)",
        ("cpi", '{"fixture":true}', "2026-01-01", "2027-01-01", 0),
    )
    legacy.execute(
        "INSERT INTO library VALUES (?,?,?,?,?)",
        ("saved", "synthetic note", "2026-01-01", "{}", "retain"),
    )
    legacy.execute(
        "INSERT INTO stories VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "story",
            "event",
            "2026-01-01",
            "2026-01-01",
            "2026-01-01",
            "2026-01-01",
            "Archived",
            1,
            "{}",
            "hash",
            "fixture",
            "[]",
        ),
    )
    legacy.execute(
        "INSERT INTO story_versions VALUES (?,?,?,?,?)",
        ("story", 1, "2026-01-01", "fixture", "{}"),
    )
    legacy.execute(
        "INSERT INTO reports VALUES (?,?,?,?)",
        ("current", "fingerprint", "{}", "2026-01-01"),
    )
    legacy.commit()
    tables = ["source_cache", "library", "stories", "story_versions", "reports"]
    before = {t: legacy.execute("SELECT * FROM " + t).fetchall() for t in tables}
    with sqlite3.connect(tmp_path / "backup.sqlite3") as backup:
        legacy.backup(backup)
    legacy.close()
    upgraded = Store(path)
    upgraded.probe()
    Ingestion(upgraded, [ControlledAdapter()]).run_once()
    with upgraded.connection() as db:
        after = {
            t: [tuple(r) for r in db.execute("SELECT * FROM " + t)] for t in tables
        }
        assert before == after
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert (
            len(
                db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ingest_%'"
                ).fetchall()
            )
            == 5
        )
    with sqlite3.connect(tmp_path / "backup.sqlite3") as backup:
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert backup.execute("SELECT notes FROM library").fetchone()[0] == "retain"


def test_capacity_check_tolerates_disappearing_wal(tmp_path, monkeypatch):
    from pathlib import Path

    store = Store(tmp_path / "capacity.db")
    engine = Ingestion(store, [ControlledAdapter()])
    wal = Path(str(store.path) + "-wal")
    wal.write_bytes(b"synthetic")
    original = Path.stat
    calls = [0]

    def disappear(path, *args, **kwargs):
        if path == wal:
            calls[0] += 1
            if calls[0] > 1:
                raise FileNotFoundError("Synthetic checkpoint removes sidecar")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", disappear)
    try:
        engine._capacity()
        engine._capacity()
    finally:
        wal.unlink(missing_ok=True)
