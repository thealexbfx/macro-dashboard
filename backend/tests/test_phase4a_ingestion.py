"""Offline regressions: disposable SQLite and synthetic XLSX, no paid/live dependencies."""

import json
import sqlite3
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
from xml.sax.saxutils import escape
from zipfile import ZipFile

import pytest
import requests

from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.runner import Ingestion, IngestionWorker
from backend.app.ingestion.world_bank import PILOT, WorldBank, parse_workbook
from backend.app.v2.state import Store

NOW = datetime(2026, 10, 28, tzinfo=UTC)


def workbook(mutate=None, count=24):
    headers = {
        "A": "Period",
        "C": "Crude oil, Brent",
        "F": "Copper",
        "J": "Iron ore, cfr spot",
    }
    data = [headers, {"C": "($/bbl)", "F": "($/mt)", "J": "($/dmtu)"}]
    for i in range(count):
        data.append(
            {
                "A": f"{2024 + i // 12}M{i % 12 + 1:02d}",
                "C": 70 + i,
                "F": 8000 + i,
                "J": 100 + i,
            }
        )
    if mutate:
        mutate(data)
    rows = []
    for n, row in enumerate(data, 1):
        cells = []
        for col, value in row.items():
            if isinstance(value, (int, float)):
                cells.append(f'<c r="{col}{n}"><v>{value}</v></c>')
            elif isinstance(value, tuple):
                cells.append(f'<c r="{col}{n}"><f>1+2</f><v>3</v></c>')
            else:
                cells.append(
                    f'<c r="{col}{n}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'
                )
        rows.append("<row>" + "".join(cells) + "</row>")
    output = BytesIO()
    with ZipFile(output, "w") as z:
        z.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Monthly Prices" r:id="rId7"/></sheets></workbook>',
        )
        z.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships><Relationship Id="rId7" Target="worksheets/prices.xml"/></Relationships>',
        )
        z.writestr(
            "xl/worksheets/prices.xml",
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
            + "".join(rows)
            + "</sheetData></worksheet>",
        )
    return output.getvalue()


class Fake:
    id = "world_bank"
    series = PILOT

    def __init__(self, batch=None):
        self.batch = batch or parse_workbook(workbook(), NOW)
        self.error = None
        self.calls = 0

    def fetch(self):
        self.calls += 1
        if self.error:
            raise self.error
        return self.batch


@pytest.fixture
def env(tmp_path):
    clock = [NOW]
    provider = Fake()
    store = Store(tmp_path / "local.db")
    return Ingestion(store, [provider], now_fn=lambda: clock[0]), provider, clock


def records(engine):
    with engine.store.connection() as db:
        return [
            tuple(r)
            for r in db.execute(
                "SELECT * FROM ingest_observations ORDER BY dataset_id,period"
            )
        ]


def test_actual_column_labels_native_periods_and_missing_values():
    batch = parse_workbook(
        workbook(lambda rows: rows[3].update(C="...", F="", J="\u2026")), NOW
    )
    assert len(batch.points) == 72
    assert sum(p.value is None for p in batch.points) == 3
    assert all(p.quality == "missing" for p in batch.points if p.value is None)
    assert batch.metadata["wb_brent_monthly"]["first_observed"] == "2024-01"
    assert batch.metadata["wb_copper_monthly"]["source_column"] == "F"
    assert batch.metadata["wb_iron_ore_monthly"]["warnings"]
    assert batch.metadata["wb_iron_ore_monthly"]["source_unit"] == "($/dmtu)"


@pytest.mark.parametrize(
    "mutate,code",
    [
        (lambda r: r[0].update(C="Other crude"), "missing_pilot_header"),
        (lambda r: r[0].update(D="Copper"), "duplicate_header"),
        (lambda r: r[1].update(F="EUR/mt"), "unit_changed"),
        (lambda r: r[3].update(A="2024M13"), "invalid_period"),
        (lambda r: r[3].update(A="2024M01"), "duplicate_or_unordered_period"),
        (lambda r: r[3].update(A="2024-02"), "invalid_period"),
        (lambda r: r[3].update(C=("formula",)), "invalid_cell"),
        (lambda r: r[3].update(C=-1), "invalid_price"),
        (lambda r: r[3].update(C=0), "invalid_price"),
        (lambda r: r[3].update(C="NaN"), "invalid_price"),
        (lambda r: r[3].update(C="invalid"), "malformed_workbook"),
    ],
)
def test_malformed_workbooks_fail_closed(mutate, code):
    with pytest.raises(ProviderError, match=code):
        parse_workbook(workbook(mutate), NOW)


def test_not_a_workbook_and_archive_bombs_rejected(monkeypatch):
    with pytest.raises(ProviderError, match="malformed_workbook"):
        parse_workbook(b"<html>provider unavailable</html>", NOW)
    monkeypatch.setattr("backend.app.ingestion.world_bank.MAX_EXPANDED", 10)
    with pytest.raises(ProviderError, match="expanded_file_too_large"):
        parse_workbook(workbook(), NOW)


