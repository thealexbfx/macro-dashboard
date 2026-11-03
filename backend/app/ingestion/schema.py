"""Additive schema only. Old state tables, IDs and API contracts remain untouched."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS ingest_datasets (
 id TEXT PRIMARY KEY, provider TEXT NOT NULL, metadata TEXT NOT NULL,
 public_display INTEGER NOT NULL DEFAULT 0 CHECK(public_display=0),
 ai_allowed INTEGER NOT NULL DEFAULT 0 CHECK(ai_allowed=0),
 rights_state TEXT NOT NULL DEFAULT 'unreviewed', updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ingest_jobs (
 provider TEXT PRIMARY KEY, cursor TEXT, next_due REAL NOT NULL DEFAULT 0,
 failures INTEGER NOT NULL DEFAULT 0, last_attempt TEXT, last_success TEXT,
 error_code TEXT, source_hash TEXT, last_full_check REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS ingest_runs (
 id TEXT PRIMARY KEY, provider TEXT NOT NULL, started_at TEXT NOT NULL,
 finished_at TEXT, state TEXT NOT NULL, error_code TEXT,
 inserted INTEGER NOT NULL DEFAULT 0, revised INTEGER NOT NULL DEFAULT 0,
 source_hash TEXT, byte_count INTEGER, source_checked_at TEXT
);
CREATE INDEX IF NOT EXISTS ingest_runs_provider ON ingest_runs(provider,started_at);
CREATE TABLE IF NOT EXISTS ingest_observations (
 dataset_id TEXT NOT NULL REFERENCES ingest_datasets(id), period TEXT NOT NULL,
 value REAL, quality TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
 first_seen TEXT NOT NULL, changed_at TEXT NOT NULL, run_id TEXT NOT NULL,
 PRIMARY KEY(dataset_id,period)
);
CREATE TABLE IF NOT EXISTS ingest_revisions (
 dataset_id TEXT NOT NULL, period TEXT NOT NULL, revision INTEGER NOT NULL,
 old_value REAL, old_quality TEXT NOT NULL, replaced_at TEXT NOT NULL,
 run_id TEXT NOT NULL, PRIMARY KEY(dataset_id,period,revision)
);
"""
