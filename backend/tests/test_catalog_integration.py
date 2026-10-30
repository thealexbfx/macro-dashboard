"""Public/native boundary regression tests; temporary databases and fake rights only."""

import sqlite3
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from backend.app.v2 import main as v
from backend.app.v2.catalog_api import PublicCatalog
from backend.app.v2.native_compare import transform_native
from backend.app.v2.native_reader import NativeReader
from backend.app.v2.state import Store
from scripts.batch0_catalog_fixture import seed_catalog


@pytest.fixture(scope="module")
def populated(tmp_path_factory):
    store = Store(tmp_path_factory.mktemp("catalog") / "disposable.sqlite3")
    reader = seed_catalog(store)
    return store, reader


@pytest.fixture
def catalog(populated, monkeypatch):
    store, reader = populated
    legacy = SimpleNamespace(
        store=store,
        today_fn=lambda: date(2026, 2, 1),
        get=Mock(side_effect=AssertionError("No provider calls")),
    )
    catalog = PublicCatalog(legacy, v.service.reader, reader)
    monkeypatch.setattr(v, "public_catalog", catalog)
    return catalog


def test_full_manifest_and_public_catalog_are_independent(catalog):
    assert catalog.manifest.page(audience="planning")["total"] == 309
    assert catalog.manifest.page()["total"] == 30
    ids, offset = [], 0
    while True:
        page = catalog.page(limit=17, offset=offset)
        assert len(page["items"]) <= 17 and page["total"] == 309
        assert all(not d["observations"] for d in page["items"])
        ids.extend(d["id"] for d in page["items"])
        if page["next_offset"] is None:
            break
        offset = page["next_offset"]
    assert len(set(ids)) == 309
    catalog.legacy.get.assert_not_called()


def test_api_filters_pagination_favourites_and_bounds(catalog):
    client = TestClient(v.app)
    r = client.get(
        "/api/v2/catalog",
        params={
            "frequency": "annual",
            "provider": "fixture_ons",
            "region": "JP",
            "limit": 3,
        },
    )
    assert r.status_code == 200
    assert r.json()["total"] > 0
    assert all(
        d["frequency"] == "annual"
        and d["provider"] == "fixture_ons"
        and d["region"] == "JP"
        for d in r.json()["items"]
    )
    r = client.post(
        "/api/v2/catalog/search",
        json={"ids": ["fixture_catalog_000", "retired_missing", "wb_copper_monthly"]},
    )
    assert [d["id"] for d in r.json()["items"]] == ["fixture_catalog_000"]
    for suffix in ("?limit=101", "?offset=-1", "?query=" + "x" * 201):
        assert client.get("/api/v2/catalog" + suffix).status_code == 422
    assert (
        client.post("/api/v2/catalog/search", json={"ids": ["x"] * 401}).status_code
        == 422
    )


def test_all_real_nonpublic_ids_deny_every_direct_read(catalog, monkeypatch):
    # The entire 309-entry real manifest is exercised; synthetic approvals have different IDs.
    client = TestClient(v.app)
    ids = [
        e["id"] for e in catalog.manifest.page(audience="planning", limit=100)["items"]
    ]
    for offset in (100, 200, 300):
        ids += [
            e["id"]
            for e in catalog.manifest.page(
                audience="planning", limit=100, offset=offset
            )["items"]
        ]
    private = set(ids) - set(v.SPECS)
    assert len(private) == 279
    for key in private:
        assert client.get(f"/api/v2/catalog/{key}").status_code == 404
        assert client.get(f"/api/v2/observations/{key}").status_code == 404
        r = client.post(
            "/api/v2/compare",
            json={"datasets": [key], "start": "2020-01-01", "end": "2020-12-31"},
        )
        assert r.status_code == 422 and "Unknown" in r.text
    assert client.get("/api/v2/catalog?query=wb_copper_monthly").json()["total"] == 0