def test_unsafe_xml_rejected():
    original = ZipFile(BytesIO(workbook()))
    out = BytesIO()
    with ZipFile(out, "w") as z:
        for name in original.namelist():
            content = original.read(name)
            if name == "xl/workbook.xml":
                content = b'<!DOCTYPE x [<!ENTITY y "danger">]>' + content
            z.writestr(name, content)
    with pytest.raises(ProviderError, match="unsafe_xml"):
        parse_workbook(out.getvalue(), NOW)


def test_idempotent_duplicate_prevention_and_permissions(env):
    engine, _, _ = env
    assert engine.run_once()["inserted"] == 72
    old = records(engine)
    assert engine.run_once(force=True)["state"] == "unchanged"
    assert records(engine) == old
    assert all(
        not s["public_display"] and not s["ai_allowed"]
        for s in engine.status()["datasets"]
    )
    with engine.store.connection(True) as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE ingest_datasets SET ai_allowed=1")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE ingest_datasets SET public_display=1")


def test_revisions_include_withdrawn_values_and_old_vintages(env):
    engine, provider, _ = env
    engine.run_once()
    provider.batch = parse_workbook(
        workbook(lambda r: r[-1].update(C=123.456, F="...")), NOW
    )
    result = engine.run_once(force=True)
    assert result["revised"] == 2 and result["inserted"] == 0
    with engine.store.connection() as db:
        old = db.execute(
            "SELECT * FROM ingest_revisions ORDER BY dataset_id"
        ).fetchall()
        assert len(old) == 2 and old[0]["old_value"] == 93
        assert (
            db.execute(
                "SELECT value FROM ingest_observations WHERE dataset_id='wb_copper_monthly' AND period='2025-12'"
            ).fetchone()[0]
            is None
        )
    assert engine.run_once(force=True)["state"] == "unchanged"
    assert engine.status()["revisions"] == 2


def test_changed_artifact_without_numeric_changes_does_not_create_revisions(env):
    engine, provider, _ = env
    engine.run_once()
    before = records(engine)
    provider.batch = replace(
        provider.batch, source_hash=sha256(b"different metadata").hexdigest()
    )
    assert engine.run_once(force=True)["revised"] == 0
    assert records(engine) == before


def test_bounded_backfill_resumes_after_restart_and_respects_due_time(tmp_path):
    clock = [NOW]
    provider = Fake()
    store = Store(tmp_path / "resume.db")
    first = Ingestion(store, [provider], now_fn=lambda: clock[0], chunk_months=12)
    assert first.run_once()["inserted"] == 36
    restarted = Ingestion(
        Store(store.path), [provider], now_fn=lambda: clock[0], chunk_months=12
    )
    assert restarted.run_once()["state"] == "idle"
    clock[0] += timedelta(seconds=61)
    assert restarted.run_once()["inserted"] == 36
    assert restarted.status()["observations"] == 72


@pytest.mark.parametrize(
    "error",
    [
        ProviderError("http_429", 900),
        requests.Timeout("SYNTHETIC_SECRET"),
        RuntimeError("SYNTHETIC_SECRET"),
    ],
)
def test_outages_backoff_and_recovery_preserve_good_data(env, error):
    engine, provider, clock = env
    engine.run_once()
    before = records(engine)
    success = engine.status()["jobs"][0]["last_success"]
    provider.error = error
    failed = engine.run_once(force=True)
    assert failed["state"] == "failed" and "SYNTHETIC_SECRET" not in json.dumps(
        engine.status()
    )
    assert records(engine) == before
    assert engine.status()["jobs"][0]["last_success"] == success
    assert engine.run_once()["state"] == "idle"
    clock[0] += timedelta(days=2)
    provider.error = None
    assert engine.run_once()["state"] == "unchanged"
    assert engine.status()["jobs"][0]["failures"] == 0


def test_shared_lease_and_abandoned_job_recovery(env):
    engine, _, clock = env
    assert engine.store.acquire(
        "ingestion:world_bank", "crashed-worker", NOW.timestamp(), 60
    )
    with engine.store.connection(True) as db:
        db.execute(
            "INSERT INTO ingest_runs(id,provider,started_at,state) VALUES ('old','world_bank',?,'running')",
            (NOW.isoformat(),),
        )
    assert engine.run_once()["state"] == "idle"
    clock[0] += timedelta(seconds=61)
    assert engine.run_once()["state"] == "complete"
    with engine.store.connection() as db:
        assert (
            db.execute("SELECT state FROM ingest_runs WHERE id='old'").fetchone()[0]
            == "abandoned"
        )


def test_expired_worker_cannot_commit_after_lease_reassigned(env):
    engine, provider, clock = env
    original = provider.fetch

    def replaced():
        batch = original()
        clock[0] += timedelta(seconds=181)
        assert engine.store.acquire(
            "ingestion:world_bank", "new-owner", clock[0].timestamp(), 180
        )
        return batch

    provider.fetch = replaced
    assert engine.run_once()["error_code"] == "lease_lost"
    assert records(engine) == []


