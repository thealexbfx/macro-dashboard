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
    for publication in reviewed.values():
        if publication.definition.provider == "eurostat":
            assert any(
                "Eurostat bears no responsibility" in note
                and "MacroLens calculations" in note
                for note in publication.limitations
            )
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
            store, [d], {"ons": object()}, max_storage_bytes=513 * 1024 * 1024
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
        assert db.execute("SELECT count(*) FROM norm_staged").fetchone()[0] == 0
        assert (
            db.execute("SELECT count(*) FROM catalog_staging_receipts").fetchone()[0]
            == 2
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


def test_boe_metadata_blank_lines_and_stock_adjustment_are_source_native():
    from backend.app.ingestion.expansion_sources import parse_boe

    e = {
        "id": "fixture_boe",
        "frequency": "monthly",
        "units": "GBP million",
        "seasonal_adjustment": "SA",
        "source": {"provider": "boe", "selector": "LPMBC69"},
    }
    raw = b"SERIES,DESCRIPTION\r\nLPMBC69,Monthly amounts outstanding of M4 lending (in sterling millions) seasonally adjusted\r\n\r\n\r\nDATE,SERIES,VALUE\r\n31 Jan 2020,LPMBC69,0\r\n29 Feb 2020,LPMBC69,-2\r\n"
    d, points, metadata = parse_boe(e, raw)
    assert d.adjustment == "Seasonally adjusted" and [p.value for p in points] == [
        0,
        -2,
    ]
    assert points[1].period == "2020-02" and points[1].label == "29 Feb 2020"
    assert "Amounts outstanding" in metadata["scope"]
    with pytest.raises(ValueError):
        parse_boe(e, b"<html>Error: From date before 1963</html>")


def test_bls_dash_is_missing_not_negative_or_zero():
    entry = {
        "id": "fixture_cps",
        "frequency": "monthly",
        "units": "Percent",
        "seasonal_adjustment": "SA",
        "source": {"provider": "bls", "selector": "LNS12300000"},
        "definition_note": "CPS people, not CES payroll jobs",
    }
    body = {
        "status": "REQUEST_SUCCEEDED",
        "Results": {
            "series": [
                {
                    "seriesID": "LNS12300000",
                    "data": [
                        {"year": "2020", "period": "M01", "value": "-"},
                        {"year": "2020", "period": "M02", "value": "-1"},
                        {"year": "2020", "period": "M03", "value": "0"},
                    ],
                }
            ]
        },
    }
    _, points, metadata = parse_bls(entry, json.dumps(body).encode())
    assert [p.value for p in points] == [None, -1, 0]
    assert metadata["definition_note"] == entry["definition_note"]


def test_fed_weekly_assets_preserve_wednesday_calendar():
    entry = {
        "id": "fixture_assets",
        "frequency": "weekly",
        "units": "Millions USD",
        "seasonal_adjustment": "NSA",
        "week_ending": 2,
        "source": {"provider": "federal_reserve", "selector": "H41/RESPPMA_N.WW"},
        "expected_source_attributes": {"FREQ": "19", "UNIT": "Currency"},
    }
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "H41_data.xml",
            '<root><Series SERIES_NAME="RESPPMA_N.WW" FREQ="19" UNIT="Currency"><Obs TIME_PERIOD="2020-01-01" OBS_VALUE="0"/></Series></root>',
        )
    d, points, _ = parse_selected(entry, output.getvalue())
    assert d.calendar.week_ending == 2
    assert points[0].validated(d, datetime(2021, 1, 1, tzinfo=UTC)).key == "2020-01-01"
    entry["week_ending"] = 4
    d, points, _ = parse_selected(entry, output.getvalue())
    with pytest.raises(ValueError):
        points[0].validated(d, datetime(2021, 1, 1, tzinfo=UTC))


def test_larger_download_budget_is_limited_to_named_board_archives():
    from backend.app.ingestion.official_snapshots import download

    for url in (
        "https://www.ons.gov.uk/test",
        "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&filetype=zip",
        "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H41&filetype=xml",
    ):
        with pytest.raises(ValueError, match="Unsafe download bounds"):
            download(url, maximum=16 * 1024 * 1024)