@pytest.mark.parametrize(
    "index,frequency",
    list(
        enumerate(
            ("daily", "weekly", "monthly", "quarterly", "annual", "event", "irregular")
        )
    ),
)
def test_native_frequencies_nulls_zero_negative_and_pagination(
    catalog, index, frequency
):
    key = f"fixture_catalog_{index:03d}"
    page = catalog.observations(key, date(1700, 1, 1), date(2025, 1, 1), limit=200)
    points = page["dataset"]["observations"]
    assert page["dataset"]["frequency"] == frequency
    assert len(points) == (121 if frequency in {"event", "irregular"} else 120)
    assert any(o["value"] is None for o in points)
    assert any(o["value"] == 0 for o in points)
    assert any(o["value"] is not None and o["value"] < 0 for o in points)
    first = catalog.observations(key, date(1700, 1, 1), date(2025, 1, 1), limit=10)
    second = catalog.observations(
        key, date(1700, 1, 1), date(2025, 1, 1), limit=10, offset=10
    )
    assert first["has_more"] and first["next_offset"] == 10
    assert (
        first["dataset"]["observations"] + second["dataset"]["observations"]
        == points[:20]
    )
    tail = catalog.observations(
        key, date(1700, 1, 1), date(2025, 1, 1), limit=8, preview=True
    )
    assert (
        tail["dataset"]["observations"] == points[-8:] and tail["next_offset"] is None
    )


def test_fiscal_quarter_metadata_and_events(catalog):
    q = catalog.observations("fixture_catalog_003", date(1960, 1, 1), date(2010, 1, 1))[
        "dataset"
    ]
    assert q["native_calendar"]["year_start_month"] == 4
    assert q["observations"][0]["native_label"] == "1970-Q1"
    assert q["observations"][0]["period_start"] == "1969-04-01"
    e = catalog.observations("fixture_catalog_005", date(2000, 1, 3), date(2000, 1, 3))[
        "dataset"
    ]["observations"]
    assert len(e) == 2 and e[0]["date"] == e[1]["date"] and e[0]["key"] != e[1]["key"]


def test_native_compare_exact_labels_and_mixed_frequency_no_resampling(catalog):
    client = TestClient(v.app)
    base = {
        "datasets": ["fixture_catalog_002", "fixture_catalog_003"],
        "start": "1960-01-01",
        "end": "2015-01-01",
    }
    r = client.post("/api/v2/compare", json=base)
    assert r.status_code == 200, r.text
    body = r.json()
    assert (
        body["statistics"] == []
        and len(body["raw_observations"]["fixture_catalog_002"]) == 120
    )
    assert body["series"][1]["observations"][0]["native_label"] == "1970-Q1"
    assert (
        client.post(
            "/api/v2/compare", json=base | {"alignment": "period_end"}
        ).status_code
        == 422
    )
    r = client.post(
        "/api/v2/compare",
        json={
            "datasets": ["fixture_catalog_002", "fixture_catalog_016"],
            "start": "2000-01-01",
            "end": "2010-01-01",
        },
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["statistics"]) == 1


def test_changes_do_not_skip_missing_native_periods_or_zero_bases():
    points = [
        {"date": d, "value": x}
        for d, x in (
            ("2020-01-01", 10),
            ("2020-03-01", 20),
            ("2020-04-01", 0),
            ("2020-05-01", -1),
        )
    ]
    metadata = {
        "frequency": "monthly",
        "units": "units",
        "allowed_transformations": ["percent"],
    }
    result, _ = transform_native(points, metadata, "percent", 1)
    assert [o["value"] for o in result] == [None, None, -100, None]


@pytest.mark.parametrize(
    "sql",
    [
        "UPDATE norm_datasets SET public_display=0 WHERE id='fixture_catalog_002'",
        "UPDATE norm_datasets SET rights_state='unreviewed' WHERE id='fixture_catalog_002'",
        "UPDATE catalog_scope_reviews SET approved=0 WHERE dataset_id='fixture_catalog_002'",
        "UPDATE catalog_scope_reviews SET reviewed_at='2100-01-01T00:00:00+00:00' WHERE dataset_id='fixture_catalog_002'",
        "UPDATE catalog_dataset_completeness SET state='partial' WHERE dataset_id='fixture_catalog_002'",
        "UPDATE norm_observations SET value=1234 WHERE dataset_id='fixture_catalog_002'",
        "UPDATE norm_pages SET content_hash='bad' WHERE partition_id IN (SELECT id FROM norm_partitions WHERE generation_id='catalog_fixture_catalog_002')",
    ],
)
def test_revoked_permissions_incomplete_and_corrupt_data_fail_closed(
    populated, tmp_path, sql
):
    original, reader = populated
    path = tmp_path / "copy.sqlite3"
    with sqlite3.connect(original.path) as source, sqlite3.connect(path) as target:
        source.backup(target)
        target.execute(sql)
        target.commit()
    copy = NativeReader(path, reader.publications, now_fn=reader.now)
    with pytest.raises(ValueError, match="Unknown dataset"):
        copy.observations("fixture_catalog_002", date(2000, 1, 1), date(2010, 1, 1))
    # Independent AI/Discovery permissions never follow public display.
    with sqlite3.connect(path) as db:
        assert db.execute(
            "SELECT DISTINCT ai_allowed,discovery_allowed FROM norm_datasets"
        ).fetchall() == [(0, 0)]


