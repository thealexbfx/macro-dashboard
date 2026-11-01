"""Disposable-only automatic native ingestion and privacy regressions."""

import io
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Event
from urllib.error import HTTPError

import pytest

from backend.app.catalog.release_cli import ingest
from backend.app.catalog.releases import activate, candidates, migrate as releases
from backend.app.ingestion.catalog_refresh import (
    CatalogRefresh,
    CatalogRefreshWorker,
    migrate,
    policy,
)
from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.native import Observation
from backend.app.ingestion.official_snapshots import download, freeze
from backend.app.ingestion.partition_schema import migrate as native
from backend.app.v2.native_reader import NativeReader
from backend.app.v2.state import Store

ID = "ons_27271ab0b950200f5401"


def setup(tmp_path, *, mode="refresh"):
    store = Store(tmp_path / "disposable.sqlite3")
    pub = candidates()[ID]
    with store.connection(True) as db:
        native(db)
        releases(db)
        migrate(db)
        db.execute(
            "INSERT INTO library VALUES('saved','Saved research','2020-01-01','{}','preserve')"
        )
    path, key = freeze(
        tmp_path / "initial",
        pub.definition,
        (Observation("2020-01", "2020 JAN", -2.0),),
        b"initial",
        pub.source_url,
    )
    assert ingest(store, pub, path, key)["state"] == "complete"
    reader = NativeReader(store.path)
    if mode == "refresh":
        with store.connection(True) as db:
            activate(db, pub, reader, approved=True)
    config = tmp_path / "policy.json"
    config.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "id": ID,
                        "mode": mode,
                        "ingest_approved": True,
                        "automation_ready": True,
                        "check_seconds": 86400,
                    }
                ]
            }
        )
    )
    clock = [datetime.now(UTC)]
    calls = []
    result = [body([-2, 0, None])]

    def fetch(url, **kwargs):
        calls.append((url, kwargs))
        if isinstance(result[0], Exception):
            raise result[0]
        return result[0], {
            "etag": '"fixture"',
            "last_modified": "Wed, 01 Jan 2020 00:00:00 GMT",
        }

    worker = CatalogRefresh(store, config=config, now=lambda: clock[0], fetch=fetch)
    return store, worker, reader, clock, result, calls


def body(values, *, unit="%"):
    return json.dumps(
        {
            "description": {
                "cdid": "D7G7",
                "unit": unit,
                "releaseDate": "2020-05-20T00:00:00Z",
            },
            "months": [
                {"date": "2020 " + month, "value": "" if v is None else str(v)}
                for month, v in zip(["JAN", "FEB", "MAR", "APR"], values)
            ],
        }
    ).encode()


def due(store, clock):
    clock[0] += timedelta(days=1)
    with store.connection(True) as db:
        db.execute("UPDATE catalog_refresh_jobs SET next_due=0")


def test_defaults_and_disabled_worker_never_initialize_or_schedule(tmp_path):
    assert policy() == {}
    store = Store(tmp_path / "must-not-exist.sqlite3")
    w = CatalogRefreshWorker(store)
    w.start()
    w.tick()
    w.stop()
    assert not store.path.exists() and w.pool is None


def test_new_revision_unchanged_and_permissions(tmp_path):
    store, w, reader, clock, result, calls = setup(tmp_path)
    with store.connection() as db:
        grants = [tuple(r) for r in db.execute("SELECT * FROM catalog_release_grants")]
    assert w.run_once()["state"] == "changed"
    assert [
        x["value"]
        for x in reader.observations(ID, date(2020, 1, 1), date(2020, 4, 1))["dataset"][
            "observations"
        ]
    ] == [-2, 0, None]
    assert w.run_once()["state"] == "idle"
    due(store, clock)
    result[0] = body([-3, 0, None, 4])
    assert w.run_once()["state"] == "changed"
    with store.connection() as db:
        assert db.execute("SELECT count(*) FROM norm_revisions").fetchone()[0] == 1
        count = db.execute("SELECT count(*) FROM norm_generations").fetchone()[0]
        assert [
            tuple(r) for r in db.execute("SELECT * FROM catalog_release_grants")
        ] == grants
        assert (
            db.execute(
                "SELECT count(*) FROM catalog_scope_reviews WHERE scope IN ('ai','discovery') AND approved=1"
            ).fetchone()[0]
            == 0
        )
        assert db.execute("SELECT notes FROM library").fetchone()[0] == "preserve"
    due(store, clock)
    assert w.run_once()["state"] == "unchanged"
    assert calls[-1][1]["validators"]["etag"] == '"fixture"'
    with store.connection() as db:
        assert (
            db.execute("SELECT count(*) FROM norm_generations").fetchone()[0] == count
        )
        assert (
            db.execute(
                "SELECT failures,last_change,last_success FROM catalog_refresh_jobs"
            ).fetchone()[0]
            == 0
        )
    assert not list(w.directory.glob("*.json"))


