"""Synthetic/disposable audit evidence only. No production or provider access."""

import csv
import json
import socket
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from backend.app.catalog import readiness as audit
from backend.app.v2.definitions import SPECS

NOW = datetime(2026, 11, 3, 12, tzinfo=UTC)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("Audit attempted network access")

    monkeypatch.setattr(socket.socket, "connect", denied)


def points(frequency="monthly", count=140):
    aliases = {
        "daily": "B",
        "weekly": "W-FRI",
        "monthly": "MS",
        "quarterly": "QS",
        "annual": "YS",
    }
    return [
        {"date": d.date().isoformat(), "value": float(100 + n % 17 + n / 10)}
        for n, d in enumerate(
            pd.date_range("2000-01-01", periods=count, freq=aliases[frequency])
        )
    ]


def database(tmp_path, observations=None, release=None):
    path = tmp_path / "data" / "state.sqlite3"
    path.parent.mkdir()
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE source_cache (id TEXT PRIMARY KEY,payload TEXT,checked_at TEXT,next_due TEXT,failures INTEGER)"
        )
        payload = {
            "observations": observations if observations is not None else points(),
            "release_metadata": release or {},
            "retrieved_at": NOW.isoformat(),
            "revision_count": 0,
        }
        db.execute(
            "INSERT INTO source_cache VALUES(?,?,?,?,?)",
            (
                "cpi",
                json.dumps(payload),
                NOW.isoformat(),
                (NOW + timedelta(days=1)).isoformat(),
                0,
            ),
        )
    return path


def test_all_legacy_ids_missing_cache_remain_visible_and_no_network_or_writes(tmp_path):
    path = database(tmp_path)
    before = path.read_bytes()
    report = audit.audit(path, expected_public=194, evidence_origin="fixture", now=NOW)
    assert len(report["datasets"]) == len(SPECS) == 30
    assert not report["scope"]["matches_expected"]
    assert report["scope"]["all_enumerated_public_ids_evaluated"]
    assert report["summary"]["verified_successful_source_checks"] == 0
    cpi = next(r for r in report["datasets"] if r["id"] == "cpi")
    assert cpi["refresh"]["configured"]
    assert not cpi["refresh"]["successful_source_check_verified"]
    assert cpi["existing_documentary_suitability_review"]["revision_methodology"]
    assert (
        cpi["research_suitability"]["historical_relationships"]["status"]
        == "eligible_with_limitations"
    )
    assert path.read_bytes() == before
    assert not Path(str(path) + "-journal").exists()


@pytest.mark.parametrize("frequency", list(audit.MINIMA))
def test_frequency_specific_sufficiency(frequency):
    count = audit.MINIMA[frequency][2]
    # Annual 20 observations are enough; 20 monthly observations are not.
    history, _ = audit.summarize_history(points(frequency, count), frequency, NOW)
    result = audit.capabilities(history, frequency, True)
    assert result["historical_relationships"]["status"] == "eligible_with_limitations"
    history["longest_complete_run"] = count - 1
    assert (
        audit.capabilities(history, frequency, True)["historical_relationships"][
            "status"
        ]
        == "insufficient_or_unsupported"
    )


def test_internal_gaps_nulls_and_duplicate_periods():
    original = points(count=140)
    original.pop(70)
    original[90]["value"] = None
    history, issues = audit.summarize_history(original, "monthly", NOW)
    assert history["expected_periods"] == 140
    assert history["absent_periods"] == history["null_value_count"] == 1
    assert history["longest_complete_run"] == 70
    assert "history_gaps" in {x["code"] for x in issues}
    original.append(original[0])
    history, _ = audit.summarize_history(original, "monthly", NOW)
    assert history["duplicate_period_count"] == 1
    assert (
        audit.capabilities(history, "monthly", True)["comparisons"]["status"]
        == "insufficient_or_unsupported"
    )


@pytest.mark.parametrize("value", [True, "1.2", float("inf"), float("nan")])
def test_invalid_values(value):
    history, _ = audit.summarize_history(
        [{"date": "2026-01-01", "value": value}], "monthly", NOW
    )
    assert history["invalid_count"] == 1


def test_existing_legacy_definition_validation_reused():
    rows = [{"date": "2026-01-02", "value": -2.0}]
    history, issues = audit.summarize_history(rows, "monthly", NOW, spec=SPECS["cpi"])
    assert history["invalid_count"]
    assert any(x["code"] == "legacy_definition_validation_failed" for x in issues)


