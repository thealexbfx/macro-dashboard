import csv
import io
from datetime import UTC, datetime, timedelta

import pytest

from backend.app.ingestion.catalog_refresh import CatalogRefresh
from backend.app.ingestion.official_snapshots import safe_url, download
from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.g7_cpi import JP_LIST, JP_TITLE, configuration
from scripts.g7_cpi_refresh import open_workspace, report


def test_native_cpi_refresh_preserves_last_good_and_revisions(tmp_path):
    now = datetime.now(UTC)
    store = open_workspace(tmp_path / "private", initialize=True)
    rules, publications, entries = configuration()
    key = "jp_cpi_all_items_2025_nsa"
    state = {"edition": 0, "tail": 9, "value": "100.0"}

    def fetch(url, **kwargs):
        if url == JP_LIST:
            return f'<a href="?stat_infid=000040482945">{JP_TITLE}</a>'.encode(), {}
        if "stat_infid" in url:
            return (
                f"<td>2025-Base Consumer Price Index</td><th>Survey date</th>"
                f"<td>2025 {['Sep.', 'Oct.'][state['tail'] == 10]}</td>"
                f"<th>Published date and time</th>"
                f"<td>2025-{state['tail'] + 1:02d}-23 08:30</td>"
            ).encode(), {}
        if state["edition"] == 1:
            assert kwargs["validators"]["etag"] == '"initial"'
            return None, {"not_modified": True, "etag": '"initial"'}
        if state["edition"] == 2:
            raise ProviderError("http_429", retry_after=900)
        rows = [
            ["Japanese heading", "Japanese label"],
            ["Group/Item", "All items"],
            ["(Group/Item code)", "0001"],
            ["Serial number", "001"],
            ["Weight", "1"],
            ["Weight per 10000", "10000"],
        ]
        first = 1970 * 12 + (state["edition"] == 3)
        rows.extend(
            [f"{m // 12:04d}{m % 12 + 1:02d}", state["value"] if m == first else "100.0"]
            for m in range(first, 2025 * 12 + state["tail"])
        )
        out = io.StringIO(newline="")
        csv.writer(out).writerows(rows)
        return out.getvalue().encode("cp932"), {"etag": '"initial"'}

    worker = CatalogRefresh(
        store, fetch=fetch, now=lambda: now,
        private_sources=({key: rules[key]}, {key: publications[key]}, {key: entries[key]}),
    )
    assert worker.run_once()["state"] == "changed"
    baseline = report(store)
    now += timedelta(days=1)
    state["edition"] = 1
    assert worker.run_once()["state"] == "unchanged"
    assert report(store) == baseline
    now += timedelta(days=1)
    state["edition"] = 2
    assert worker.run_once()["error_code"] == "http_429"
    assert worker.status()[0]["next_due"] >= now.timestamp() + 900
    assert worker.run_once()["state"] == "idle"
    assert report(store) == baseline
    now += timedelta(hours=1)
    state["edition"] = 3
    assert worker.run_once()["error_code"] == "cpi_history_coverage_mismatch"
    assert report(store) == baseline
    now += timedelta(hours=1)
    state.update(edition=4, tail=10, value="99.9")
    assert worker.run_once()["state"] == "changed"
    updated = report(store)[0]
    assert updated["last_period"] == "2025-10"
    assert updated["revisions"] == 1
    with store.connection() as db:
        assert db.execute("SELECT count(*) FROM catalog_release_grants").fetchone()[0] == 0
        assert db.execute("SELECT value FROM norm_observations WHERE period_key='1970-01'").fetchone()[0] == 99.9
        assert '"value":100.0' in db.execute("SELECT old_payload FROM norm_revisions").fetchone()[0]


def test_development_cli_requires_initialized_workspace(tmp_path):
    with pytest.raises(ValueError, match="dedicated initialized"):
        open_workspace(tmp_path)


def test_official_cpi_allowlist_is_exact_and_https_only():
    for url in (
        "https://www150.statcan.gc.ca/n1/tbl/csv/18100004-eng.zip",
        "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401",
        JP_LIST,
        "https://www.e-stat.go.jp/en/stat-search/files?stat_infid=1234",
    ):
        assert safe_url(url) == url
    for url in (
        "http://www150.statcan.gc.ca/n1/tbl/csv/18100004-eng.zip",
        "https://www150.statcan.gc.ca.evil.example/n1/tbl/csv/18100004-eng.zip",
        "https://www.e-stat.go.jp.evil.example/en/stat-search/files",
        "https://www.e-stat.go.jp:444/en/stat-search/files",
        "https://www.e-stat.go.jp/en/stat-search/files?token=secret",
    ):
        with pytest.raises(ProviderError, match="unapproved_official_host"):
            safe_url(url)


def test_statcan_large_zip_budget_is_restricted_to_exact_table_path():
    class Response(io.BytesIO):
        headers = {}
        def geturl(self):
            return "https://www150.statcan.gc.ca/n1/tbl/csv/18100004-eng.zip"

    class Opener:
        def open(self, request, timeout=None):
            return Response(b"test-bytes")

    body, _ = download(
        "https://www150.statcan.gc.ca/n1/tbl/csv/18100004-eng.zip",
        maximum=32 * 1024**2, opener=Opener(),
    )
    assert body == b"test-bytes"
    with pytest.raises(ValueError, match="Unsafe download bounds"):
        download(JP_LIST, maximum=32 * 1024**2, opener=Opener())

    # Both exact Canadian CPI bulk tables may use the larger budget; a
    # near-match, a different publisher and a query-string variant may not.
    class CanadianResponse(io.BytesIO):
        headers = {}
        def __init__(self, url):
            super().__init__(b"fixture")
            self.url = url
        def geturl(self):
            return self.url

    class CanadianOpener:
        def open(self, request, timeout=None):
            return CanadianResponse(request.full_url)

    for pid in ("18100004", "18100256"):
        url = f"https://www150.statcan.gc.ca/n1/tbl/csv/{pid}-eng.zip"
        body, _ = download(url, maximum=32 * 1024**2, opener=CanadianOpener())
        assert body == b"fixture"
    for url in (
        "https://www150.statcan.gc.ca/n1/tbl/csv/18100005-eng.zip",
        "https://www150.statcan.gc.ca/n1/tbl/csv/18100004-eng.zip?version=2",
        "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401",
    ):
        with pytest.raises(ValueError, match="Unsafe download bounds"):
            download(url, maximum=32 * 1024**2, opener=CanadianOpener())


def test_staged_publisher_release_timestamps_hash_and_paginate(tmp_path):
    from datetime import date
    from backend.app.ingestion.native import Observation
    from backend.app.ingestion.official_snapshots import SnapshotAdapter, freeze
    from backend.app.ingestion.partition_contracts import Bounds, Window

    publication = configuration()[1]["jp_cpi_all_items_2025_nsa"]
    released = datetime(2020, 10, 23, tzinfo=UTC)
    point = Observation("2020-09", "202009", 98.4, release_at=released)
    path, digest = freeze(
        tmp_path, publication.definition, [point], b"synthetic source fixture",
        publication.source_url,
    )
    adapter = SnapshotAdapter(path, digest)
    window = Window(date(2020, 1, 1), date(2020, 12, 31))
    page = adapter.fetch(publication.definition, window, None, Bounds())
    assert page.points == (point,)
    assert page.next_cursor is None
    assert len(page.content_hash) == 64
    assert adapter.fetch(publication.definition, window, None, Bounds()).content_hash == page.content_hash
