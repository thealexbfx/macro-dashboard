"""All state and approvals below are synthetic/disposable, never production."""

import json
import sqlite3
from pathlib import Path
from datetime import UTC, date, datetime, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.catalog import operations, rollout
from backend.app.catalog.releases import candidates
from backend.app.ingestion.catalog_refresh import CatalogRefresh, policy
from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.native import Observation, digest
from backend.app.ingestion.official_snapshots import freeze
from backend.app.ingestion.provider_requests import Requests, migrate
from backend.app.ingestion.release_discovery import attachment, discover
from backend.app.v2 import main as v
from backend.app.v2.refresh import scheduled_service_class
from backend.tests.test_release100 import fixture, stage_all
from backend.app.catalog import release100


def hundred(tmp_path):
    store, bundle, reader = fixture(tmp_path)
    stage_all(store, bundle)
    release100.publish(store.path, bundle, approved=True)
    return store, reader


def test_canonical_registry_preserves_all_ids_and_never_claims_grants():
    rows = operations.registry()
    assert len(rows) == 313 and len({r["id"] for r in rows}) == 313
    assert {r["id"] for r in rows if r["legacy"]} == set(v.SPECS)
    assert not any(r.get("public_display") for r in rows if not r["legacy"])
    assert len(policy()) == 164
    plan = rollout.load_plan()
    assert len(plan["baseline_ids"]) == 100 and len(plan["datasets"]) == 94
    assert not {r["id"] for r in plan["datasets"]} & rollout.PRIVATE


def test_one_release_194_private_stage_idempotency_rollback_and_migration_restore(
    tmp_path,
):
    store, reader = hundred(tmp_path)
    before = operations.health(store.path)
    assert (
        before["summary"]["public"] == 100
        and before["summary"]["automatic_refresh"] == 0
    )
    with store.connection() as db:
        baseline = [tuple(r) for r in db.execute("SELECT * FROM library")]
        old_grants = [
            tuple(r)
            for r in db.execute(
                "SELECT * FROM catalog_release_grants ORDER BY dataset_id"
            )
        ]
        backup = sqlite3.connect(tmp_path / "schema4.sqlite3")
        db.backup(backup)
        backup.close()
    with store.connection(True) as db:
        migrate(db)
        migrate(db)
    plan = rollout.load_plan()
    pubs = candidates()
    bundle = tmp_path / "expansion"
    records = {}
    for row in plan["datasets"]:
        p = pubs[row["id"]]
        periods = {
            "daily": ("2020-01-02", "2020-01-03"),
            "weekly": ("2020-01-03", "2020-01-10"),
            "monthly": ("2020-01", "2020-02"),
            "quarterly": ("2020-Q1", "2020-Q2"),
            "annual": ("2020", "2021"),
        }[p.definition.frequency]
        if p.definition.frequency == "weekly":
            first = date(2020, 1, 1)
            first += timedelta(
                days=(p.definition.calendar.week_ending - first.weekday()) % 7
            )
            periods = (first.isoformat(), (first + timedelta(days=7)).isoformat())
        path, hashed = freeze(
            bundle / "snapshots",
            p.definition,
            tuple(Observation(x, x, y) for x, y in zip(periods, (0, -2))),
            b"SYNTHETIC",
            p.source_url,
        )
        records[row["id"]] = {
            "snapshot_hash": hashed,
            "bytes": path.stat().st_size,
            "rows": 2,
        }
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "created_at": datetime.now(UTC).isoformat(),
                "plan_sha256": digest(plan),
                "datasets": records,
            }
        )
    )
    with pytest.raises(ValueError):
        rollout.publish(store.path, bundle, plan, approved=True)
    for _ in range(40):
        if rollout.stage(store.path, bundle, plan)["complete"]:
            break
    else:
        pytest.fail("Bounded staging failed to converge")
    assert len(release100.public_ids(reader)) == 100
    for row in plan["datasets"]:
        with pytest.raises(ValueError):
            reader.metadata(row["id"])
    assert rollout.validate(store.path, bundle, plan)["validated"] == 94
    assert rollout.publish(store.path, bundle, plan, approved=True)["public"] == 194
    assert (
        rollout.publish(store.path, bundle, plan, approved=True)["state"]
        == "already_published"
    )
    assert rollout.stage(store.path, bundle, plan)["complete"]
    report = operations.health(
        store.path, scheduler={"ready": True}, refresh={"enabled": True}, limit=400
    )
    assert (
        report["summary"]["public"] == 194
        and report["summary"]["automatic_refresh"] == 194
    )
    assert (
        report["summary"]["healthy"] == 0
    )  # Configuration/liveness alone is not verification.
    assert all(
        "observations" not in r or r["observations"] is None for r in report["items"]
    )
    # Audit the existing full 194-dataset release fixture, not a second ingestion
    # fixture or a 30-only shortcut. This is synthetic evidence, not production.
    from backend.app.catalog.readiness import audit

    with store.connection() as db:
        before_audit = list(db.iterdump())
    readiness = audit(store.path, evidence_origin="fixture", expected_public=194)
    assert readiness["scope"]["matches_expected"]
    assert len(readiness["datasets"]) == 194
    assert {r["id"] for r in readiness["datasets"]} == set(
        release100.public_ids(reader)
    )
    assert readiness["summary"]["verified_successful_source_checks"] == 0
    assert all(
        "historical_quality" in r and "research_suitability" in r
        for r in readiness["datasets"]
    )
    with store.connection() as db:
        assert list(db.iterdump()) == before_audit
    assert rollout.rollback(store.path, plan, approved=True)["public"] == 100
    assert rollout.rollback(store.path, plan, approved=True)["public"] == 100
    with store.connection() as db:
        assert [tuple(r) for r in db.execute("SELECT * FROM library")] == baseline
        assert [
            tuple(r)
            for r in db.execute(
                "SELECT * FROM catalog_release_grants WHERE public_display=1 ORDER BY dataset_id"
            )
        ] == old_grants
        assert db.execute("SELECT count(*) FROM ingest_observations").fetchone()[0] == 3
        backup = sqlite3.connect(tmp_path / "schema5.sqlite3")
        db.backup(backup)
        backup.close()
    assert (
        rollout.verify_backup(
            tmp_path / "schema5.sqlite3",
            release100.file_sha256(tmp_path / "schema5.sqlite3"),
        )["disposable_restore"]
        == "ok"
    )
    # Old executable still reads the additive schema, original 100 and private pilots.
    assert release100.check(store.path)["public"] == 100


