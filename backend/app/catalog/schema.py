"""Explicit, additive Batch 0 foundation migration. Never run at app startup.

No old table is renamed, copied, altered, dropped or updated. No dataset records,
rights, jobs or observations are seeded. Future writers require separate review.
"""

import sqlite3

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS catalog_schema_versions (
        version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE
    )""",
    """CREATE TABLE IF NOT EXISTS catalog_scope_reviews (
        dataset_id TEXT NOT NULL, scope TEXT NOT NULL
          CHECK(scope IN ('public_display','ai','discovery')),
        rights_state TEXT NOT NULL DEFAULT 'unreviewed'
          CHECK(rights_state IN ('unreviewed','permitted','permission_required','prohibited')),
        approved INTEGER NOT NULL DEFAULT 0 CHECK(approved IN (0,1)),
        evidence TEXT NOT NULL DEFAULT '', definition_hash TEXT NOT NULL DEFAULT '',
        reviewed_at TEXT,
        CHECK(approved=0 OR (rights_state='permitted' AND length(evidence)>0
              AND length(definition_hash)=64 AND reviewed_at IS NOT NULL)),
        PRIMARY KEY(dataset_id,scope)
    )""",
    """CREATE TABLE IF NOT EXISTS catalog_dataset_completeness (
        dataset_id TEXT NOT NULL, batch_id TEXT NOT NULL,
        source_hash TEXT NOT NULL, definition_hash TEXT NOT NULL,
        cursor TEXT, state TEXT NOT NULL DEFAULT 'pending'
          CHECK(state IN ('pending','partial','complete','failed')),
        quality_passed INTEGER NOT NULL DEFAULT 0 CHECK(quality_passed IN (0,1)),
        checked_at TEXT NOT NULL,
        CHECK(state!='complete' OR (cursor IS NULL AND quality_passed=1
              AND length(source_hash)=64 AND length(definition_hash)=64)),
        PRIMARY KEY(dataset_id,batch_id)
    )""",
)


def migrate(connection):
    """Apply inside a savepoint; safe in a caller transaction, repeatable, no IO paths."""
    if not isinstance(connection, sqlite3.Connection):
        raise TypeError("An explicit SQLite connection is required")
    connection.execute("SAVEPOINT batch0_foundation")
    try:
        for statement in SCHEMA:
            connection.execute(statement)
        connection.execute(
            "INSERT OR IGNORE INTO catalog_schema_versions(version,name) VALUES(1,?)",
            ("batch0_manifest_publication_foundation",),
        )
        connection.execute("RELEASE batch0_foundation")
    except BaseException:
        connection.execute("ROLLBACK TO batch0_foundation")
        connection.execute("RELEASE batch0_foundation")
        raise
