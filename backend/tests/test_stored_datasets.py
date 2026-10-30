"""Synthetic approval fixtures only. No real rights grant and no provider HTTP."""

import json
import sqlite3
from dataclasses import asdict
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from backend.app.ingestion.schema import SCHEMA
from backend.app.v2 import main as v
from backend.app.v2.ai_guard import AIGuard
from backend.app.v2.definitions import SPECS, Spec
from backend.app.v2.state import Store
from backend.app.v2.stored_datasets import (
    PUBLIC_STORED_DEFINITIONS,
    PermissionedDataService,
    PublicStoredDefinition,
    StoredDatasetReader,
)

TODAY = date(2026, 1, 15)
KEY = "fixture_copper"
SPEC = Spec(
    id=KEY,
    name="Synthetic monthly copper benchmark",
    provider_id="FIXTURE_COPPER",
    source="Synthetic official distributor",
    category="Commodities",
    region="Global",
    frequency="monthly",
    units="USD / metric tonne",
    seasonal_adjustment="Not seasonally adjusted",
    representation="level",
    original_transformation="Native monthly benchmark",
    source_url="https://example.invalid/fixture.xlsx",
    allowed_transformations=("level", "mom", "yoy", "indexed", "standardized"),
    provider="fixture_vendor",
    definition="Synthetic benchmark only",
)
DEFINITION = PublicStoredDefinition(
    SPEC,
    ("Synthetic supplier",),
    "https://example.invalid/license",
    "Synthetic LME-like benchmark",
    "($/mt)",
)


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / "disposable.sqlite3"
    # Future-approved schema simulation ONLY in this disposable test database.
    # The application's schema and its CHECK(...=0) constraints remain unchanged.
    fixture_schema = SCHEMA.replace(
        "CHECK(public_display=0)", "CHECK(public_display IN (0,1))"
    ).replace("CHECK(ai_allowed=0)", "CHECK(ai_allowed IN (0,1))")
    with sqlite3.connect(path) as db:
        db.executescript(fixture_schema)
    store = Store(path)
    meta = {
        "id": KEY,
        "provider": SPEC.provider,
        "selector": SPEC.provider_id,
        "frequency": "monthly",
        "units": SPEC.units,
        "source_unit": "($/mt)",
        "source_url": SPEC.source_url,
        "source_hash": "a" * 64,
        "source_checked_at": "2026-01-03T00:00:00+00:00",
        "validation": {
            "source_unit": "($/mt)",
            "first_period": "1989-01",
            "last_period": "2025-12",
            "coverage_gaps": False,
        },
        "private_internal_note": "NEVER_PUBLISH_ME",
    }
    with store.connection(True) as db:
        db.execute(
            "INSERT INTO ingest_datasets VALUES (?,?,?,?,?,?,?)",
            (KEY, SPEC.provider, json.dumps(meta), 1, 0, "approved", "2026-01-03"),
        )
        db.execute(
            "INSERT INTO ingest_jobs(provider,last_success,source_hash) VALUES (?,?,?)",
            (SPEC.provider, "2026-01-03T00:00:00+00:00", "a" * 64),
        )
        rows = []
        for i in range(444):
            period = f"{1989 + i // 12:04d}-{i % 12 + 1:02d}"
            value = None if i == 433 else 100 + i
            rows.append(
                (
                    KEY,
                    period,
                    value,
                    "missing" if value is None else "observed",
                    1,
                    "2026-01-03",
                    "2026-01-03",
                    "fixture-run",
                )
            )
        db.executemany("INSERT INTO ingest_observations VALUES (?,?,?,?,?,?,?,?)", rows)
    reader = StoredDatasetReader(
        path, v.Dataset, {KEY: DEFINITION}, today_fn=lambda: TODAY
    )
    legacy_data = v.Dataset(
        **asdict(SPECS["unemployment"]),
        status="ok",
        message="Synthetic",
        observations=[
            v.Observation(date=r[1] + "-01", value=float(4 + i / 100))
            for i, r in enumerate(rows)
        ],
        latest_value=8,
        latest_observation_date="2025-12-01",
    )
    legacy = SimpleNamespace(
        today_fn=lambda: TODAY,
        catalogue=lambda: [legacy_data],
        get=lambda key: legacy_data,
        provider=Mock(),
    )
    service = PermissionedDataService(legacy, reader, lambda: SPECS)
    return store, reader, service