def test_daily_calendar_respects_weekends_holidays_and_actual_source_values():
    rows = [
        {"date": d, "value": 100.0 + n}
        for n, d in enumerate(("2026-07-02", "2026-07-06", "2026-07-07"))
    ]
    history, _ = audit.summarize_history(rows, "daily", NOW, spec=SPECS["sp500"])
    assert history["expected_periods"] == 3
    assert history["absent_periods"] == 0
    rows.insert(1, {"date": "2026-07-03", "value": 100.5})
    history, _ = audit.summarize_history(rows, "daily", NOW, spec=SPECS["sp500"])
    assert history["expected_periods"] == 4


def test_irregular_and_constant_series_not_certified_for_anomalies():
    history, _ = audit.summarize_history(points(), "irregular", NOW)
    assert history["expected_periods"] is None
    assert (
        audit.capabilities(history, "irregular", True)["comparisons"]["status"]
        == "insufficient_or_unsupported"
    )
    rows = points()
    for p in rows:
        p["value"] = 5.0
    history, _ = audit.summarize_history(rows, "monthly", NOW)
    result = audit.capabilities(history, "monthly", True)
    assert result["comparisons"]["status"] == "eligible_with_limitations"
    assert result["anomaly_detection"]["status"] == "insufficient_or_unsupported"


def test_success_is_not_configuration_or_change_and_future_success_invalid(tmp_path):
    path = database(
        tmp_path,
        release={
            "source_check_succeeded": True,
            "last_source_success_at": NOW.isoformat(),
        },
    )
    report = audit.audit(path, evidence_origin="fixture", now=NOW)
    cpi = next(r for r in report["datasets"] if r["id"] == "cpi")
    refresh = cpi["refresh"]
    assert refresh["successful_source_check_verified"]
    assert refresh["last_observed_change"] is None
    assert refresh["new_observations_ingested"] == "not_separately_recorded"
    assert refresh["historical_revisions_observed"] == 0
    with sqlite3.connect(path) as db:
        payload = json.loads(
            db.execute("SELECT payload FROM source_cache WHERE id='cpi'").fetchone()[0]
        )
        payload["release_metadata"]["last_source_success_at"] = (
            NOW + timedelta(days=1)
        ).isoformat()
        db.execute(
            "UPDATE source_cache SET payload=? WHERE id='cpi'", (json.dumps(payload),)
        )
    report = audit.audit(path, evidence_origin="fixture", now=NOW)
    cpi = next(r for r in report["datasets"] if r["id"] == "cpi")
    assert not cpi["refresh"]["successful_source_check_verified"]
    assert "invalid_refresh_timestamp" in {i["code"] for i in cpi["issues"]}


def test_broken_public_grant_is_counted_and_private_rows_not_read(tmp_path):
    path = database(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE catalog_release_grants(dataset_id TEXT,public_display INTEGER)"
        )
        db.executemany(
            "INSERT INTO catalog_release_grants VALUES(?,?)",
            [("unknown_public", 1), ("private_secret", 0)],
        )
    report = audit.audit(path, expected_public=31, evidence_origin="fixture", now=NOW)
    assert report["scope"]["matches_expected"]
    row = next(r for r in report["datasets"] if r["id"] == "unknown_public")
    assert row["classification"] == "Needs attention"
    assert "private_secret" not in json.dumps(report)


def test_write_attempt_from_reused_reader_is_denied(tmp_path, monkeypatch):
    path = database(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE catalog_release_grants(dataset_id TEXT,public_display INTEGER)"
        )
        db.execute("INSERT INTO catalog_release_grants VALUES('bad_public',1)")
    attempted = []

    def malicious(self, db, key):
        with pytest.raises(sqlite3.DatabaseError):
            db.execute("DELETE FROM source_cache")
        attempted.append(key)
        raise ValueError("Invalid publication")

    monkeypatch.setattr(audit.NativeReader, "_permission", malicious)
    before = path.read_bytes()
    audit.audit(path, evidence_origin="fixture", now=NOW)
    assert attempted == ["bad_public"]
    assert path.read_bytes() == before


def test_reports_json_csv_markdown_and_output_protection(tmp_path):
    path = database(tmp_path)
    report = audit.audit(path, evidence_origin="fixture", now=NOW)
    out = tmp_path / "reports"
    audit.write_reports(report, out, path)
    assert (
        json.loads((out / "audit.json").read_text(encoding="utf-8"))["evidence_origin"]
        == "fixture"
    )
    with (out / "datasets.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 30
    assert "refresh.successful_source_check_verified" in rows[0]
    assert "## Recommended fixes" in (out / "summary.md").read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        audit.write_reports(report, out, path)
    with pytest.raises(ValueError):
        audit.write_reports(report, path.parent / "unsafe", path)


def test_missing_database_is_not_created_and_time_budget_fails(tmp_path):
    path = tmp_path / "missing.sqlite3"
    with pytest.raises(FileNotFoundError):
        audit.audit(path, evidence_origin="fixture")
    assert not path.exists()
    path = database(tmp_path)
    with pytest.raises(ValueError):
        audit.audit(path, evidence_origin="fixture", max_seconds=121)


def test_cli_scope_mismatch_preserves_reports_and_returns_two(tmp_path, monkeypatch):
    path = database(tmp_path)
    out = tmp_path / "scope-mismatch"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "readiness",
            "--database",
            str(path),
            "--output",
            str(out),
            "--evidence-origin",
            "fixture",
        ],
    )
    with pytest.raises(SystemExit) as error:
        audit.main()
    assert error.value.code == 2
    assert (out / "audit.json").is_file()