def xlsx_fixture(sheet, rows):
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.active.title = sheet
    for row in rows:
        workbook.active.append(row)
    stream = io.BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def test_census_housing_pins_national_one_unit_saar_not_total_or_nsa():
    from backend.app.ingestion.expansion_sources import parse_census_construction

    e = {
        "id": "fixture_housing",
        "frequency": "monthly",
        "units": "Thousands",
        "seasonal_adjustment": "SA",
        "source": {"provider": "census", "selector": "NRC/starts/US/1unit/SAAR"},
    }
    rows = [
        ["New Privately-Owned Housing Units Started"],
        ["Thousands of units"],
        [],
        ["Seasonally adjusted annual rate"],
        ["Month", "United States"],
        [None, "Total", "1 unit"],
        [datetime(2020, 1, 1), 2000, 1000],
    ]
    d, points, _ = parse_census_construction(
        e, xlsx_fixture("Seasonally Adjusted", rows)
    )
    assert d.units == "Thousands of units, annual rate" and points[0].value == 1000
    rows[5][2] = "5 units or more"
    with pytest.raises(ValueError, match="definition/units/column"):
        parse_census_construction(e, xlsx_fixture("Seasonally Adjusted", rows))


def test_m3_native_code_does_not_splice_sic_or_fill_template_months():
    from backend.app.ingestion.expansion_sources import parse_census_construction

    e = {
        "id": "fixture_orders",
        "frequency": "monthly",
        "units": "USD",
        "seasonal_adjustment": "SA",
        "source": {"provider": "census", "selector": "M3/AMDMNO"},
    }
    raw = xlsx_fixture(
        "m3-outp-nop",
        [
            ["AMDMNO", 2020, None, 0, None, -2] + [None] * 8,
            ["UMDMNO", 2020] + [999] * 12,
        ],
    )
    d, points, metadata = parse_census_construction(e, raw)
    assert [p.period for p in points] == ["2020-02", "2020-03", "2020-04"]
    assert [p.value for p in points] == [0, None, -2]
    assert (
        d.units == "Millions of US dollars"
        and "no SIC splice" in metadata["revision_note"]
    )


def test_dol_exact_adjustment_saturday_and_unpublished_templates():
    from backend.app.ingestion.expansion_sources import parse_dol_claims

    e = {
        "id": "fixture_claims",
        "frequency": "weekly",
        "units": "Number",
        "week_ending": 5,
        "seasonal_adjustment": "SA",
        "source": {"provider": "dol", "selector": "r539cyNational/ContinuedClaims/SA"},
        "query_parameters": {"level": "us"},
    }
    raw = b'<r539cyNational rundate="10/31/2026"><week><weekEnded>01/04/2020</weekEnded><ContinuedClaims><NSA>999</NSA><SA>1,234</SA></ContinuedClaims></week><week><weekEnded>01/11/2020</weekEnded><ContinuedClaims><SA>&#160;</SA></ContinuedClaims></week><week><weekEnded>01/18/2020</weekEnded><ContinuedClaims><SA>0</SA></ContinuedClaims></week><week><weekEnded>12/26/2099</weekEnded><ContinuedClaims><SA>&#160;</SA></ContinuedClaims></week></r539cyNational>'
    d, points, _ = parse_dol_claims(e, raw)
    assert [p.value for p in points] == [1234, None, 0]
    for p in points:
        p.validated(d, datetime(2021, 1, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="Unsafe DOL XML"):
        parse_dol_claims(e, b"<!DOCTYPE root>" + raw)


def test_dol_post_cannot_be_repurposed_for_nonstatistical_forms():
    from backend.app.ingestion.official_snapshots import download

    class NoNetwork:
        def open(self, *_args, **_kwargs):
            raise AssertionError("Invalid query reached network")

    with pytest.raises(ValueError, match="Unapproved DOL statistical query"):
        download(
            "https://oui.doleta.gov/unemploy/wkclaims/report.asp",
            payload=b"level=state",
            opener=NoNetwork(),
        )
    with pytest.raises(ValueError, match="Only bounded official"):
        download(
            "https://oui.doleta.gov/other", payload=b"level=us", opener=NoNetwork()
        )


def test_first_release_has_exact_reviewed_definitions_and_no_implicit_grants():
    from dataclasses import asdict

    from scripts.smoke_first_release import SELECTION

    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    assert len(selection["ids"]) == len(set(selection["ids"])) == 13
    assert not any(
        selection[k]
        for k in (
            "production_approved",
            "public_display_default",
            "ai_allowed",
            "discovery_allowed",
        )
    )
    reviewed = candidates()
    for row in selection["datasets"]:
        publication = reviewed[row["id"]]
        assert publication.definition.provider in {"eurostat", "ons", "eia"}
        assert row["definition"] == json.loads(
            json.dumps(asdict(publication.definition))
        )
        assert row["attribution"] == list(publication.attribution)
        assert row["license_url"] == publication.license_url
        assert row["rights_basis"]
        if publication.definition.provider == "eia":
            assert row["publication_evidence"]["date"] in {"2026-10-28", "2026-10-29"}
            assert row["publication_evidence"]["date"] in row["attribution"][0]