def test_partial_writes_rollback_atomically(env):
    engine, _, _ = env
    with engine.store.connection(True) as db:
        db.execute(
            "CREATE TRIGGER test_abort BEFORE INSERT ON ingest_observations WHEN NEW.dataset_id='wb_copper_monthly' BEGIN SELECT RAISE(ABORT,'synthetic'); END"
        )
    assert engine.run_once()["state"] == "failed"
    assert records(engine) == []
    with engine.store.connection(True) as db:
        db.execute("DROP TRIGGER test_abort")
    assert engine.run_once(force=True)["inserted"] == 72


def test_storage_budget_halts_without_deletion(env, monkeypatch):
    engine, _, _ = env
    monkeypatch.setattr(
        engine, "_capacity", Mock(side_effect=ProviderError("storage_budget"))
    )
    assert engine.run_once()["error_code"] == "storage_budget"
    assert engine.status()["observations"] == 0


def test_shrunken_history_and_missing_period_rows_quarantined(env):
    engine, provider, _ = env
    engine.run_once()
    before = records(engine)
    provider.batch = parse_workbook(workbook(count=12), NOW)
    assert engine.run_once(force=True)["error_code"] == "history_truncated"
    provider.batch = parse_workbook(workbook(lambda r: r.pop(10)), NOW)
    assert engine.run_once(force=True)["error_code"] == "missing_period_rows"
    assert records(engine) == before


def test_download_is_bounded_and_429_is_not_retried_inline(monkeypatch):
    response = Mock(status_code=429, headers={"Retry-After": "900"})
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    session = Mock()
    session.get.return_value = response
    with pytest.raises(ProviderError) as e:
        WorldBank(session).fetch()
    assert e.value.retry_after == 900 and session.get.call_count == 1
    response.status_code = 200
    response.iter_content.return_value = [b"x" * 20]
    monkeypatch.setattr("backend.app.ingestion.world_bank.MAX_BYTES", 10)
    with pytest.raises(ProviderError, match="download_too_large"):
        WorldBank(session).fetch()


def test_additive_schema_preserves_existing_state(tmp_path):
    path = tmp_path / "old.db"
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE library(id TEXT PRIMARY KEY,label TEXT NOT NULL,created_at TEXT NOT NULL,snapshot TEXT NOT NULL,notes TEXT NOT NULL); INSERT INTO library VALUES ('saved','Existing research','2026-01-01','{}','keep');"
    )
    db.close()
    store = Store(path)
    Ingestion(store, [Fake()]).run_once()
    with store.connection() as db:
        assert (
            db.execute("SELECT notes FROM library WHERE id='saved'").fetchone()[0]
            == "keep"
        )
    from backend.app.v2.definitions import SPECS

    assert len(SPECS) == 30 and not set(SPECS).intersection(s.id for s in PILOT)


def test_worker_disabled_by_default_and_unexpected_failure_recovers(tmp_path):
    store = Store(tmp_path / "worker.db")
    disabled = IngestionWorker(store)
    disabled.tick()
    assert disabled._pool is None and not store.path.exists()
    worker = IngestionWorker(store, enabled=True)
    engine = Mock()
    engine.run_once.side_effect = [RuntimeError("secret"), {"state": "complete"}]
    worker._engine = engine
    try:
        worker.tick()
        worker._future.result(timeout=2)
        assert worker.error_code == "worker_error"
        worker.tick()
        worker._future.result(timeout=2)
        assert worker.error_code is None
    finally:
        worker.stop()


def test_discovery_exception_does_not_starve_ingestion_dispatch(monkeypatch):
    from backend.app.v2 import main

    monkeypatch.setattr(
        main,
        "discovery_service",
        SimpleNamespace(get=Mock(side_effect=RuntimeError("scan"))),
    )
    worker = SimpleNamespace(tick=Mock())
    monkeypatch.setattr(main, "ingestion_worker", worker)
    with pytest.raises(RuntimeError):
        main.background_refresh()
    worker.tick.assert_called_once()


def test_recent_incremental_update_and_monthly_old_revision_reconciliation(env):
    engine, provider, clock = env
    engine.run_once()
    provider.batch = parse_workbook(workbook(count=30), NOW)
    assert engine.run_once(force=True)["inserted"] == 18
    # An old revision outside the 24-month incremental window waits for reconciliation.
    provider.batch = parse_workbook(
        workbook(lambda r: r[2].update(C=99), count=30), NOW
    )
    assert engine.run_once(force=True)["revised"] == 0
    clock[0] += timedelta(days=31)
    assert engine.run_once(force=True)["revised"] == 1


def test_stale_source_is_recorded_without_claiming_freshness():
    batch = parse_workbook(workbook(count=12), NOW)
    assert all(m["stale"] for m in batch.metadata.values())


def test_future_period_is_rejected():
    with pytest.raises(ProviderError, match="duplicate_or_unordered_period"):
        parse_workbook(workbook(count=36), NOW)


def test_duplicate_batch_is_quarantined(env):
    engine, provider, _ = env
    provider.batch = replace(
        provider.batch, points=provider.batch.points + (provider.batch.points[0],)
    )
    assert engine.run_once()["error_code"] == "duplicate_or_unknown_observation"
    assert records(engine) == []