def test_legacy_successful_stale_reference_is_not_transport_failure_and_truncation_retains_history(
    tmp_path,
):
    now = [datetime(2026, 11, 2, tzinfo=UTC)]
    data = pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=24, freq="MS"),
            "value": [4.0] * 24,
        }
    )

    class Provider:
        def fred_series(self, *_):
            return data.to_dict("records")

    from backend.app.v2.state import Store

    store = Store(tmp_path / "legacy.sqlite3")
    service = scheduled_service_class(v.DataService, v.Dataset)(
        store,
        provider=Provider(),
        today_fn=lambda: now[0].date(),
        now_fn=lambda: now[0],
    )
    first = service.get("unemployment")
    assert first.status == "stale" and first.release_metadata["source_check_succeeded"]
    assert first.release_metadata["last_source_success_at"] == now[0].isoformat()
    with store.connection() as db:
        assert db.execute("SELECT failures FROM source_cache").fetchone()[0] == 0
    now[0] += timedelta(days=1)
    data = data.tail(2)
    failed = service.get("unemployment")
    assert (
        len(failed.observations) == 24
        and failed.release_metadata["source_check_succeeded"] is False
    )
    assert (
        failed.release_metadata["last_source_success_at"]
        == first.release_metadata["last_source_success_at"]
    )
    with store.connection() as db:
        assert db.execute("SELECT failures FROM source_cache").fetchone()[0] == 1


