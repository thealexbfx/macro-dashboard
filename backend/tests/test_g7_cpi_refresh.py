import csv
import io
from datetime import UTC, datetime, timedelta

import pytest

from backend.app.ingestion.catalog_refresh import CatalogRefresh
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
