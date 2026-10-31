"""Official parser, immutable checkpoint and additive release privacy regressions."""

import io
import json
import sqlite3
import zipfile
from datetime import UTC, date, datetime

import pytest

from backend.app.catalog.release_cli import ingest
from backend.app.catalog.releases import activate, candidates, migrate
from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.expansion_sources import (
    parse_bls,
    parse_ons,
    workbook_number,
)
from backend.app.ingestion.federal_reserve_bulk import parse_selected
from backend.app.ingestion.native import Definition, Observation, SourceCalendar
from backend.app.ingestion.official_snapshots import SnapshotAdapter, freeze, safe_url
from backend.app.ingestion.partition_contracts import Bounds, Window
from backend.app.ingestion.partition_schema import migrate as native_migrate
from backend.app.ingestion.partitioned import PartitionedIngestion
from backend.app.v2.native_reader import NativePublication, NativeReader
from backend.app.v2.state import Store


def fixture(tmp_path):
    store = Store(tmp_path / "disposable.sqlite3")
    with store.connection(True) as db:
        native_migrate(db)
        migrate(db)
    d = Definition(
        "release_example",
        "ons",
        "ABC/example",
        "Percent",
        "monthly",
        "NSA",
        SourceCalendar("months"),
    )
    p = NativePublication(
        d,
        "Example",
        "Macro",
        "UK",
        "https://www.ons.gov.uk/example",
        "https://www.ons.gov.uk/help/terms-conditions",
        ("ONS",),
        "TEST_ONLY_NOT_REAL_RIGHTS",
    )
    return store, d, p


def test_snapshot_pages_preserve_negative_zero_missing_and_detect_tampering(tmp_path):
    _, d, p = fixture(tmp_path)
    points = tuple(
        Observation(f"2020-0{i + 1}", f"2020-0{i + 1}", v)
        for i, v in enumerate([-2, 0, None, 4])
    )
    path, key = freeze(tmp_path, d, points, b"official fixture bytes", p.source_url)
    adapter = SnapshotAdapter(path, key)
    page = adapter.fetch(
        d, Window(date(2020, 1, 1), date(2020, 12, 31)), None, Bounds(records=2)
    )
    assert [p.value for p in page.points] == [-2, 0]
    assert page.next_cursor == "2"
    following = adapter.fetch(
        d,
        Window(date(2020, 1, 1), date(2020, 12, 31)),
        page.next_cursor,
        Bounds(records=2),
    )
    assert [p.value for p in following.points] == [None, 4]
    assert following.next_cursor is None
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ProviderError, match="snapshot_changed"):
        adapter.fetch(d, Window(date(2020, 1, 1), date(2020, 12, 31)), None, Bounds())


def test_display_grant_requires_receipt_and_does_not_enable_other_scopes(tmp_path):
    store, d, p = fixture(tmp_path)
    reader = NativeReader(store.path, {d.id: p})
    with pytest.raises(ValueError):
        reader.metadata(d.id)
    with store.connection(True) as db, pytest.raises(ValueError):
        activate(db, p, reader, approved=False)
    path, key = freeze(
        tmp_path,
        d,
        (Observation("2020-01", "January 2020", 0),),
        b"fixture",
        p.source_url,
    )
    assert ingest(store, p, path, key)["state"] == "complete"
    assert ingest(store, p, path, key)["state"] == "unchanged"
    with pytest.raises(ValueError):
        reader.metadata(d.id)
    with store.connection(True) as db:
        activate(db, p, reader, approved=True)
        assert tuple(
            db.execute(
                "SELECT public_display,ai_allowed,discovery_allowed,rights_state FROM norm_datasets"
            ).fetchone()
        ) == (0, 0, 0, "unreviewed")
        assert (
            db.execute(
                "SELECT count(*) FROM catalog_scope_reviews WHERE scope IN ('ai','discovery') AND approved=1"
            ).fetchone()[0]
            == 0
        )
    assert (
        reader.observations(d.id, date(2020, 1, 1), date(2020, 12, 31))["dataset"][
            "observations"
        ][0]["value"]
        == 0
    )
    with store.connection(True) as db:
        db.execute("UPDATE catalog_release_grants SET public_display=0")
    with pytest.raises(ValueError):
        reader.metadata(d.id)