def test_durable_request_quota_restart_corruption_failure_and_day_boundary(tmp_path):
    from backend.app.v2.state import Store
    from backend.app.ingestion.partition_schema import migrate as native
    from backend.app.catalog.releases import migrate as releases
    from backend.app.ingestion.catalog_refresh import migrate as refresh

    store = Store(tmp_path / "quota.sqlite3")
    with store.connection(True) as db:
        native(db)
        releases(db)
        refresh(db)
        migrate(db)
    now = [datetime(2026, 11, 2, tzinfo=UTC)]
    calls = []

    def fetch(url, **kw):
        calls.append(kw)
        if kw["payload"] == b"failure":
            raise ProviderError("http_503")
        return b"official source", {"etag": "fixture"}

    request = Requests(store, fetch, tmp_path / "raw", now=lambda: now[0])
    assert (
        request.get(
            "bls",
            "https://api.bls.gov/publicAPI/v2/timeseries/data/",
            payload=b"one",
            quota=2,
        )[0]
        == b"official source"
    )
    restarted = Requests(store, fetch, tmp_path / "raw", now=lambda: now[0])
    restarted.get(
        "bls",
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        payload=b"one",
        quota=2,
    )
    assert len(calls) == 1
    with pytest.raises(ProviderError, match="http_503"):
        restarted.get(
            "bls",
            "https://api.bls.gov/publicAPI/v2/timeseries/data/",
            payload=b"failure",
            quota=2,
        )
    with pytest.raises(ProviderError, match="provider_daily_budget"):
        restarted.get(
            "bls",
            "https://api.bls.gov/publicAPI/v2/timeseries/data/",
            payload=b"three",
            quota=2,
        )
    assert len(calls) == 2
    now[0] += timedelta(days=1)
    restarted.get(
        "bls",
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        payload=b"three",
        quota=2,
    )
    assert len(calls) == 3
    path = next((tmp_path / "raw").glob("*.raw"))
    path.write_bytes(b"corrupt")
    with pytest.raises(ProviderError, match="provider_cache_invalid"):
        restarted.get(
            "bls",
            "https://api.bls.gov/publicAPI/v2/timeseries/data/",
            payload=b"three",
            quota=2,
        )


def test_official_release_discovery_rejects_ambiguity_and_foreign_urls():
    url = "https://assets.publishing.service.gov.uk/media/official/ET_3.13_OCT_26.xlsx"
    document = {
        "details": {
            "attachments": [{"title": "Deliveries (ET 3.13 - monthly)", "url": url}]
        }
    }
    assert attachment(document, table="3.13") == url
    entry = {"source": {"provider": "desnz", "selector": "ET 3.13 / Month / column I"}}
    assert (
        discover(entry, fetch=lambda *_: (json.dumps(document).encode(), {}))[0] == url
    )
    document["details"]["attachments"].append(
        {"title": "Other (ET 3.13 - monthly)", "url": url.replace("OCT", "NOV")}
    )
    with pytest.raises(ProviderError, match="ambiguous"):
        attachment(document, table="3.13")
    document["details"]["attachments"] = [
        {
            "title": "Other (ET 3.13 - monthly)",
            "url": "https://attacker.invalid/file.xlsx",
        }
    ]
    with pytest.raises(ProviderError, match="unapproved"):
        attachment(document, table="3.13")


def test_bls_definition_metadata_is_required_even_after_successful_observations(
    tmp_path, monkeypatch
):
    from backend.app.ingestion import bls_history
    from backend.app.ingestion.provider_requests import bls_group
    from backend.app.ingestion.catalog_refresh import source_entries
    from backend.app.v2.state import Store

    key = "bls_24870509f36ee4ecd234"
    entry = source_entries()[key]
    monkeypatch.setattr(
        bls_history,
        "capture",
        lambda *a, **kw: (
            json.dumps(
                {
                    "Results": {
                        "series": [
                            {"seriesID": entry["source"]["selector"], "data": []}
                        ]
                    }
                }
            ).encode(),
            {},
        ),
    )
    with pytest.raises(ProviderError, match="bls_definition_metadata_unavailable"):
        bls_group(
            [entry],
            Requests(Store(tmp_path / "unused.sqlite3"), None, tmp_path / "raw"),
        )


def test_backup_orchestrator_uses_sqlite_backup_api_and_disposable_restore_only(
    tmp_path, capsys
):
    from scripts.catalog_backup import REMOTE

    source = tmp_path / "source.sqlite3"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE library(id TEXT,notes TEXT)")
        db.execute("INSERT INTO library VALUES('saved','preserve')")
    before = source.read_bytes()
    exec(
        compile(
            REMOTE.replace("/var/data/macrolens-v2.sqlite3", source.as_posix()),
            "<disposable backup test>",
            "exec",
        ),
        {},
    )
    result = json.loads(capsys.readouterr().out)
    assert source.read_bytes() == before
    assert Path(result["backup"]) != source
    assert (
        rollout.verify_backup(Path(result["backup"]), result["sha256"])[
            "disposable_restore"
        ]
        == "ok"
    )
    with pytest.raises(ValueError, match="checksum"):
        rollout.verify_backup(Path(result["backup"]), "0" * 64)