def change_meta(store, mutate):
    with store.connection(True) as db:
        meta = json.loads(
            db.execute("SELECT metadata FROM ingest_datasets").fetchone()[0]
        )
        mutate(meta)
        db.execute("UPDATE ingest_datasets SET metadata=?", (json.dumps(meta),))


def test_production_defaults_have_no_public_commodity_definitions(setup):
    store, _, _ = setup
    reader = StoredDatasetReader(store.path, v.Dataset)
    assert PUBLIC_STORED_DEFINITIONS == {} and reader.catalogue() == []
    for key in (KEY, "wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly"):
        with pytest.raises(ValueError, match="Unknown dataset ID"):
            reader.get(key)
    assert len(SPECS) == 30 and not any(k.startswith("wb_") for k in SPECS)


def test_approved_fixture_payload_has_exact_nulls_and_sanitized_provenance(setup):
    _, reader, _ = setup
    d = reader.get(KEY)
    assert d.coverage_start == "1990-01-01" and len(d.observations) == 432
    assert any(o.value is None for o in d.observations)
    assert d.latest_value == 543 and d.retrieved_at == "2026-01-03T00:00:00+00:00"
    assert d.stored_provenance["stored_start"] == "1989-01"
    assert d.stored_provenance["ai_allowed"] is False
    assert "NEVER_PUBLISH_ME" not in d.model_dump_json()
    assert len(reader.catalogue()[0].observations) == 40


@pytest.mark.parametrize(
    "column,value",
    [
        ("public_display", 0),
        ("rights_state", "unreviewed"),
        ("rights_state", "revoked"),
    ],
)
def test_permissions_checked_again_without_stale_cache(setup, column, value):
    store, reader, service = setup
    assert reader.get(KEY).status == "ok"
    with store.connection(True) as db:
        db.execute(f"UPDATE ingest_datasets SET {column}=?", (value,))
    with pytest.raises(ValueError, match="Unknown dataset ID"):
        service.get(KEY)
    assert len(service.catalogue()) == 1


@pytest.mark.parametrize(
    "mutate",
    [
        lambda m: m.update(units="USD / wrong unit"),
        lambda m: m.update(provider="other"),
        lambda m: m.update(source_hash="b" * 64),
        lambda m: m["validation"].update(coverage_gaps=True),
        lambda m: m.update(source_checked_at="2026-01-03"),
    ],
)
def test_metadata_changes_fail_closed(setup, mutate):
    store, reader, _ = setup
    change_meta(store, mutate)
    with pytest.raises(ValueError):
        reader.get(KEY)


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE ingest_observations SET quality='unit_review' WHERE period='2025-12'",
        "DELETE FROM ingest_observations WHERE period='2024-01'",
        "UPDATE ingest_jobs SET cursor='2020-01'",
        "UPDATE ingest_observations SET value=-5 WHERE period='2025-12'",
    ],
)
def test_unit_review_gaps_partial_backfills_and_invalid_values_are_denied(setup, sql):
    store, reader, _ = setup
    with store.connection(True) as db:
        db.execute(sql)
    assert reader.catalogue() == []


def test_failure_and_old_observations_are_explicitly_stale(setup):
    store, reader, _ = setup
    with store.connection(True) as db:
        db.execute("UPDATE ingest_jobs SET error_code='http_403'")
    assert reader.get(KEY).status == "stale"
    reader.today_fn = lambda: date(2026, 10, 30)
    assert reader.get(KEY).status == "stale"


