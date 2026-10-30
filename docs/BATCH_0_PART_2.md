# Batch 0 Part 2: native observations and bounded private partitions

Base: `d782a7a159fe9834a3ee13d04e4ab03c9997e575` on
`feature/macrolens-batch0-foundation`, draft PR #9. This extends Part 1, not the
production registry. Existing public APIs, all 30 canonical public IDs, source
providers, frontend contracts, Discovery modes and saved research are unchanged.

## What is implemented

`backend/app/ingestion/native.py` describes native daily, weekly, monthly,
quarterly, annual and event/irregular observations. It preserves provider labels
separately from normalized identity and actual reference-period start/end dates.
Events preserve an offset-aware instant and optional source event ID; multiple
events at the same instant are distinct when IDs differ. Reference periods,
publication instants, source revision labels and retrieval time are separate.

Zero and negative values are valid. An explicit source null is stored as null.
Missing date rows stay absent; there is no grid generation, filling, interpolation,
automatic aggregation or resampling. A missing required value field is malformed,
not a fabricated null. Flags, units, frequency, adjustment and calendar identity
are retained. Revisions capture prior values and metadata; these are captured
changes, not a claim to reconstruct historical publication vintages.

Calendars explicitly declare weekly end-date versus ISO-week labels, fiscal-year
start month and year-label convention, timezone and convention version. Holidays
are metadata, never a rule for fabricating/dropping source records. Supplied
release instants require evidence; DST gaps and naive timestamps are rejected.
No guessed recurrence or universal US trading calendar is used. Unknown next
release remains unknown. Changed native conventions/units require definition
version review; adding sourced release dates does not mint a new dataset ID.

`partition_contracts.py` defines bounded pages/windows and explicit adapter
contracts. `formats.py` supplies fixture-tested format interpreters and access
profiles for FRED JSON, pinned Eurostat JSON-stat, explicitly selected ONS native
arrays, EIA v2 JSON and OECD/ECB SDMX CSV. These are **not live HTTP adapters**:
no credentials, API calls, provider registration or new scheduled jobs exist.

- FRED dates are interpreted only at the explicitly configured native frequency;
  vintage fields are retained. FRED API/service, caching, redistribution and AI
  restrictions still require clearance.
- Eurostat rejects multi-member/unpinned non-time dimensions. Sparse null cells
  are emitted only for actual source time labels; no extra labels are created.
- ONS selects the declared monthly/quarterly/annual array instead of guessing.
  CDID, base, overlapping labour periods and publication versions need review.
- EIA checks native units/facets/frequency. FRED/EIA pagination totals, when
  supplied, cannot be silently ignored at an apparently terminal page.
- SDMX checks pinned dimensions, flags and UNIT_MULT. Values are not silently
  multiplied or rebased. SDMX deltas are not complete replacement snapshots.

## Durable jobs and source consistency

`partitioned.py` is an inactive explicit-call engine. It requires the new schema
to have already been installed by an authorized caller; it does not migrate on
construction, attach to the production scheduler or alter the existing monthly
World Bank runner. Existing public IDs and all three WB pilot IDs are protected
against shadowing. Duplicate canonical source registrations are rejected.

Each dataset generation declares nonoverlapping request windows. Ownership uses
the **native reference-period start**, not the lexical year label or publication
date. Adapters must query sufficient source coverage for week-ending/fiscal
labels, then return exactly the owned records.

Every page carries a content hash and a verified, pinned source snapshot/vintage
hash. The snapshot must agree across every page and partition of that dataset
generation. Content/page-chain hashes and definition hashes are retained.
Snapshot changes require an explicit full-generation restart, retaining the old
staging evidence. A client-invented constant is not a valid live snapshot proof.

Pages and opaque, unauthenticated checkpoints commit atomically to staging.
Expired/reassigned workers are fenced before writes and again before commit.
The SQLite worker lease caps this engine at one in-flight page across processes;
an in-process nonqueuing lock prevents concurrent use of one instance. No network
or parsing occurs inside a SQLite write transaction.

Only after **all declared partitions** finish does a short, streamed transaction
promote the dataset, capture changes and update its active-generation pointer and
dataset-specific completeness receipt. Partial/failed generations cannot replace
last-good observations. Missing historical rows inside replacement windows are
rejected; a withdrawal must be an explicit source null. A failure in one dataset
backs off independently while other due partitions remain eligible.

Defaults/caps:

| Bound | Limit |
|---|---:|
| Definitions in one engine | 64 |
| Windows per generation | 32 |
| Response body before parsing | 512 KiB |
| Records per page | 250 default, 1,000 maximum |
| Transport deadline | 20 s default, 30 s maximum |
| Pages per partition | 64 |
| Observations per generation | 10,000 |
| Promotion read buffer | 250 rows |
| Worker lease | 120 s |
| SQLite busy timeout | 2 s |
| Retry backoff | bounded exponential, up to 24 h; respects Retry-After |
| Storage admission | existing 256 MiB SQLite-family / 64 MiB free-space guards |

The actual transport must enforce response/deadline bounds while downloading.
The engine can reject a late returned page but cannot interrupt an arbitrary
blocking Python function. No unbounded transport is provided by this change.

