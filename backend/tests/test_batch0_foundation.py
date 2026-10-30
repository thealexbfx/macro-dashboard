"""Offline planning/security and additive-migration tests; synthetic data only."""

import json
import sqlite3
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from backend.app.catalog.manifest import Manifest, canonical_id, validate
from backend.app.catalog.publication import Completeness, Review, permits
from backend.app.catalog.schema import migrate
from backend.app.v2.definitions import SPECS
from backend.app.v2.dynamic_scan import MODES
from backend.app.v2.state import Store
from backend.app.v2.stored_datasets import PUBLIC_STORED_DEFINITIONS
from scripts.build_dataset_manifest import build
from scripts.validate_batch0_foundation import seed, snapshot

REPO = Path(__file__).resolve().parents[2]
PLANNING = REPO / "research/planning/batch0"
SOURCE_HASH = "a" * 64
DEFINITION_HASH = "b" * 64


def test_recovered_sources_are_byte_for_byte_originals():
    provenance = json.loads((PLANNING / "provenance.json").read_text())
    for source in provenance["files"]:
        data = (PLANNING / source["path"]).read_bytes()
        assert len(data) == source["bytes"]
        assert sha256(data).hexdigest() == source["sha256"]


def test_manifest_rebuild_is_reproducible_and_reconciles_every_reference():
    data = json.loads((REPO / "catalog/datasets.json").read_text())
    assert build() == data
    assert len(data["datasets"]) == 309
    refs = [r for e in data["datasets"] for r in e["planning_refs"]]
    assert len(refs) == len(set(refs)) == 298
    assert set(refs) == {f"ML-{n:03d}" for n in range(1, 265)} | {
        f"G{n:02d}" for n in range(1, 35)
    }
    assert (
        sum(e["publication"]["status"] == "private_ingested" for e in data["datasets"])
        == 3
    )
    assert sum(e["kind"] == "selection" for e in data["datasets"]) > 0


def test_all_legacy_ids_definitions_and_discovery_eligibility_are_preserved():
    manifest = Manifest.load()
    assert {e["id"] for e in manifest.page(limit=100)["items"]} == set(SPECS)
    for key, spec in SPECS.items():
        row = manifest.get(key)
        for field in ("name", "units", "frequency", "region", "category"):
            assert row[field] == getattr(spec, field)
        assert row["source"]["selector"] == spec.provider_id
        assert row["publication"]["discovery"] == (key in MODES)
    assert not PUBLIC_STORED_DEFINITIONS


def test_metadata_pages_do_not_include_histories_or_private_counts():
    manifest = Manifest.load()
    seen = []
    offset = 0
    while True:
        page = manifest.page(offset=offset, limit=7)
        assert page["total"] == 30
        assert len(page["items"]) <= 7
        assert all(
            set(e)
            == {
                "id",
                "name",
                "category",
                "region",
                "units",
                "frequency",
                "kind",
                "provider",
            }
            for e in page["items"]
        )
        seen.extend(e["id"] for e in page["items"])
        if page["next_offset"] is None:
            break
        offset = page["next_offset"]
    assert len(seen) == len(set(seen)) == 30
    assert manifest.page(query="wb_")["total"] == 0
    assert manifest.page(audience="planning", limit=100)["total"] == 309
    assert manifest.page(offset=1000)["items"] == []


@pytest.mark.parametrize(
    "kwargs",
    [
        {"limit": 101},
        {"limit": 0},
        {"offset": -1},
        {"offset": True},
        {"audience": "admin"},
        {"query": "a" * 201},
    ],
)
def test_metadata_bounds(kwargs):
    with pytest.raises(ValueError):
        Manifest.load().page(**kwargs)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_id",
        "duplicate_source",
        "duplicate_ref",
        "enable_private",
        "spoof_legacy",
        "approved_rights",
        "enable_ai",
        "bad_url",
    ],
)
def test_invalid_or_escalated_manifest_is_rejected(mutation):
    payload = build()
    rows = payload["datasets"]
    private = next(e for e in rows if e["publication"]["status"] == "planned")
    if mutation == "duplicate_id":
        rows[1]["id"] = rows[0]["id"]
    elif mutation == "duplicate_source":
        other = json.loads(json.dumps(private))
        other["id"] = "other_id"
        other["planning_refs"] = []
        rows.append(other)
    elif mutation == "duplicate_ref":
        rows[1]["planning_refs"] = rows[0]["planning_refs"]
        if not rows[0]["planning_refs"]:
            rows[0]["planning_refs"] = rows[1]["planning_refs"] = ["G01"]
    elif mutation == "enable_private":
        private["publication"]["discovery"] = True
    elif mutation == "spoof_legacy":
        private["publication"].update(status="legacy_public", public_display=True)
    elif mutation == "approved_rights":
        private["rights"]["status"] = "approved"
    elif mutation == "enable_ai":
        private["publication"]["ai"] = True
    else:
        private["source"]["endpoint"] = "https://user:secret@example.invalid/"
    with pytest.raises(ValueError):
        validate(payload)