def test_catalogue_and_investigate_api_use_approved_fixture_only(setup, monkeypatch):
    store, _, service = setup
    monkeypatch.setattr(v, "service", service)
    client = TestClient(v.app)
    result = client.get("/api/v2/datasets")
    assert result.status_code == 200 and {d["id"] for d in result.json()} == {
        "unemployment",
        KEY,
    }
    req = {
        "datasets": [KEY, "unemployment"],
        "start": "2020-01-01",
        "end": "2025-12-31",
        "transformations": {KEY: "yoy"},
        "alignment": "native",
    }
    response = client.post("/api/v2/compare", json=req)
    assert response.status_code == 200, response.text
    assert len(response.json()["statistics"]) == 1
    for pilot in ("wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly"):
        denied = client.post("/api/v2/compare", json={**req, "datasets": [pilot]})
        assert denied.status_code == 422 and "NEVER_PUBLISH_ME" not in denied.text
    with store.connection(True) as db:
        db.execute("UPDATE ingest_datasets SET public_display=0")
    denied = client.post("/api/v2/compare", json={**req, "datasets": [KEY]})
    assert denied.status_code == 422


def test_ai_rejects_even_public_fixture_before_any_send(setup, monkeypatch):
    from backend.app.v2 import ai_guard

    store, _, _ = setup
    # Simulated key and send stub only. No real AI model is enabled or contacted.
    monkeypatch.setenv("MACROLENS_AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    send = Mock(side_effect=AssertionError("Must not send"))
    monkeypatch.setattr(ai_guard, "send", send)
    result = AIGuard(store).generate(
        [{"datasets": [KEY]}, {"datasets": ["wb_copper_monthly"]}]
    )
    assert result["generated"] == 0
    send.assert_not_called()


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "absent.sqlite3"
    reader = StoredDatasetReader(path, v.Dataset, {KEY: DEFINITION})
    assert reader.catalogue() == [] and not path.exists()


def test_shadowing_legacy_ids_is_rejected(setup):
    _, reader, service = setup
    with pytest.raises(ValueError, match="shadow"):
        PermissionedDataService(service.legacy, reader, lambda: {KEY: SPEC})


@pytest.mark.parametrize("raw", ["[]", "{broken", '{"validation":null}'])
def test_malformed_metadata_is_hidden_without_leaking(raw, setup):
    store, reader, _ = setup
    with store.connection(True) as db:
        db.execute("UPDATE ingest_datasets SET metadata=?", (raw,))
    assert reader.catalogue() == []
    with pytest.raises(ValueError, match="Unknown dataset ID"):
        reader.get(KEY)


def test_reads_do_not_initialize_schema_write_or_use_store_connection(
    setup, monkeypatch
):
    store, reader, _ = setup
    with store.connection() as db:
        before = list(db.iterdump())
    monkeypatch.setattr(
        Store, "connection", Mock(side_effect=AssertionError("No Store writes"))
    )
    assert reader.get(KEY).latest_value == 543
    with sqlite3.connect(store.path) as db:
        assert list(db.iterdump()) == before


def test_default_production_schema_keeps_all_pilots_private(tmp_path):
    store = Store(tmp_path / "private.sqlite3")
    ids = ("wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly")
    with store.connection(True) as db:
        for key in ids:
            db.execute(
                "INSERT INTO ingest_datasets(id,provider,metadata,updated_at) VALUES (?,?,?,?)",
                (key, "world_bank", '{"secret":"DO_NOT_DISCLOSE"}', "2026-01-03"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE ingest_datasets SET public_display=1")
    reader = StoredDatasetReader(store.path, v.Dataset)
    assert reader.catalogue() == []
    for key in ids:
        with pytest.raises(ValueError, match="Unknown dataset ID"):
            reader.get(key)
    with store.connection() as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM ingest_datasets WHERE public_display=0 AND ai_allowed=0 AND rights_state='unreviewed'"
            ).fetchone()[0]
            == 3
        )