## Permissions and migration

`partition_schema.py:migrate(connection)` is an **explicit additive version 2**
migration. There is no startup/CLI migration hook. It creates only new `norm_*`
registry, generation, partition, lease, page, staging, observation, revision, run
and active-generation tables/indexes, plus a version record in the Part 1 ledger.
It never alters, copies, deletes or resets old tables or research history.

All normalized dataset rows have CHECK constraints enforcing private display,
AI denial, Discovery exclusion and `rights_state='unreviewed'`. Completeness is
not a rights grant. The independent Part 1 scope-review ledger is never populated
or approved by ingestion. Unit-review/quarantined/partial-period data can remain
private but cannot receive a quality-passed publication completeness receipt.

Original `ingest_*` tables, their private-only CHECK constraints and all 2,403 WB
observations remain untouched. The existing stored reader cannot see `norm_*`.
No new dataset can reach the public catalog, Investigate, Discovery or AI here.

## Validation and measurements

Offline tests cover leap years, fiscal quarters/years, ISO week 53, timezone/DST,
source calendars, native formats, negative/zero/null values, duplicate and cyclic
pages, historical revisions/omissions, source outages/Retry-After, snapshot changes,
checkpoint restart, expired-worker fencing, promotion rollback, unavailable DB,
safe errors, privacy constraints and additive migration/backup restore.

Local full-suite result: **698 passed, five opt-in live-provider checks skipped**.
All **48 V2 frontend tests**, frontend lint/type-check, repository fatal-error Ruff
and full Ruff checks for the new implementation/tests/scripts passed. Linux build
and resource conclusions must be checked on the actual pushed commit.

The existing XLSX test helper now fixes ZIP timestamps: wall-clock metadata had
made identical synthetic workbooks hash differently during a longer test run.
Only the test fixture changed; production WB hash and transport behavior did not.

Local offline commands (the probe always creates its own temporary databases and
has no production database-path argument):

```text
python -m pytest backend/tests/test_native_partitioned.py -q
python scripts/validate_batch0_foundation.py
```

`scripts/batch0_partition_fixture.py` supplies 24 explicitly synthetic datasets,
six frequencies, 2,880 observations and a historical revision. The restore probe
starts from the original schema with 2,403 synthetic WB rows and saved research,
uses SQLite backup/restore, installs the new tables only on the restored disposable
DB, then hashes all old tables before/after the native workload.

The Linux harness retains the 309-entry manifest and runs native partition work in
the **same capped backend process and disposable SQLite DB** alongside API requests,
Discovery and the optional existing WB fixture worker. It asserts completion and
privacy. Limits remain 512 MiB RAM, no swap, 0.5 CPU and approximately 1 GiB disk.
Final GitHub workflow conclusions, memory/CPU/SQLite metrics and resource logs are
reported on PR #9 for the actual commit, not inferred from Windows measurements.

This tests a bounded mixed-frequency workload, not hundreds of simultaneous full
histories or real-provider network latency. Staging/revision/run evidence is
retained, so long-run retention/space policy still needs explicit review; the
admission guard stops writes without deleting history.

## Rollback — instructions only, no production operation authorized

No migration is needed to retain this inactive code. A future authorized migration
requires an independently verified consistent backup/restore, disk/WAL headroom,
reviewed SHA, unchanged persistent mount and disabled ingestion/AI settings.

Code rollback to Part 1 or e70 ignores the new tables. Leave all tables and captured
history in place; do not run a destructive reverse migration or replace SQLite.
Unfinished new work resumes from committed checkpoints after lease expiry. If a
source snapshot changed, explicitly restart the incomplete generation rather than
mixing pages or deleting staging. Do not restore an old DB over newer saved research
as ordinary code rollback.

## Precisely remaining for Part 3

1. Metadata-only paginated public API and visible-page previews; wire Explorer
   search/filters/pagination without loading every full history. Keep old endpoints
   compatible during transition.
2. Read-only normalized range queries using dataset/date indexes, current active
   generation and matching completeness/hash/definition checks. Generalize approved
   presentation beyond monthly-positive commodities without weakening existing
   rights, cursor, freshness and revocation checks.
3. Explicit annual/event/fiscal/weekly-date handling in API/frontend contracts,
   transformations, chart labels, comparisons and save/reopen versions. Preserve
   all existing calculations; no implicit frequency conversion or filling.
4. Independent display/AI/Discovery checks on every relevant path. Keep all pilots
   private and all new grants denied; no publication migration or activation is
   authorized by the existence of this foundation.
5. Full-catalog-scale metadata/history fixtures and combined Linux/browser tests,
   including performance, concurrency/backpressure and sustained storage growth.

Before later live ingestion: each provider still needs approved transport/access,
reliable snapshot or reconciliation evidence, exact units/selectors, sourced
release-calendar configuration, rights clearance and representative live-source
validation. ONS full legacy downloads and latest-only multi-page APIs need
source-specific methods within these bounds. Iron-ore unit/benchmark uncertainty
and WB redistribution/AI review remain unresolved. No production activation,
publication, source switch, paid service or deployment is authorized here.