def test_additive_migration_backup_restore_preserves_legacy_checks(tmp_path):
    store, _, _ = fixture(tmp_path)
    with store.connection(True) as db:
        db.execute(
            "INSERT INTO library VALUES('old','Old save','2020-01-01','{}','keep')"
        )
        before = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='norm_datasets'"
        ).fetchone()[0]
        migrate(db)
        assert (
            db.execute(
                "SELECT sql FROM sqlite_master WHERE name='norm_datasets'"
            ).fetchone()[0]
            == before
        )
        assert (
            db.execute("SELECT count(*) FROM catalog_release_grants").fetchone()[0] == 0
        )
    with (
        store.connection() as db,
        sqlite3.connect(tmp_path / "backup.sqlite3") as backup,
    ):
        db.backup(backup)
        with sqlite3.connect(tmp_path / "restored.sqlite3") as restored:
            backup.backup(restored)
            assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert restored.execute("SELECT notes FROM library").fetchone()[0] == "keep"


@pytest.mark.parametrize(
    "url",
    [
        "http://www.ons.gov.uk/a",
        "https://evil.invalid/a",
        "https://user:password@www.ons.gov.uk/a",
        "https://www.ons.gov.uk:444/a",
    ],
)
def test_official_transport_rejects_unapproved_destinations(url):
    with pytest.raises(ProviderError):
        safe_url(url)


def test_bls_annual_summary_is_not_a_fake_month_and_footnotes_survive():
    entry = {
        "id": "fixture_bls",
        "source": {"provider": "bls", "selector": "TEST"},
        "frequency": "monthly",
        "units": "Thousands",
        "seasonal_adjustment": "NSA",
    }
    data = {
        "status": "REQUEST_SUCCEEDED",
        "Results": {
            "series": [
                {
                    "seriesID": "TEST",
                    "data": [
                        {
                            "year": "2020",
                            "period": "M01",
                            "value": "-2",
                            "footnotes": [{"code": "P", "text": "Preliminary"}],
                        },
                        {"year": "2020", "period": "M13", "value": "100"},
                    ],
                }
            ]
        },
    }
    d, points, _ = parse_bls(entry, json.dumps(data).encode())
    assert (
        len(points) == 1
        and points[0].value == -2
        and points[0].flags == ("P=Preliminary",)
    )
    assert points[0].validated(d, datetime(2021, 1, 1, tzinfo=UTC)).key == "2020-01"


def test_ons_pound_preunit_is_not_dropped_and_cdid_must_match():
    entry = {
        "id": "fixture_ons",
        "source": {"provider": "ons", "selector": "KAI7/LMS"},
        "frequency": "monthly",
        "units": "GBP",
        "seasonal_adjustment": "SA",
    }
    data = {
        "description": {"cdid": "KAI7", "unit": "", "preUnit": "£"},
        "months": [{"date": "2020 JAN", "value": "500"}],
    }
    d, points, _ = parse_ons(entry, json.dumps(data).encode())
    assert d.units == "£" and points[0].value == 500
    data["description"]["cdid"] = "WRONG"
    with pytest.raises(ValueError):
        parse_ons(entry, json.dumps(data).encode())


def test_fed_xml_month_end_is_native_month_and_units_are_pinned():
    entry = {
        "id": "fixture_fed",
        "source": {"provider": "federal_reserve", "selector": "H6/M2.M"},
        "frequency": "monthly",
        "units": "Billions",
        "seasonal_adjustment": "SA",
        "expected_source_attributes": {"FREQ": "129", "UNIT_MULT": "1e+09"},
    }
    xml = b'<root><Series SERIES_NAME="M2.M" FREQ="129" UNIT_MULT="1e+09"><Obs TIME_PERIOD="2020-02-29" OBS_VALUE="0" OBS_STATUS="A"/></Series></root>'
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        z.writestr("H6_data.xml", xml)
    _, points, _ = parse_selected(entry, output.getvalue())
    assert points[0].period == "2020-02" and points[0].label == "2020-02-29"
    entry["expected_source_attributes"]["UNIT_MULT"] = "1000"
    with pytest.raises(ValueError):
        parse_selected(entry, output.getvalue())


