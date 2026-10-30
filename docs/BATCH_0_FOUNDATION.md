# Batch 0, PR 1: manifest and publication foundation

Base: `e70e338a546afb64bf1e427f12bd63532f7ec9b4`.
Branch: `feature/macrolens-batch0-foundation`.

This is the first reviewable part of Batch 0, not a complete catalog rollout.
No production operation, new ingestion, permission grant, UI change or public API
change is included. Existing 30 public definitions, source/provider behavior,
saved-research contracts, ingestion adapter and all old SQLite tables are untouched.

## Implementation

- Preserved original research and source hashes under `research/planning/batch0`.
- Reproducible `catalog/datasets.json`: 309 deduplicated entries, 298 planning
  references, all 30 public IDs and all three private pilot IDs retained. Panels
  remain explicitly non-atomic selections. Rights are unreviewed, not assumed.
- `backend/app/catalog/manifest.py`: bounded, validated metadata reader with
  stable ID assignments, protected legacy public IDs, independent scope defaults,
  pagination, search and region filtering. Public filtering precedes counts and
  pagination. It never loads observation histories. It is an internal library,
  **not a new route or a replacement for Dataset Explorer's current request**.
- `publication.py`: future independent display/AI/Discovery gates. Each requires
  explicit code registration, matching dataset-specific scope review, reviewed
  definition hash, complete batch, matching artifact hash, empty cursor and passed
  quality checks. No rights are granted and no current reader guard is replaced.
- `schema.py`: explicit additive foundation migration with separate scope-review
  and dataset/batch completeness tables. It does not seed dataset rows or jobs.
  It is **not wired to application startup or the ingestion CLI**. Existing
  `CHECK(public_display=0)` and `CHECK(ai_allowed=0)` remain in force.
- The resource harness loads the manifest and applies the new migration only to
  its existing disposable fixture database. The production app is unchanged.

Metadata previews intentionally contain zero observations in this first PR. The
next integration must fetch bounded previews for the visible page only. The old
catalogue endpoint still behaves as before until that separately reviewed change.

## Validation

The focused suite covers source-byte preservation, manifest reproducibility and
reconciliation, all 30 legacy definitions/Discovery modes, pagination bounds,
private-name/count denial, duplicate detection, privilege escalation, independent
scope grants, source/definition/cursor mismatch, incomplete batches, atomic
migration failure, caller rollback and repeated migration.

Local results: **652 Python tests passed, five opt-in live checks skipped**;
**25 focused foundation tests passed**; **48 V2 frontend tests passed**. Repository
fatal-error Ruff checks and full Ruff checks for the new modules/tests/scripts
passed. The preserved/generated endpoint scan found 143 credential-bearing query
examples, all placeholders. No production credentials were inspected or copied.
Linux build/resource results must be confirmed on the pushed commit; they are not
inferred from local results.

The restore test seeds **2,403 synthetic** private commodity observations, a
captured revision and a saved investigation using the unchanged e70 schemas. It
uses SQLite's backup API to restore into a different disposable database, applies
the migration twice and hashes every old table before/after. It also reopens via
the unchanged Store and proves old permission CHECK constraints still reject a
public grant. No real production backup is read.

Local disposable probe: 450,560 bytes before migration, 475,136 bytes after;
**24,576 bytes growth** in this SQLite fixture. No manifest metadata is seeded
into SQLite. These figures are not a forecast of full-catalog storage. Measured
execution time depends on the host; the probe emits actual results per run.

The existing Linux workflow now also runs the offline restore/manifest probe with
512 MiB RAM, no additional swap, 0.5 CPU and network disabled. Its combined backend
scenarios retain the full manifest while exercising synthetic public requests,
Discovery, ingestion enabled/disabled, failures, restart and memory pressure.
The approximately 1 GiB disposable filesystem and all existing resource checks
remain. Linux CI logs/artifacts provide the actual RSS/cgroup/CPU/SQLite results;
Windows results are never labelled Linux measurements.

## Migration and rollback notes — no production commands authorized

There is no automatic migration in this PR and no need to run one to deploy its
inactive foundation. A future integration must explicitly opt into the reviewed
`migrate(connection)` function. It creates only:

- `catalog_schema_versions` (one migration-version record);
- `catalog_scope_reviews` (empty, default denied);
- `catalog_dataset_completeness` (empty, default pending).

It operates through a savepoint, participates in caller rollback and is repeatable.
It never modifies or replaces existing observation, revision, library, story or
source-cache tables. It does not remove the old private-only CHECK constraints.

Before any future approved production migration, verify an independent consistent
SQLite backup, restore test, disk/WAL headroom, current revision and disabled
ingestion/AI settings. Keep the persistent `/var/data` path unchanged. Code
rollback to e70 ignores the new empty tables; leave them in place. Do not restore
an old database over newer saved research as an ordinary code rollback.

## Remaining reviewable Batch 0 parts

1. **PR 2 — normalized observation/job foundation:** native daily/weekly/monthly/
   quarterly/annual periods, negative/zero values, provider calendars, revisions,
   bounded provider partitions and dataset completeness writer/recovery. No new
   provider or ingestion activation. Calendar rules must be explicit; never fill
   missing observations. Existing monthly WB observations must remain byte/logically
   intact. Current monthly-only ingestion and 5,000-point provider cap remain here.
2. **PR 3 — paginated website integration:** metadata-only API and visible-page
   previews, frontend pagination/search, bounded date-window queries and generalized
   reader/analytics support. Preserve current routes/saves, apply both old and new
   publication safeguards, and test permission revocation. Repeat Linux resource
   tests with representative hundreds-of-series fixtures, not just this manifest.

Public release remains blocked by rights review, missing atomic selectors,
iron-ore unit/benchmark resolution, publication migration/registration approval,
and the remaining integration/capacity tests. Public approval must never imply AI
or Discovery approval. No datasets, countries or paid services are added by this PR.
