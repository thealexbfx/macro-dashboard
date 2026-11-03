"""Exact release approvals, staged publication and reversible rollout; offline."""

import json
import sqlite3
from datetime import UTC, date, datetime

import pytest

from backend.app.catalog import release100 as r
from backend.app.catalog.release_cli import ingest
from backend.app.catalog.releases import activate, candidates, migrate
from backend.app.ingestion.catalog_refresh import CONFIG, migrate as refresh_migrate
from backend.app.ingestion.native import Observation
from backend.app.ingestion.official_snapshots import freeze
from backend.app.ingestion.partition_schema import migrate as native_migrate
from backend.app.v2.native_reader import NativeReader
from backend.app.v2.state import Store


def fixture(tmp_path):
    plan, pubs = r.load_plan(), candidates()
    store = Store(tmp_path / "disposable.sqlite3")
    with store.connection(True) as db:
        native_migrate(db)
        migrate(db)
        refresh_migrate(db)
        db.execute(
            "INSERT INTO library VALUES('saved','Saved','2020-01-01','{}','preserve')"
        )
        for key in r.PRIVATE:
            db.execute(
                "INSERT INTO ingest_datasets(id,provider,metadata,updated_at) VALUES(?,'world_bank','{}','2020-01-01')",
                (key,),
            )
            db.execute(
                "INSERT INTO ingest_observations VALUES(?,'2020-01',1,'fixture',1,'2020-01-01','2020-01-01','fixture')",
                (key,),
            )
    bundle = tmp_path / "bundle"
    records = {}
    reader = NativeReader(store.path)
    for row in plan["datasets"]:
        key, p = row["id"], pubs[row["id"]]
        periods = {
            "daily": ("2020-01-02", "2020-01-03"),
            "weekly": ("2020-01-03", "2020-01-10"),
            "monthly": ("2020-01", "2020-02"),
            "quarterly": ("2020-Q1", "2020-Q2"),
            "annual": ("2020", "2021"),
        }[p.definition.frequency]
        path, hashed = freeze(
            bundle / "snapshots",
            p.definition,
            tuple(
                Observation(period, period, value)
                for period, value in zip(periods, (0, -2))
            ),
            b"SYNTHETIC RELEASE FIXTURE",
            p.source_url,
        )
        records[key] = {
            "snapshot_hash": hashed,
            "bytes": path.stat().st_size,
            "rows": 2,
        }
        if key in plan["existing_native_ids"]:
            assert ingest(store, p, path, hashed)["state"] == "complete"
            with store.connection(True) as db:
                activate(db, p, reader, approved=True)
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "plan_sha256": r.plan_hash(),
                "created_at": datetime.now(UTC).isoformat(),
                "datasets": records,
            }
        )
    )
    return store, bundle, reader


def stage_all(store, bundle):
    for _ in range(100):
        result = r.stage(store.path, bundle)
        if not result["results"]:
            return
    pytest.fail("Stage failed to converge within bound")


def test_historical_70_approvals_preserved_by_larger_reviewed_plan():
    p = r.load_plan()
    rules = json.loads(CONFIG.read_text())
    assert len(rules["datasets"]) == 185
    assert sum(x["ingest_approved"] for x in rules["datasets"]) == 164
    assert {x["id"] for x in p["datasets"]} <= {x["id"] for x in rules["datasets"] if x["ingest_approved"]}
    assert len(p["additional_ids"]) == 57
    assert len({x["region"] for x in p["datasets"]}) >= 7
    assert {x["provider"] for x in p["datasets"]} == {
        "eurostat",
        "ons",
        "eia",
        "bea",
        "boe",
        "ecb",
        "census",
    }