def test_reviewed_candidates_never_shadow_public_or_private_pilots():
    from backend.app.v2.definitions import SPECS

    reviewed = candidates()
    assert not set(reviewed) & set(SPECS)
    assert not set(reviewed) & {
        "wb_brent_monthly",
        "wb_copper_monthly",
        "wb_iron_ore_monthly",
    }
    assert len(reviewed) >= 150


def test_generation_capacity_increase_is_explicit_and_bounded(tmp_path):
    store, d, _ = fixture(tmp_path)
    assert (
        PartitionedIngestion(store, [d], {"ons": object()}).max_generation_rows == 10000
    )
    for limit in [True, 0, 50001]:
        with pytest.raises(ValueError):
            PartitionedIngestion(
                store, [d], {"ons": object()}, max_generation_rows=limit
            )
    with pytest.raises(ValueError):
        PartitionedIngestion(
            store, [d], {"ons": object()}, max_storage_bytes=385 * 1024 * 1024
        )


def test_revisions_and_source_proofs_survive_staging_compaction(tmp_path):
    store, d, p = fixture(tmp_path)
    reader = NativeReader(store.path, {d.id: p})
    for value in (2, -3):
        path, key = freeze(
            tmp_path,
            d,
            (Observation("2020-01", "January 2020", value),),
            str(value).encode(),
            p.source_url,
        )
        assert ingest(store, p, path, key)["state"] == "complete"
    with store.connection(True) as db:
        activate(db, p, reader, approved=True)
        assert db.execute("SELECT count(*) FROM norm_revisions").fetchone()[0] == 1
        assert (
            db.execute("SELECT DISTINCT payload FROM norm_staged").fetchall()[0][0]
            == ""
        )
    assert (
        reader.observations(d.id, date(2020, 1, 1), date(2020, 12, 31))["dataset"][
            "observations"
        ][0]["value"]
        == -3
    )
    with store.connection(True) as db:
        row = db.execute("SELECT payload FROM norm_observations").fetchone()[0]
        payload = json.loads(row)
        payload["value"] = 99
        db.execute(
            "UPDATE norm_observations SET value=99,payload=?", (json.dumps(payload),)
        )
    with pytest.raises(ValueError):
        reader.observations(d.id, date(2020, 1, 1), date(2020, 12, 31))


@pytest.mark.parametrize("value", ["[x]", "[c]", "[z]", None])
def test_source_missing_markers_are_never_zero(value):
    assert workbook_number(value) is None


def test_bls_backfill_windows_are_disjoint_and_keep_source_hashes():
    from backend.app.ingestion.bls_history import capture

    seen = []

    def fetch(_url, *, payload):
        request = json.loads(payload)
        seen.append(request)
        year = request["startyear"]
        body = json.dumps(
            {
                "status": "REQUEST_SUCCEEDED",
                "Results": {
                    "series": [
                        {
                            "seriesID": "A",
                            "data": [{"year": year, "period": "M01", "value": "0"}],
                        }
                    ]
                },
            }
        ).encode()
        return body, {}

    raw, metadata = capture(
        ["A"], start=2000, end=2026, fetch=fetch, pause=lambda _: None
    )
    assert [(r["startyear"], r["endyear"]) for r in seen] == [
        ("2000", "2009"),
        ("2010", "2019"),
        ("2020", "2026"),
    ]
    assert len(metadata["source_windows"]) == 3
    assert len(json.loads(raw)["Results"]["series"][0]["data"]) == 3


def test_bls_backfill_failure_does_not_publish_a_partial_response():
    from backend.app.ingestion.bls_history import capture

    def fetch(_url, *, payload):
        return b'{"status":"REQUEST_NOT_PROCESSED"}', {}

    with pytest.raises(ProviderError, match="bls_history_request_failed"):
        capture(["A"], start=2020, end=2026, fetch=fetch, pause=lambda _: None)
