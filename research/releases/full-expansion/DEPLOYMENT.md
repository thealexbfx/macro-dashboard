# Approval-gated deployment and rollback

Nothing below has been run on production. The commands are a proposed operator
sequence, not authorization to execute it. No production access was used here.

## Review and prerequisite chain

1. Review Batch 0 draft PR #9, suitability draft PR #10 and the stacked expansion
   draft PR. Confirm final CI conclusions and exact reviewed SHAs. Merge only
   after explicit approval, in foundation → audit → expansion order, into the
   approved release branch. Do not directly push to the production branch.
2. Record both currently deployed Render SHAs and verify their actual commands,
   single-process backend, Python version and `/var/data` mount. Do not use the
   old blueprint. Verify ingestion/AI remain disabled. No setting change is needed.
3. Verify a consistent SQLite backup and disposable restore; download an
   independently SHA-256-verified off-Render copy. Record DB/WAL/SHM sizes and
   available disk. Existing production size/headroom is not known from this task.
4. Select an independent release unit and its exact canonical IDs. The complete
   new catalog measured about 348 MiB before legacy data/WAL; do not approve an
   all-at-once import without a combined storage calculation. Keep total DB/WAL
   below the 384 MiB release guard and enough free space for writes and recovery.
   Keep large source snapshots on ephemeral storage, not the 1 GB persistent disk.

## Separate approved operations

Deploy only the reviewed code after approval. Candidates remain invisible without
schema, data and explicit display grants. No startup migration or ingestion runs.
The database file is never replaced by code deployment or a bundled fixture.

After a separately approved backup/migration window, the proposed command is:

```sh
python -m backend.app.catalog.release_cli \
  --database /var/data/macrolens-v2.sqlite3 --operation migrate
```

It applies additive foundation versions 1/2 if absent and creates version 3 grant
and digest tables. It does not seed datasets, alter legacy tables, enable jobs or
change any permissions. The same command can be rehearsed on a disposable restore.

Capture a selected cleared unit outside production first, using only official
routes and no committed credentials. For example:

```sh
python -m scripts.collect_expansion --workspace /tmp/macrolens-capture \
  --providers eurostat --only-ids eurostat_03b4d5b0fa407ee1b32e
# Original-producer routes use --overrides. BLS full backfills also require
# --full-bls-history; --refresh creates a new immutable capture and retains
# the previous source index. Do not use --reuse-local-workbooks for fresh updates.
```

The collector refuses production-style `/var`/`/mnt` locations and never grants
display. Review source status, units, counts, missingness, capture time and hashes.
An unresolved/failed capture is not an eligible input. Transfer only approved
snapshots/index to the operator's ephemeral working directory, verifying hashes
and updating local snapshot paths in the index if necessary.

One approved bounded ingestion (maximum 16 IDs per invocation):

```sh
python -m backend.app.catalog.release_cli \
  --database /var/data/macrolens-v2.sqlite3 --operation ingest \
  --source-index /tmp/macrolens-capture/source-results.json \
  --ids eurostat_03b4d5b0fa407ee1b32e
```

This remains private. Stable snapshot/generation IDs prevent duplicate imports;
partial jobs retain checkpoints/backoff and existing active histories. Rerun with
the **same immutable snapshot index** after the reported cooldown. Do not replace
an incomplete generation with a different latest-source snapshot. Inconsistent
snapshots, missing history, units, source hashes or row/disk limits fail closed.
Exit code is nonzero for failed/waiting work. Verify the complete receipt before
requesting display approval.

Inspect safe internal progress, without printing values, private data or secrets:

```sql
SELECT g.dataset_id,g.state,p.state,p.page_count,p.failures,p.error_code,p.next_due
FROM norm_generations g JOIN norm_partitions p ON p.generation_id=g.id
WHERE g.dataset_id='eurostat_03b4d5b0fa407ee1b32e';
SELECT dataset_id,state,quality_passed,cursor
FROM catalog_dataset_completeness
WHERE dataset_id='eurostat_03b4d5b0fa407ee1b32e';
```

After separate explicit display approval:

```sh
python -m backend.app.catalog.release_cli \
  --database /var/data/macrolens-v2.sqlite3 --operation activate --approve-display \
  --ids eurostat_03b4d5b0fa407ee1b32e
```

Display activation requires the exact reviewed definition/rights evidence and a
complete source receipt. It grants neither AI nor Discovery. World Bank IDs and
all 30 legacy public IDs are rejected by the release registry/activation path.
No environment variable change or ingestion scheduling is required.

## Smoke checks after each small unit

* `/health` and `/ready`; existing 30 IDs, Discovery and saved investigations.
* Catalog filters/counts/pagination; selected ID metadata, bounded observations,
  preview and comparison; units, attribution, native labels and missing values.
* Private WB direct-ID requests still denied; no AI/Discovery scope grants.
* RSS/cgroup peaks, API error/latency, DB/WAL/SHM and remaining disk; stop if the
  software guard or operational headroom is approached. Never truncate history
  or remove a backup merely to force a batch through.
* Read a fresh public page after revoke/reapprove rehearsal on staging. Retain
  audit receipts and operator approval records; keep schedules disabled.

## Rollback without losing research

Revoke only the newly approved IDs (operator approval required):

```sh
python -m backend.app.catalog.release_cli \
  --database /var/data/macrolens-v2.sqlite3 --operation revoke \
  --ids eurostat_03b4d5b0fa407ee1b32e
```

This leaves all observations, revisions, saved research and source receipts in
place. Then restore the previously recorded backend/frontend **code revisions**
through the approved Render mechanism. Do not overwrite the SQLite file, run
down-migrations or delete additive tables. Older code ignores the new grant tables
and private normalized registrations; the 30 existing sources remain available.

A database restore is a separate incident action requiring approval and a plan
to preserve research written since the backup. It is not the routine rollback.