def test_assignment_is_independent_of_names_units_and_planning_row_numbers():
    original = next(
        e for e in build()["datasets"] if e["publication"]["status"] == "planned"
    )
    changed = {
        **original,
        "name": "Revised title",
        "units": "Revised unit",
        "planning_refs": [],
    }
    assert canonical_id(original) == canonical_id(changed)
    manifest = Manifest.load()
    copy = manifest.get("wb_brent_monthly")
    copy["publication"]["public_display"] = True
    assert not manifest.get("wb_brent_monthly")["publication"]["public_display"]


@pytest.mark.parametrize("scope", ["public_display", "ai", "discovery"])
def test_scope_grants_are_independent_and_require_all_safeguards(scope):
    complete = Completeness(
        "fixture",
        "batch_1",
        SOURCE_HASH,
        DEFINITION_HASH,
        state="complete",
        quality_passed=True,
    )
    review = Review(
        "fixture", scope, "permitted", True, "fixture evidence", DEFINITION_HASH
    )
    args = {
        "dataset_id": "fixture",
        "scope": scope,
        "registration": True,
        "review": review,
        "completeness": complete,
        "source_hash": SOURCE_HASH,
        "definition_hash": DEFINITION_HASH,
    }
    assert permits(**args)
    for other in {"public_display", "ai", "discovery"} - {scope}:
        assert not permits(**{**args, "scope": other})
    for field, value in (
        ("cursor", "next"),
        ("cursor", ""),
        ("source_hash", "c" * 64),
        ("definition_hash", "d" * 64),
        ("dataset_id", "different"),
        ("quality_passed", False),
        ("state", "partial"),
        ("batch_id", ""),
    ):
        assert not permits(
            **{**args, "completeness": replace(complete, **{field: value})}
        )
    for field, value in (
        ("approved", False),
        ("rights_state", "unreviewed"),
        ("evidence", ""),
        ("evidence", None),
        ("reviewed_definition_hash", "e" * 64),
    ):
        assert not permits(**{**args, "review": replace(review, **{field: value})})
    assert not permits(**{**args, "registration": False})
    assert not permits(**{**args, "source_hash": "not_a_hash"})


def test_backup_restore_additive_migration_and_old_reader_compatibility(tmp_path):
    original = tmp_path / "synthetic-e70.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    with sqlite3.connect(original) as db:
        seed(db)
        before = snapshot(db)
    with sqlite3.connect(original) as source, sqlite3.connect(restored) as target:
        source.backup(target)
    with sqlite3.connect(restored) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        migrate(db)
        migrate(db)
        assert snapshot(db) == before
        assert (
            db.execute("SELECT count(*) FROM catalog_scope_reviews").fetchone()[0] == 0
        )
        assert (
            db.execute("SELECT count(*) FROM catalog_dataset_completeness").fetchone()[
                0
            ]
            == 0
        )
        assert (
            db.execute("SELECT count(*) FROM ingest_observations").fetchone()[0] == 2403
        )
        assert db.execute(
            "SELECT DISTINCT public_display,ai_allowed,rights_state FROM ingest_datasets"
        ).fetchall() == [(0, 0, "unreviewed")]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE ingest_datasets SET public_display=1")
    # The existing Store knows nothing about the new tables; reopening is code rollback.
    with Store(restored).connection() as db:
        assert snapshot(db) == before
    with sqlite3.connect(original) as db:
        assert snapshot(db) == before
        assert not db.execute(
            "SELECT name FROM sqlite_master WHERE name LIKE 'catalog_%'"
        ).fetchall()


def test_failed_migration_rolls_back_all_new_tables(tmp_path):
    with sqlite3.connect(tmp_path / "fixture.sqlite3") as db:
        db.execute("CREATE TABLE catalog_schema_versions(incompatible_column TEXT)")
        db.commit()
        with pytest.raises(sqlite3.OperationalError):
            migrate(db)
        assert not db.execute(
            "SELECT name FROM sqlite_master WHERE name='catalog_scope_reviews'"
        ).fetchall()


def test_migration_participates_in_caller_rollback(tmp_path):
    with sqlite3.connect(tmp_path / "fixture.sqlite3") as db:
        db.execute("BEGIN")
        migrate(db)
        db.rollback()
        assert not db.execute(
            "SELECT name FROM sqlite_master WHERE name LIKE 'catalog_%'"
        ).fetchall()
