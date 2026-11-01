# Bounded catalog ingestion and refresh

Development only. Production has not been accessed or changed. Based on deployed
commit `7f04cf270140d091599dbe058c873b75aed019e9`. All 185 configuration entries
have `ingest_approved=false`; `MACROLENS_CATALOG_REFRESH_ENABLED` defaults to 0.
The independent World Bank worker and its existing switch are unchanged.

## Candidate result

The existing 185 integrations include the 13 now public: **172 remain additional**.
Reusing the committed rights/definition reviews, **150 have current-source routes**
supported by the new refresh worker, including all 13 public native datasets:
**137 additional candidates** can proceed to controlled private staging and
per-ID publication approval. Fresh official downloads/parsing/definition checks
passed for all 150 on 1 November 2026 (see `official-source-checks.json`). That is
a source check, not a guarantee of permanent access or a new redistribution grant.

| Provider | Current-route candidates |
|---|---:|
| Eurostat | 78 |
| ONS, including current construction workbook | 26 |
| Census | 15 |
| BEA | 9 |
| ECB | 8 |
| Bank of England | 7 |
| EIA official historical XLS downloads, no paid API | 7 |

The other **35 need targeted adapter work**: BLS 9 (batched historical reconciliation
and shared free-request budget); Federal Reserve 10 (announced DDP retirement and
large bulk-source continuity); DESNZ 6 and UK building materials 4 (dated workbook
discovery); USGS 5 (dated issues/rolling coverage); DOL 1 (bounded year-window POST).
These are technical holds, not newly discovered legal prohibitions. Their existing
source-owner rights evidence, units and definition limitations are preserved in
`candidates.json`; all 98 earlier unresolved selections remain outside this worker.
OECD, Japan and private World Bank rights are not inferred from API availability.

## Implementation

* `catalog/refresh_policy.json` is the bounded ID allowlist, cadence and staging or
  refresh configuration. It is not a publishing authority. `stage` imports privately;
  `refresh` requires the existing display permission first. Unknown IDs, all legacy
  public IDs and the three World Bank IDs cannot enter this registry.
* Explicit schema-4 migration adds only `catalog_refresh_jobs`. No startup migration,
  dataset activation or rights changes. Persistent last-attempt/check/success/change,
  failures, safe error codes, next due, HTTP validators and snapshot checkpoints.
* Existing supervisor dispatches one background thread; one dataset and at most
  sixteen 250-record pages per dispatch. Larger histories resume from checkpoints.
  The daily cadence is a **source check**, not a manufactured publication date.
  Per-ID check intervals can be configured from one to 31 days; official next-release
  metadata is retained separately. No inference of observation frequency or release
  calendar from polling cadence.
* Conditional GET where supported, raw hashes plus normalized observation hashes.
  Retrieval timestamps or response formatting changes alone do not create generations.
  Adjacent selections share one bounded response; 429 cools the provider for an hour;
  temporary failures back off from five minutes to a day; 401/403 are not bypassed.
* Downloads/parsing occur outside write transactions. All Store instances for the
  same file share an in-process writer lock; SQLite BEGIN IMMEDIATE, short timeouts,
  worker leases and generation fencing remain the cross-process safeguards. Busy
  writes defer; requests may still receive the existing bounded 503 under overload.
* Native dates, nulls, zeros, negatives and source flags are preserved. Definition,
  unit, duplicate, quality and full-history coverage checks run before promotion.
  An unexplained non-null-to-null change is quarantined; explicit flagged missing
  revisions can pass. The existing transactional generation engine records revisions
  and preserves last-good public data on failed/partial imports.
  Refresh promotion retains existing per-observation proofs for unchanged rows,
  avoiding full-history rewrites/duplicate receipts for a small revision. The new
  generation still verifies the complete source response; old readers already
  support observations backed by multiple completed generations.
  A per-window parsed snapshot cache avoids decoding/sorting the same source for
  every page; every page still reads and verifies the complete snapshot SHA-256.
* Publication is still a separate, explicit `release_cli activate --approve-display`
  operation after per-ID approval and complete receipts. No worker writes grants,
  scope reviews, legacy datasets, saved research or World Bank tables. AI and
  Discovery remain denied independently, including after display activation.
* Live metadata reports last source check/change. After EIA updates, obsolete frozen
  release-week attribution is replaced with current source-check attribution, not a
  fabricated publication timestamp. Native retrieval time remains distinct.

## Storage and retention

The existing 384 MiB combined DB/WAL software guard and 64 MiB minimum free-space
guard remain in force. Refresh snapshots have a separate 96 MiB ceiling; only
pending snapshot files are retained after successful work. Operator archives and
backups are never touched. Completed initial-release proofs are preserved.