def test_default_empty_registration_no_migration_or_database_creation(tmp_path):
    path = tmp_path / "absent.sqlite3"
    reader = NativeReader(path)
    assert reader.catalogue() == []
    with pytest.raises(ValueError):
        reader.metadata("wb_copper_monthly")
    assert not path.exists()


def test_backup_restore_preserves_native_reads_and_private_flags(populated, tmp_path):
    store, reader = populated
    path = tmp_path / "restore.sqlite3"
    with sqlite3.connect(store.path) as db, sqlite3.connect(path) as restored:
        db.backup(restored)
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert (
            restored.execute("SELECT count(*) FROM norm_datasets").fetchone()[0] == 279
        )
    restored = NativeReader(path, reader.publications, now_fn=reader.now)
    assert restored.observations(
        "fixture_catalog_002", date(2000, 1, 1), date(2010, 1, 1)
    ) == reader.observations("fixture_catalog_002", date(2000, 1, 1), date(2010, 1, 1))


def test_incremental_revision_does_not_certify_unrelated_old_generations(
    populated, tmp_path
):
    from dataclasses import replace
    from datetime import UTC, datetime

    from backend.app.ingestion.partition_contracts import Window
    from backend.app.ingestion.partitioned import PartitionedIngestion
    from scripts.batch0_partition_fixture import FixtureAdapter, source_points

    original, reader = populated
    path = tmp_path / "revision.sqlite3"
    with sqlite3.connect(original.path) as source, sqlite3.connect(path) as target:
        source.backup(target)
    definition = reader.publications["fixture_catalog_002"].definition
    points = list(source_points(definition))
    points[1] = replace(points[1], value=-42, source_revision="corrected")
    adapter = FixtureAdapter(tuple(points))
    adapter.snapshot = "b" * 64
    engine = PartitionedIngestion(
        Store(path),
        [definition],
        {definition.provider: adapter},
        now_fn=lambda: datetime(2026, 2, 1, tzinfo=UTC),
    )
    engine.create_generation(
        definition.id,
        [Window(date(2000, 1, 1), date(2000, 12, 31))],
        generation_id="new_revision",
    )
    assert engine.run_once()["state"] != "failed"
    updated = NativeReader(path, reader.publications, now_fn=reader.now)
    result = updated.observations(definition.id, date(2000, 1, 1), date(2009, 12, 31))[
        "dataset"
    ]["observations"]
    assert result[1]["value"] == -42 and result[1]["revision"] == 2
    assert len(result) == 120
    with sqlite3.connect(path) as db:
        db.execute(
            "UPDATE catalog_dataset_completeness SET state='partial' WHERE batch_id='catalog_fixture_catalog_002'"
        )
    with pytest.raises(ValueError, match="Unknown dataset"):
        updated.observations(definition.id, date(2001, 1, 1), date(2009, 12, 31))


def test_publication_does_not_grant_ai_or_discovery(catalog, populated, monkeypatch):
    from backend.app.v2 import ai_guard
    from backend.app.v2.ai_guard import AIGuard

    store, _reader = populated
    monkeypatch.setenv("MACROLENS_AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-test-key")
    send = Mock(side_effect=AssertionError("No AI sends allowed"))
    monkeypatch.setattr(ai_guard, "send", send)
    assert (
        AIGuard(store).generate(
            [{"datasets": ["fixture_catalog_002"]}, {"datasets": ["wb_brent_monthly"]}]
        )["generated"]
        == 0
    )
    send.assert_not_called()
    assert not set(catalog.native.publications) & set(v.SPECS)


@pytest.mark.parametrize("horizon", [-1, 0, 253, True])
def test_invalid_native_horizons_never_create_lookahead(horizon):
    with pytest.raises(ValueError, match="horizon"):
        transform_native(
            [],
            {
                "frequency": "monthly",
                "units": "units",
                "allowed_transformations": ["percent"],
            },
            "percent",
            horizon,
        )