def test_native_refresh_distinguishes_success_change_revisions_and_configuration(
    tmp_path,
):
    path = tmp_path / "refresh.sqlite3"
    with sqlite3.connect(path) as db:
        db.row_factory = sqlite3.Row
        db.execute(
            "CREATE TABLE catalog_refresh_jobs(dataset_id TEXT,last_attempt TEXT,last_check TEXT,last_success TEXT,last_change TEXT,next_due REAL,failures INTEGER,error_code TEXT)"
        )
        db.execute("CREATE TABLE norm_revisions(dataset_id TEXT)")
        db.execute(
            "INSERT INTO catalog_refresh_jobs VALUES(?,?,?,?,?,?,?,?)",
            (
                "sample",
                NOW.isoformat(),
                NOW.isoformat(),
                NOW.isoformat(),
                None,
                NOW.timestamp() + 86400,
                0,
                None,
            ),
        )
        db.execute("INSERT INTO norm_revisions VALUES('sample')")
        row = {
            "id": "sample",
            "frequency": "monthly",
            "refresh": {
                "ingest_approved": True,
                "automation_ready": True,
                "mode": "refresh",
                "check_seconds": 86400,
            },
        }
        issues = []
        evidence = audit.refresh_evidence(
            db, {"catalog_refresh_jobs", "norm_revisions"}, row, {}, {}, NOW, issues
        )
        assert evidence["configured"] and evidence["registered_job"]
        assert evidence["successful_source_check_verified"]
        assert evidence["last_observed_change"] is None
        assert evidence["historical_revisions_observed"] == 1
        assert evidence["new_observations_ingested"] == "not_separately_recorded"
        db.execute(
            "UPDATE catalog_refresh_jobs SET last_success=NULL,error_code='secret upstream URL'"
        )
        evidence = audit.refresh_evidence(
            db, {"catalog_refresh_jobs", "norm_revisions"}, row, {}, {}, NOW, []
        )
        assert not evidence["successful_source_check_verified"]
        assert evidence["error_classification"] == "source_failure_review"
        assert "secret" not in json.dumps(evidence)


def test_snapshot_remains_consistent_while_separate_writer_updates(
    tmp_path, monkeypatch
):
    path = database(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA journal_mode=WAL")
    original = audit.dataset_report
    changed = []

    def concurrent(db, tables, row, reader, now):
        if not changed:
            with sqlite3.connect(path) as writer:
                writer.execute("UPDATE source_cache SET payload='{}' WHERE id='cpi'")
            changed.append(True)
        return original(db, tables, row, reader, now)

    monkeypatch.setattr(audit, "dataset_report", concurrent)
    report = audit.audit(path, evidence_origin="fixture", now=NOW)
    assert (
        next(r for r in report["datasets"] if r["id"] == "cpi")["historical_quality"][
            "row_count"
        ]
        == 140
    )


def test_deadline_stops_without_certifying_partial_report(tmp_path, monkeypatch):
    path = database(tmp_path)
    ticks = iter([0, 200])
    monkeypatch.setattr(audit, "monotonic", lambda: next(ticks, 200))
    with pytest.raises(audit.AuditStopped):
        audit.audit(path, evidence_origin="fixture", now=NOW)


def test_malformed_cache_and_csv_formulas_are_not_silently_certified(tmp_path):
    path = database(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE source_cache SET payload='not json' WHERE id='cpi'")
    report = audit.audit(path, evidence_origin="fixture", now=NOW)
    row = next(r for r in report["datasets"] if r["id"] == "cpi")
    assert row["classification"] == "Needs attention"
    assert "stored_history_unreadable_or_over_budget" in {
        i["code"] for i in row["issues"]
    }
    row["metadata"]["name"] = '=HYPERLINK("bad")'
    out = tmp_path / "formula-safe"
    audit.write_reports(report, out, path)
    with (out / "datasets.csv").open(encoding="utf-8-sig", newline="") as stream:
        assert next(r for r in csv.DictReader(stream) if r["id"] == "cpi")[
            "metadata.name"
        ].startswith("'=")