def test_private_stage_publish_rerun_rollback_restore(tmp_path):
    store, bundle, reader = fixture(tmp_path)
    old = set(r.public_ids(reader))
    assert len(old) == 43
    with store.connection() as db:
        baseline = [
            tuple(x)
            for x in db.execute(
                "SELECT * FROM catalog_release_grants ORDER BY dataset_id"
            )
        ]
    stage_all(store, bundle)
    assert r.public_ids(reader) == old
    r.validate(store.path, bundle)
    for key in r.load_plan()["additional_ids"]:
        with pytest.raises(ValueError):
            reader.metadata(key)
    with pytest.raises(ValueError):
        r.publish(store.path, bundle)
    assert r.publish(store.path, bundle, approved=True)["public"] == 100
    assert r.publish(store.path, bundle, approved=True)["state"] == "already_published"
    assert r.stage(store.path, bundle)["results"] == []
    for key in r.load_plan()["additional_ids"]:
        assert [
            p["value"]
            for p in reader.observations(key, date(2019, 1, 1), date(2022, 1, 1))[
                "dataset"
            ]["observations"]
        ] == [0, -2]
    with store.connection(True) as db:
        db.execute("UPDATE library SET notes='newer user research'")
    assert r.rollback(store.path, approved=True)["public"] == 43
    assert r.rollback(store.path, approved=True)["public"] == 43
    with store.connection() as db:
        assert db.execute("SELECT count(*) FROM norm_observations").fetchone()[0] == 140
        assert (
            db.execute("SELECT notes FROM library").fetchone()[0]
            == "newer user research"
        )
        assert db.execute("SELECT count(*) FROM ingest_observations").fetchone()[0] == 3
        assert [
            tuple(x)
            for x in db.execute(
                "SELECT * FROM catalog_release_grants WHERE public_display=1 ORDER BY dataset_id"
            )
        ] == baseline
        backup = sqlite3.connect(tmp_path / "backup.sqlite3")
        db.backup(backup)
    restored = sqlite3.connect(tmp_path / "restored.sqlite3")
    backup.backup(restored)
    assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert (
        restored.execute("SELECT notes FROM library").fetchone()[0]
        == "newer user research"
    )
    restored.close()
    backup.close()


def test_manifest_tampering_and_incomplete_history_cannot_publish(tmp_path):
    store, bundle, _ = fixture(tmp_path)
    with pytest.raises(ValueError):
        r.publish(store.path, bundle, approved=True)
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["datasets"][r.PRIVATE[0]] = next(iter(manifest["datasets"].values()))
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Exact 70"):
        r.stage(store.path, bundle)


def test_worker_flags_and_baseline_permissions_are_release_gates(tmp_path, monkeypatch):
    store, bundle, _ = fixture(tmp_path)
    monkeypatch.setenv("MACROLENS_CATALOG_REFRESH_ENABLED", "1")
    with pytest.raises(ValueError, match="Pause"):
        r.stage(store.path, bundle)
    monkeypatch.setenv("MACROLENS_CATALOG_REFRESH_ENABLED", "0")
    with store.connection(True) as db:
        db.execute(
            "UPDATE catalog_release_grants SET public_display=0 WHERE dataset_id=?",
            (r.load_plan()["existing_native_ids"][0],),
        )
    with pytest.raises(ValueError, match="Existing public"):
        r.check(store.path)


def test_stage_bound_and_corruption_fail_closed(tmp_path):
    store, bundle, _ = fixture(tmp_path)
    with pytest.raises(ValueError, match="five"):
        r.stage(store.path, bundle, max_datasets=6)
    record = next(
        iter(json.loads((bundle / "manifest.json").read_text())["datasets"].values())
    )
    path = bundle / "snapshots" / (record["snapshot_hash"] + ".json")
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum"):
        r.stage(store.path, bundle)


def test_missing_private_baseline_stops_before_staging(tmp_path):
    store, bundle, reader = fixture(tmp_path)
    with store.connection(True) as db:
        db.execute("DELETE FROM ingest_datasets WHERE id=?", (r.PRIVATE[0],))
    with pytest.raises(ValueError, match="World Bank"):
        r.stage(store.path, bundle)
    assert len(r.public_ids(reader)) == 43
    with store.connection() as db:
        assert db.execute("SELECT count(*) FROM norm_observations").fetchone()[0] == 26
