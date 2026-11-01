"""Explicit version 2 migration, new private tables only; no startup hook."""

from backend.app.catalog.schema import migrate as foundation_migrate

STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS norm_datasets (
      id TEXT PRIMARY KEY, provider TEXT NOT NULL, definition TEXT NOT NULL, definition_hash TEXT NOT NULL,
      source_identity TEXT NOT NULL UNIQUE,
      public_display INTEGER NOT NULL DEFAULT 0 CHECK(public_display=0),
      ai_allowed INTEGER NOT NULL DEFAULT 0 CHECK(ai_allowed=0),
      discovery_allowed INTEGER NOT NULL DEFAULT 0 CHECK(discovery_allowed=0),
      rights_state TEXT NOT NULL DEFAULT 'unreviewed' CHECK(rights_state='unreviewed'))""",
    """CREATE TABLE IF NOT EXISTS norm_generations (
      id TEXT PRIMARY KEY, dataset_id TEXT NOT NULL REFERENCES norm_datasets(id), definition_hash TEXT NOT NULL,
      state TEXT NOT NULL CHECK(state IN ('staging','complete','superseded')),
      snapshot_hash TEXT, created_at TEXT NOT NULL, completed_at TEXT)""",
    """CREATE UNIQUE INDEX IF NOT EXISTS norm_one_pending ON norm_generations(dataset_id) WHERE state='staging'""",
    """CREATE TABLE IF NOT EXISTS norm_partitions (
      id TEXT PRIMARY KEY, generation_id TEXT NOT NULL REFERENCES norm_generations(id),
      start_date TEXT NOT NULL, end_date TEXT NOT NULL, cursor TEXT,
      state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','running','failed','complete','superseded')),
      page_count INTEGER NOT NULL DEFAULT 0, next_due REAL NOT NULL DEFAULT 0,
      failures INTEGER NOT NULL DEFAULT 0, error_code TEXT, last_attempt TEXT, last_success TEXT)""",
    "CREATE INDEX IF NOT EXISTS norm_due ON norm_partitions(next_due,id)",
    """CREATE TABLE IF NOT EXISTS norm_worker_lease (
      singleton INTEGER PRIMARY KEY CHECK(singleton=1), owner TEXT NOT NULL, expires_at REAL NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS norm_pages (
      partition_id TEXT NOT NULL, request_hash TEXT NOT NULL, content_hash TEXT NOT NULL,
      next_hash TEXT NOT NULL, point_count INTEGER NOT NULL, PRIMARY KEY(partition_id,request_hash))""",
    """CREATE TABLE IF NOT EXISTS norm_staged (
      generation_id TEXT NOT NULL, period_key TEXT NOT NULL, reference_start TEXT NOT NULL,
      reference_end TEXT NOT NULL, partition_id TEXT NOT NULL,
      payload TEXT NOT NULL, value REAL, artifact_hash TEXT NOT NULL, checked_at TEXT NOT NULL,
      PRIMARY KEY(generation_id,period_key))""",
    """CREATE TABLE IF NOT EXISTS norm_observations (
      dataset_id TEXT NOT NULL, period_key TEXT NOT NULL, reference_start TEXT NOT NULL,
      reference_end TEXT NOT NULL, payload TEXT NOT NULL, value REAL,
      artifact_hash TEXT NOT NULL, checked_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
      generation_id TEXT NOT NULL, PRIMARY KEY(dataset_id,period_key))""",
    "CREATE INDEX IF NOT EXISTS norm_observation_dates ON norm_observations(dataset_id,reference_start,period_key)",
    """CREATE TABLE IF NOT EXISTS norm_dataset_state (
      dataset_id TEXT PRIMARY KEY, active_generation TEXT NOT NULL, updated_at TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS norm_revisions (
      dataset_id TEXT NOT NULL, period_key TEXT NOT NULL, revision INTEGER NOT NULL,
      old_payload TEXT NOT NULL, old_artifact_hash TEXT NOT NULL, replaced_at TEXT NOT NULL,
      generation_id TEXT NOT NULL, PRIMARY KEY(dataset_id,period_key,revision))""",
    """CREATE TABLE IF NOT EXISTS norm_runs (
      id TEXT PRIMARY KEY, partition_id TEXT NOT NULL, state TEXT NOT NULL,
      started_at TEXT NOT NULL, finished_at TEXT, error_code TEXT)""",
)


def migrate(connection):
    connection.execute("SAVEPOINT batch0_native")
    try:
        foundation_migrate(connection)
        for statement in STATEMENTS:
            connection.execute(statement)
        connection.execute(
            "INSERT OR IGNORE INTO catalog_schema_versions VALUES(2,?)",
            ("batch0_native_partition_foundation",),
        )
        connection.execute("RELEASE batch0_native")
    except BaseException:
        connection.execute("ROLLBACK TO batch0_native")
        connection.execute("RELEASE batch0_native")
        raise
