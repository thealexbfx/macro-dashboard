"""Audit evidence must remain complete without retargeting public identities."""

import json
from dataclasses import asdict

from backend.app.v2.definitions import SPECS
from scripts.build_suitability_audit import AUDIT, ROOT, render


def read(name):
    return json.loads((AUDIT / name).read_text(encoding="utf-8"))


def test_reviewed_artifacts_are_reproducible():
    for name, content in render().items():
        assert (AUDIT / name).read_text(encoding="utf-8") == content, name


def test_existing_public_identities_are_preserved():
    baseline = read("public_identity_baseline.json")
    assert len(baseline) == 30
    assert baseline.keys() == SPECS.keys()
    for key, original in baseline.items():
        current = json.loads(json.dumps(asdict(SPECS[key])))
        assert {field: current[field] for field in original} == original


def test_all_public_reviews_have_source_and_research_evidence():
    matrix = read("PUBLIC_DATASET_MATRIX.json")
    assert matrix["counts"] == {
        "KEEP": 4,
        "KEEP + SUPPLEMENT": 19,
        "FLAG": 5,
        "REPLACE": 2,
    }
    assert {r["id"] for r in matrix["datasets"]} == set(SPECS)
    for row in matrix["datasets"]:
        for field in (
            "original_identifier",
            "original_source",
            "revision_methodology",
            "suitable_for",
            "unsuitable_for",
            "continuity_and_presentation_risks",
            "evidence",
            "underlying_rights_code",
            "transport_rights_code",
        ):
            assert row[field], (row["id"], field)


def test_expansion_screen_does_not_claim_unreviewed_entries_are_cleared():
    screen = read("EXPANSION_QUALITY_SCREEN.json")
    manifest = json.loads((ROOT / "catalog/datasets.json").read_text(encoding="utf-8"))
    entries = {r["id"]: r for r in manifest["datasets"]}
    assert len(screen["entries"]) == len(entries) == 309
    for row in screen["entries"]:
        original = entries[row["id"]]
        assert row["prior_rights_state"] == original["rights"]["status"]
        assert row["planning_refs"] == original["planning_refs"]
        if row["id"] not in SPECS:
            assert row["existing_public_review"] is None
            assert row["status"] == "pending source-specific suitability review"