def test_health_endpoint_is_admin_only_and_never_reflects_token(tmp_path, monkeypatch):
    monkeypatch.setenv("MACROLENS_ADMIN_TOKEN", "synthetic-private-test-token")
    with TestClient(v.app) as client:
        response = client.get("/api/v2/discovery/admin/data-health")
        assert response.status_code == 403
        monkeypatch.setattr(
            operations, "health", lambda *a, **k: {"summary": {"public": 100}}
        )
        response = client.get(
            "/api/v2/discovery/admin/data-health",
            headers={"Authorization": "Bearer synthetic-private-test-token"},
        )
        assert (
            response.status_code == 200 and response.json()["summary"]["public"] == 100
        )
        assert response.headers["cache-control"] == "no-store"
        assert "synthetic-private-test-token" not in json.dumps(dict(response.headers))


def test_desnz_provisional_rows_are_not_silently_omitted(monkeypatch):
    from backend.app.ingestion import expansion_sources as sources
    from backend.app.ingestion.catalog_refresh import source_entries

    key = "desnz_545740a2d48ae00c5437"
    rows = [
        ["Deliveries (thousand tonnes)"] + [None] * 12,
        [None] * 8 + ["White diesel"] + [None] * 4,
    ]
    rows += [
        [label] + [None] * 7 + [value] + [None] * 4
        for label, value in [("July 2026", 1), ("August 2026 [provisional]", 2)]
    ]
    monkeypatch.setattr(sources, "excel_rows", lambda *_: rows)
    _, points, _ = sources.parse_desnz(source_entries()[key], b"fixture")
    assert [p.period for p in points] == ["2026-07", "2026-08"]
    assert points[-1].flags == ("source_status=p",)
    rows[-1][0] = "[provisional] August 2026"
    assert (
        sources.parse_desnz(source_entries()[key], b"fixture")[1][-1].period
        == "2026-08"
    )
    rows[-1][0] = "August 2026 [unknown annotation]"
    with pytest.raises(ValueError, match="silently omit"):
        sources.parse_desnz(source_entries()[key], b"fixture")


def test_new_desnz_artifact_does_not_reuse_old_http_validators(tmp_path, monkeypatch):
    from backend.app.ingestion import catalog_refresh as refresh_module
    from backend.app.ingestion.partition_schema import migrate as native
    from backend.app.catalog.releases import migrate as releases
    from backend.app.v2.state import Store

    store = Store(tmp_path / "desnz.sqlite3")
    with store.connection(True) as db:
        native(db)
        releases(db)
        refresh_module.migrate(db)
    key = "desnz_545740a2d48ae00c5437"
    pub = candidates()[key]
    config = tmp_path / "policy.json"
    config.write_text(
        json.dumps(
            {
                "datasets": [
                    {
                        "id": key,
                        "mode": "stage",
                        "automation_ready": True,
                        "ingest_approved": True,
                        "check_seconds": 86400,
                    }
                ]
            }
        )
    )
    version = [1]
    calls = []

    def fetch(url, **kw):
        calls.append((url, kw))
        if "/api/content/" in url:
            return json.dumps(
                {
                    "details": {
                        "attachments": [
                            {
                                "title": "Deliveries (ET 3.13 - monthly)",
                                "url": f"https://assets.publishing.service.gov.uk/media/official/ET_3.13_{version[0]}.xlsx",
                            }
                        ]
                    }
                }
            ).encode(), {}
        return str(version[0]).encode(), {"etag": "same-fixture-validator"}

    monkeypatch.setitem(
        refresh_module.PARSERS,
        "desnz",
        lambda entry, raw: (
            pub.definition,
            (Observation("2020-01", "2020-01", float(raw)),),
            {"unit_label": pub.definition.units},
        ),
    )
    engine = CatalogRefresh(store, config=config, fetch=fetch)
    pending, response = engine._download(
        key,
        {"content_hash": None, "raw_hash": None, "etag": None, "last_modified": None},
    )
    assert json.loads(Path(pending["path"]).read_text())["source_url"] == pub.source_url
    version[0] = 2
    engine._download(
        key,
        {
            "content_hash": response["content_hash"],
            "raw_hash": response["raw_hash"],
            "etag": "same-fixture-validator",
            "last_modified": None,
            "provenance": json.dumps(
                {
                    "resolved_source_url": "https://assets.publishing.service.gov.uk/media/official/ET_3.13_1.xlsx"
                }
            ),
        },
    )
    assert calls[-1][1]["validators"] == {}