For refresh-created generations only, the active and one preceding completed set
of per-row/page proofs are retained. Older unreferenced proof detail is compacted;
generation identities, snapshot hashes, aggregate completeness hashes, all current
observations and all historical revision payloads are preserved. No VACUUM,
database replacement or automatic research/history deletion. SQLite reuses freed
pages; it need not shrink the database file. Immutable revision history and small
generation metadata still grow, so the storage guard **stops safely** at capacity.

## Verification

Run `python -m pytest -q` and the existing frontend validation workflow. The offline
capacity harness is `python -m scripts.validate_catalog_refresh --datasets 150
--output /tmp/capacity.json` (also supports 20/50/70/100 native datasets). It creates
new temporary databases and 30 synthetic legacy caches, includes all 13 live IDs,
and exercises 2,403 synthetic private WB rows, saved research, the real scheduler,
API/compare/Discovery traffic, source checks, unchanged checks, full-history revisions
and controlled overload. Observation counts/definitions match actual captured
profiles; values and transport are **synthetic**, not new economic evidence.
The final workload seeds the original 30 caches at their declared daily/weekly/
monthly/quarterly frequencies from 1990 (98,437 observations), rather than using
short monthly histories for every legacy series. Discovery is warmed before the
disabled-worker baseline; three revision cycles exercise retention and restart
checkpoints. Ingestion dispatch is accelerated, with Discovery scans once/second
(production remains once/minute). Per-path status counts distinguish bounded
analysis contention from catalog/read failures. Linux SQLite runs on a disposable
1 GiB ext4 mount as well as the CPU/RAM/swap limits.

GitHub workflow `catalog-refresh.yml` runs these under Python 3.14, 512 MiB RAM,
zero swap and 0.5 CPU, with network disabled during workload tests. Separate actual
official format checks run under the same limits with network access. Artifacts
contain metrics/metadata only. This does not reproduce Render's exact warmed cache
or every provider's future workbook; a production canary remains necessary.

## Approval-gated rollout and rollback

1. Review/merge PR only after approval and final CI. Verify an independent current
   backup and disposable restore; check backend readiness, disk and memory headroom.
2. Deploy backend code with BOTH ingestion and catalog refresh disabled. No frontend
   deployment is required for this backend-only change. Verify the existing 43 IDs,
   saved research and World Bank denial. Database path/mount remain unchanged.
3. With separate migration approval, run:
   `python -m backend.app.ingestion.catalog_refresh --database /var/data/macrolens-v2.sqlite3 --operation migrate`.
   Verify status using the same command with `--operation status`. This does not
   create jobs or publish anything.
4. Approve exact IDs and a reviewed configuration commit. First authorize only the
   existing 13 in refresh mode. Separately approve enabling
   `MACROLENS_CATALOG_REFRESH_ENABLED=1`; do not enable the World Bank worker.
   Review protected admin diagnostics `/api/v2/discovery/admin/diagnostics`, logs,
   resource metrics and source freshness over an actual release cycle.
5. To reach 100 total public IDs, stage **57 additional IDs** in batches of 5–10,
   validate complete histories/units/rights/attribution and then obtain explicit
   display approval for each batch. Use the existing release CLI activation in
   batches of at most 16; AI/Discovery remain denied. Move approved IDs to refresh
   mode in the next reviewed configuration. No additional API or UI integration.
6. Only expand beyond 100 after resource measurements and operational canary pass.
   Current automatic source coverage supports at most 180 public IDs (30+150),
   not 200+. Resolve at least 20 of the 35 adapter holds, then repeat source,
   definition and capacity tests before approving 200. No architecture rewrite
   is needed just to add reviewed adapters/configuration.

Rollback: disable the new refresh switch (separate operator approval), let the
bounded request/page finish, and roll back backend code to `7f04cf2`. Keep all new
tables and ingested observations: old readers ignore the refresh ledger. Existing
43 display grants and private WB records are unchanged. Do not restore/replace the
live DB as a routine rollback. Revoke only specifically approved new display grants
if needed using the existing explicit `release_cli revoke` operation; never reset
the database or change unrelated permissions.

No paid services, credentials or hosting changes are introduced. Incremental
infrastructure subscription cost is zero on the existing plan; CPU/disk consumption
must pass the measured capacity gates before enabling it. Do not attach a second
service to the SQLite disk. A separate worker requires an explicitly reviewed
database-access design, normally PostgreSQL when independent concurrent services
or sustained write throughput require it; dataset count alone is not that trigger.
