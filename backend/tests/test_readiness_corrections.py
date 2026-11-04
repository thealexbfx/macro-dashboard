"""Methodology regressions; synthetic data is never production revalidation."""

import json
import sqlite3
from datetime import UTC, datetime

import pytest

from backend.app.catalog import readiness as audit
from backend.app.catalog import research_metadata as metadata
from backend.app.catalog.operations import registry
from backend.app.v2.definitions import SPECS
from backend.tests.test_readiness_audit import NOW, database, no_network, points
from scripts.analyze_readiness_report import analyze, render
from scripts.readiness_refresh_diagnostics import diagnostics

# Reuse the fixture's network denial, even when this module is run independently.
pytestmark = pytest.mark.usefixtures("no_network")
assert no_network


@pytest.mark.parametrize("key", ["sp500", "gold", "dxy", "wti"])
def test_market_null_adjustment_is_not_missing_or_insufficient_history(key, tmp_path):
    path = database(tmp_path)
    with sqlite3.connect(path) as db:
        payload = {"observations": points("daily", 100), "release_metadata": {}}
        db.execute(
            "INSERT INTO source_cache VALUES(?,?,?,?,0)",
            (key, json.dumps(payload), NOW.isoformat(), NOW.isoformat()),
        )
    report = audit.audit(path, evidence_origin="fixture", now=NOW)
    row = next(r for r in report["datasets"] if r["id"] == key)
    assert row["metadata"]["adjustment"] is None
    assert row["metadata"]["adjustment_status"] == "not_applicable"
    assert row["metadata"]["missing_fields"] == []
    assert (
        row["research_suitability"]["comparisons"]["status"]
        == "eligible_with_limitations"
    )
    assert (
        row["research_suitability"]["numerical_lookup"]["status"]
        == "eligible_with_limitations"
    )
    assert not any(
        i["code"] == "insufficient_comparison_history" for i in row["issues"]
    )
    assert any(i["code"] == "approximate_daily_calendar" for i in row["issues"])
    assert row["permissions"]["audit_grants_nothing"]


def test_unknown_economic_adjustment_and_other_gates_are_not_bypassed():
    assert audit.adjustment_status(SPECS["cpi"], None) == "unknown"
    history, _ = audit.summarize_history(points(), "monthly", NOW)
    result = audit.capabilities(history, "monthly", metadata_ok=False)
    assert result["comparisons"]["history_sufficient"]
    assert "Required applicable metadata missing" in result["comparisons"]["reasons"]
    result = audit.capabilities(history, "monthly", metadata_ok=True, blocked=True)
    assert (
        "Publication/completeness evidence failed" in result["comparisons"]["reasons"]
    )
    history["invalid_count"] = 1
    assert (
        "Stored observation integrity failed"
        in audit.capabilities(history, "monthly", True)["comparisons"]["reasons"]
    )


def test_null_on_excluded_closure_is_not_an_analytical_gap():
    rows = [
        {"date": "2026-07-02", "value": 100.0},
        {"date": "2026-07-03", "value": None},
        {"date": "2026-07-06", "value": 101.0},
    ]
    history, issues = audit.summarize_history(rows, "daily", NOW, spec=SPECS["sp500"])
    assert history["null_value_count"] == 1  # Raw evidence retained.
    assert history["nulls_outside_analytical_calendar"] == 1
    assert history["analytical_missing_periods"] == 0
    assert not any(i["code"] == "history_gaps" for i in issues)


def test_boundary_unavailability_is_not_silently_called_internal_data_loss():
    rows = points(count=24)
    rows[0]["value"] = rows[1]["value"] = rows[10]["value"] = rows[-1]["value"] = None
    history, issues = audit.summarize_history(rows, "monthly", NOW)
    assert history["leading_missing_periods"] == 2
    assert history["trailing_missing_periods"] == 1
    assert history["internal_missing_periods"] == 1
    assert any(i["code"] == "history_gaps" for i in issues)
    assert len(rows) == 24


