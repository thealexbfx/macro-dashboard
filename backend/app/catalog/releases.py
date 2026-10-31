"""Reviewed release candidates plus additive, explicitly applied display grants.

Candidate metadata alone never grants access. SQLite activation, matching source
definition, rights review and a complete ingestion receipt are all mandatory.
Legacy permissions and World Bank pilot flags are never updated by this module.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

from backend.app.ingestion.native import Definition, SourceCalendar

RELEASE_FILE = (
    Path(__file__).resolve().parents[3] / "catalog" / "release_candidates.json"
)
PROTECTED = {"wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly"}


def decode_definition(data):
    data = dict(data)
    calendar = dict(data["calendar"])
    calendar["releases"] = tuple(
        datetime.fromisoformat(v) for v in calendar.get("releases", ())
    )
    calendar["holidays"] = tuple(calendar.get("holidays", ()))
    data["calendar"] = SourceCalendar(**calendar)
    data["dimensions"] = tuple(tuple(x) for x in data.get("dimensions", ()))
    return Definition(**data)


def candidates(path=RELEASE_FILE):
    if not path.exists():
        return {}
    from backend.app.catalog.manifest import LEGACY_PUBLIC_SOURCES
    from backend.app.v2.native_reader import NativePublication

    data = json.loads(path.read_text(encoding="utf-8"))
    result = {}
    for row in data["datasets"]:
        d = decode_definition(row["definition"])
        if d.id in result or d.id in PROTECTED or d.id in LEGACY_PUBLIC_SOURCES:
            raise ValueError("Duplicate or protected release identity")
        if row["ai_allowed"] is not False or row["discovery_allowed"] is not False:
            raise ValueError("Display review does not authorize AI or Discovery")
        result[d.id] = NativePublication(
            d,
            row["name"],
            row["category"],
            row["region"],
            row["source_url"],
            row["license_url"],
            tuple(row["attribution"]),
            row["rights_evidence"],
            tuple(row.get("limitations", ())),
        )
    return result


def migrate(db):
    """Additive only. No DROP/ALTER/seed and no implicit call from app startup."""
    if (
        db.execute(
            "SELECT name FROM catalog_schema_versions WHERE version=2"
        ).fetchone()
        is None
    ):
        raise ValueError("Explicit Batch 0 version 2 migration required first")
    db.execute("""CREATE TABLE IF NOT EXISTS catalog_release_grants (
        dataset_id TEXT PRIMARY KEY REFERENCES norm_datasets(id),
        definition_hash TEXT NOT NULL CHECK(length(definition_hash)=64),
        evidence TEXT NOT NULL CHECK(length(evidence)>0),
        rights_state TEXT NOT NULL CHECK(rights_state='permitted'),
        public_display INTEGER NOT NULL DEFAULT 0 CHECK(public_display IN (0,1)),
        ai_allowed INTEGER NOT NULL DEFAULT 0 CHECK(ai_allowed=0),
        discovery_allowed INTEGER NOT NULL DEFAULT 0 CHECK(discovery_allowed=0),
        activated_at TEXT NOT NULL)""")
    db.execute(
        "INSERT OR IGNORE INTO catalog_schema_versions VALUES(3,'reviewed_display_release_grants')"
    )
    db.execute("""CREATE TABLE IF NOT EXISTS catalog_staging_digests (
        generation_id TEXT NOT NULL, period_key TEXT NOT NULL,
        payload_hash TEXT NOT NULL CHECK(length(payload_hash)=64),
        PRIMARY KEY(generation_id,period_key))""")


def activate(db, publication, reader, *, approved=False):
    """Explicit operator approval; existing norm_* deny flags remain intact.

    Display rights are authoritative in this new grant and catalog_scope_reviews;
    old private-only CHECK constraints stay intact, preserving backward rollback.
    """
    from backend.app.catalog.manifest import LEGACY_PUBLIC_SOURCES

    d = publication.definition
    if approved is not True or d.id in PROTECTED or d.id in LEGACY_PUBLIC_SOURCES:
        raise ValueError("Explicit approved, nonprotected release required")
    row = db.execute(
        "SELECT definition_hash FROM norm_datasets WHERE id=?", (d.id,)
    ).fetchone()
    if row is None or row[0] != d.fingerprint:
        raise ValueError("Ingested definition differs from reviewed selection")
    generation = db.execute(
        "SELECT g.* FROM norm_dataset_state s JOIN norm_generations g ON g.id=s.active_generation WHERE s.dataset_id=?",
        (d.id,),
    ).fetchone()
    reader._receipt(
        db, d, generation
    )  # Includes partition/cursor/source hash reconciliation.
    stamp = datetime.now(UTC).isoformat()
    db.execute(
        "INSERT INTO catalog_release_grants VALUES(?,?,?,'permitted',1,0,0,?) ON CONFLICT(dataset_id) DO UPDATE SET definition_hash=excluded.definition_hash,evidence=excluded.evidence,public_display=1,activated_at=excluded.activated_at",
        (d.id, d.fingerprint, publication.rights_evidence, stamp),
    )
    db.execute(
        "INSERT INTO catalog_scope_reviews VALUES(?,'public_display','permitted',1,?,?,?) ON CONFLICT(dataset_id,scope) DO UPDATE SET rights_state='permitted',approved=1,evidence=excluded.evidence,definition_hash=excluded.definition_hash,reviewed_at=excluded.reviewed_at",
        (d.id, publication.rights_evidence, d.fingerprint, stamp),
    )