def test_native_preview_includes_pre_1990_history(catalog):
    r = TestClient(v.app).get(
        "/api/v2/observations/fixture_catalog_004?preview=true&limit=8"
    )
    assert r.status_code == 200, r.text
    d = r.json()["dataset"]
    assert len(d["observations"]) == 8
    assert d["native_history_start"] == "1800-01-01"
    assert d["latest_native_label"] == "1919"
    assert d["status"] == "stale"


def test_short_reads_are_bounded_without_waiting_for_heavy_discovery(catalog):
    with v.analytical_workload.enter():
        assert TestClient(v.app).get("/api/v2/catalog?limit=3").status_code == 200
        with v.catalog_reads.enter(), v.catalog_reads.enter():
            rejected = TestClient(v.app).get("/api/v2/catalog?limit=3")
            assert (
                rejected.status_code == 503 and rejected.headers["retry-after"] == "2"
            )
    assert TestClient(v.app).get("/api/v2/catalog?limit=3").status_code == 200


def test_mixed_native_comparison_delegates_existing_legacy_calculations(catalog):
    from backend.app.v2.native_compare import compare_native

    response = {
        "series": [
            {
                "id": "payrolls",
                "observations": [],
                "transformation": "jobs",
                "units": "Net jobs",
            }
        ],
        "datasets": [catalog.metadata("payrolls")],
        "raw_observations": {"payrolls": []},
    }
    calculate = Mock(return_value=SimpleNamespace(model_dump=lambda: response))
    req = v.ComparisonRequest(
        datasets=["payrolls", "fixture_catalog_002"],
        transformations={"payrolls": "jobs"},
        start="2000-01-01",
        end="2009-12-31",
    )
    result = compare_native(catalog, req, calculate)
    assert result["series"][0]["units"] == "Net jobs"
    assert calculate.call_args.args[0].datasets == ["payrolls"]
    assert calculate.call_args.args[0].transformations == {"payrolls": "jobs"}


def test_missing_native_schema_does_not_break_legacy_catalog(catalog, tmp_path):
    reader = NativeReader(tmp_path / "missing.sqlite3", catalog.native.publications)
    assert PublicCatalog(catalog.legacy, catalog.stored, reader).page()["total"] == 30
    assert not reader.path.exists()


def test_legacy_metadata_and_observations_share_one_revision(tmp_path):
    from contextlib import contextmanager
    from datetime import UTC, datetime

    store = Store(tmp_path / "cache.sqlite3")
    original = v.Dataset(
        **v.SPECS["cpi"].__dict__,
        status="stale",
        message="SYNTHETIC",
        observations=[
            {"date": "2020-01-01", "value": 1},
            {"date": "2020-02-01", "value": 2},
        ],
        latest_value=2,
    )
    revised = original.model_copy(
        update={
            "latest_value": 999,
            "observations": [v.Observation(date="2020-02-01", value=999)],
        }
    )
    with store.connection(True) as db:
        db.execute(
            "INSERT INTO source_cache VALUES(?,?,?,?,?)",
            (
                "cpi",
                original.model_dump_json(),
                "2026-01-01T00:00:00+00:00",
                "2100-01-01T00:00:00+00:00",
                0,
            ),
        )
    changed = [False]

    @contextmanager
    def concurrent_connection():
        with store.connection() as db:

            class Proxy:
                def execute(self, sql, args=()):
                    result = db.execute(sql, args)
                    if "json_remove" in sql and not changed[0]:
                        changed[0] = True
                        with store.connection(True) as writer:
                            writer.execute(
                                "UPDATE source_cache SET payload=? WHERE id='cpi'",
                                (revised.model_dump_json(),),
                            )
                    return result

            yield Proxy()

    legacy = SimpleNamespace(
        store=SimpleNamespace(connection=concurrent_connection),
        today_fn=lambda: date(2026, 2, 1),
        now_fn=lambda: datetime(2026, 2, 1, tzinfo=UTC),
    )
    catalog = PublicCatalog(legacy, v.service.reader, NativeReader(store.path))
    page = catalog.observations("cpi", date(2020, 1, 1), date(2020, 12, 31))["dataset"]
    assert page["latest_value"] == page["observations"][-1]["value"] == 2
    page = catalog.observations("cpi", date(2020, 1, 1), date(2020, 12, 31))["dataset"]
    assert page["latest_value"] == page["observations"][-1]["value"] == 999