@pytest.mark.parametrize(
    "failure",
    [
        ProviderError("http_503"),
        ProviderError("http_429"),
        RuntimeError("never log secret"),
    ],
)
def test_failure_recovery_and_restart(tmp_path, failure, caplog):
    store, w, reader, clock, result, calls = setup(tmp_path)
    result[0] = failure
    assert w.run_once()["state"] == "failed"
    assert reader.metadata(ID)["id"] == ID
    assert "never log secret" not in caplog.text
    assert w.run_once()["state"] == "idle"
    result[0] = body([-2, 0, None])
    due(store, clock)
    restarted = CatalogRefresh(
        store, config=w.rules and tmp_path / "policy.json", fetch=w.fetch, now=w.now
    )
    assert restarted.run_once()["state"] == "changed"
    assert restarted.status()[0]["failures"] == 0


@pytest.mark.parametrize(
    "payload,code",
    [
        (body([-2], unit="GBP"), "definition_drift"),
        (b"<html>not data</html>", "invalid_source"),
        (body([]), "empty_or_oversized_history"),
        (body([None, 0]), "unexplained_value_loss"),
    ],
)
def test_bad_sources_preserve_last_good(tmp_path, payload, code):
    _, w, reader, _, result, _ = setup(tmp_path)
    result[0] = payload
    assert w.run_once()["error_code"] == code
    assert (
        reader.observations(ID, date(2020, 1, 1), date(2020, 4, 1))["dataset"][
            "observations"
        ][0]["value"]
        == -2
    )


def test_truncation_is_rejected_even_if_source_looks_valid(tmp_path):
    store, w, _, clock, result, _ = setup(tmp_path)
    assert w.run_once()["state"] == "changed"
    due(store, clock)
    result[0] = body([-2])
    assert w.run_once()["error_code"] == "history_omitted"


def test_different_response_bytes_same_observations_do_not_make_generation(tmp_path):
    store, w, _, clock, result, _ = setup(tmp_path)
    assert w.run_once()["state"] == "changed"
    with store.connection() as db:
        count = db.execute("SELECT count(*) FROM norm_generations").fetchone()[0]
    due(store, clock)
    result[0] += b" \n"
    assert w.run_once()["state"] == "unchanged"
    with store.connection() as db:
        assert (
            db.execute("SELECT count(*) FROM norm_generations").fetchone()[0] == count
        )


def test_stage_mode_does_not_publish_and_cannot_touch_world_bank(tmp_path):
    store, w, reader, _, _, _ = setup(tmp_path, mode="stage")
    assert w.run_once()["state"] == "changed"
    with pytest.raises(ValueError):
        reader.metadata(ID)
    cfg = json.loads((tmp_path / "policy.json").read_text())
    cfg["datasets"][0]["id"] = "wb_brent_monthly"
    (tmp_path / "bad.json").write_text(json.dumps(cfg))
    with pytest.raises(ValueError):
        policy(tmp_path / "bad.json")
    with store.connection() as db:
        assert (
            db.execute("SELECT count(*) FROM catalog_release_grants").fetchone()[0] == 0
        )


def test_refresh_permission_revocation_prevents_fetch(tmp_path):
    store, w, _, _, _, calls = setup(tmp_path)
    with store.connection(True) as db:
        db.execute("UPDATE catalog_release_grants SET public_display=0")
    assert w.run_once()["state"] == "failed"
    assert not calls


def test_database_writer_contention_defers_without_reset(tmp_path):
    store, w, reader, clock, _, _ = setup(tmp_path)
    other = sqlite3.connect(store.path, isolation_level=None)
    other.execute("BEGIN IMMEDIATE")
    try:
        assert w.run_once()["state"] == "failed"
        assert reader.metadata(ID)["id"] == ID
    finally:
        other.rollback()
        other.close()
    due(store, clock)
    assert w.run_once()["state"] == "changed"


def test_single_worker_admission_across_instances(tmp_path):
    store, w, _, _, _, _ = setup(tmp_path)
    entered, release = Event(), Event()
    fetch = w.fetch

    def slow(*a, **kw):
        entered.set()
        assert release.wait(10)
        return fetch(*a, **kw)

    w.fetch = slow
    other = CatalogRefresh(store, config=tmp_path / "policy.json")
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(w.run_once)
        assert entered.wait(10)
        assert other.run_once()["state"] == "busy"
        release.set()
        assert future.result()["state"] == "changed"


def test_conditional_304_and_header_validation():
    class Opener:
        def open(self, request, timeout):
            assert request.get_header("If-none-match") == '"safe"'
            raise HTTPError(request.full_url, 304, "Not modified", {}, io.BytesIO())

    raw, headers = download(
        "https://www.ons.gov.uk/example", validators={"etag": '"safe"'}, opener=Opener()
    )
    assert raw is None and headers["not_modified"]
    with pytest.raises(ValueError):
        download(
            "https://www.ons.gov.uk/example",
            validators={"etag": "bad\r\nInjected: x"},
            opener=Opener(),
        )


def test_explicit_migration_idempotent_and_restore(tmp_path):
    store, _, _, _, _, _ = setup(tmp_path)
    with store.connection(True) as db:
        migrate(db)
        assert (
            db.execute(
                "SELECT count(*) FROM catalog_schema_versions WHERE version=4"
            ).fetchone()[0]
            == 1
        )
    restored = sqlite3.connect(tmp_path / "restore.sqlite3")
    with store.connection() as db:
        db.backup(restored)
    assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert restored.execute("SELECT notes FROM library").fetchone()[0] == "preserve"
    restored.close()