def test_annual_age_uses_end_of_measured_period():
    from backend.app.ingestion.native import Definition, SourceCalendar

    definition = Definition(
        "annual_test",
        "eurostat",
        "annual selector",
        "EUR",
        "annual",
        "NSA",
        SourceCalendar("calendar-year"),
    )
    history, _ = audit.summarize_history(
        [{"date": "2025-01-01", "end": "2025-12-31", "key": "2025", "value": 100.0}],
        "annual",
        NOW,
        definition=definition,
    )
    assert history["last_valid_reference_end"] == "2025-12-31"
    assert (
        NOW.date() - datetime.fromisoformat(history["last_valid_reference_end"]).date()
    ).days < audit.LAGS["annual"]
    assert (
        NOW.date() - datetime.fromisoformat(history["last_valid_observation"]).date()
    ).days > audit.LAGS["annual"]


def test_review_overlay_is_definition_bound_and_cannot_carry_permissions(tmp_path):
    row = next(r for r in registry() if r["id"] == "cpi")
    review = {
        "id": row["id"],
        "identity_sha256": metadata.identity(row),
        "definition": "Synthetic reviewed definition for test only.",
        "observation_convention": "Monthly reference date",
        "publication_behavior": None,
        "revision_behavior": None,
        "references": ["https://example.org/source"],
        "reviewed_at": datetime(2026, 11, 3, tzinfo=UTC).isoformat(),
        "reviewer": "Test fixture",
    }
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps({"schema_version": 1, "reviews": [review]}))
    reviews = metadata.load_reviews(path)
    resolved = metadata.resolve(row, reviews)
    assert resolved["publication_behavior"] is None
    assert not resolved["grants_permissions"]
    with pytest.raises(ValueError):
        metadata.resolve({**row, "units": "changed"}, reviews)
    review["ai_allowed"] = True
    path.write_text(json.dumps({"schema_version": 1, "reviews": [review]}))
    with pytest.raises(ValueError):
        metadata.load_reviews(path)


def test_review_queue_never_invents_description_or_adjustment():
    row = next(r for r in registry() if not r["description"])
    report = {
        "as_of": NOW.isoformat(),
        "datasets": [
            {
                "id": row["id"],
                "issues": [{"code": "description_missing"}, {"code": "history_gaps"}],
            }
        ],
    }
    queue = metadata.review_queue(report, [row])
    assert len(queue) == 1 and queue[0]["priority"] == 1
    facts = queue[0]["canonical_facts"]
    assert facts["definition"] is None
    assert facts["seasonal_adjustment"] == row["adjustment"]
    assert facts["revision_behavior"] is None


def test_diagnostics_distinguish_guard_and_missing_telemetry_without_exporting_secrets(
    tmp_path,
):
    path = database(tmp_path)
    with sqlite3.connect(path) as db:
        payload = {
            "observations": [{"secret": "never export"}],
            "quality_warnings": [
                "Provider history omitted previously observed values; SECRET URL"
            ],
            "release_metadata": {"source_error_code": "SECRET token"},
            "status": "stale",
        }
        db.execute(
            "INSERT INTO source_cache VALUES(?,?,?,?,6)",
            (
                "high_yield_spread",
                json.dumps(payload),
                NOW.isoformat(),
                NOW.isoformat(),
            ),
        )
    before = path.read_bytes()
    report = diagnostics(path)
    row = next(r for r in report["datasets"] if r["id"] == "high_yield_spread")
    assert row["history_truncation_guard_recorded"]
    assert row["source_check_succeeded"] is None
    assert "SECRET" not in json.dumps(report) and "never export" not in json.dumps(
        report
    )
    assert path.read_bytes() == before


def test_report_analysis_does_not_mislabel_new_evidence_as_reviewed_production(
    tmp_path,
):
    path = database(tmp_path)
    report = audit.audit(path, evidence_origin="fixture", now=NOW)
    findings, queue = analyze(report, registry())
    assert findings["public_count"] == 30
    assert findings["not_a_new_production_audit"]
    assert queue == []
    assert "fixture" in render(findings)
    assert "not a new production audit" in render(findings)
