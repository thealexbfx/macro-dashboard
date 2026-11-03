# Universal refresh and reviewed catalog release

Preparation only; no production deployment, permissions, ingestion or environment
changes have been executed. Base: `7260bdcebcddbaba2298fe13a2bf567ef1434764`.

## Reconciled scope

The live public metadata endpoint returned **100 unique public IDs** on 2 November
2026. The repository contains **313 unique IDs**: 309 manifest entries plus four
additional original-producer/suitability entries. This includes unresolved panels
and private/planned selections, not 313 implemented, rights-cleared series.

[CATALOG.csv](CATALOG.csv) reconciles every ID, source/selector, geography, frequency,
units, release status and blocker. The authoritative canonical **view** is
`backend.app.catalog.operations.registry()`, composing existing reviewed manifests,
overrides and publications without minting replacement IDs or a parallel permission
system. The CSV is an audit export, not a publication grant. SQLite grants and
definition-bound rights reviews remain authoritative at every public read.

[Publication plan](../../../catalog/publication_plan.json) contains **94 exact new
display approvals** for operator review. With the existing 100 this prepares **194**
public datasets. All 30 legacy IDs/definitions/history remain unchanged; 164 native
IDs are refresh-approved, 21 of the 185 integrated entries remain denied. Every new
AI/Discovery permission stays denied. World Bank's three unreviewed pilots are
excluded from source requests, grants, public APIs, charts, AI and Discovery.

The additions include remaining Eurostat macro/construction tables, ONS price/pay/
housing series, own BEA/Census national accounts/construction/orders, BoE monetary
stocks, ECB own policy/overnight/reference FX data, EIA physical inventories and
asphalt product supplied, ten Federal Reserve series including real yields/broad
dollar, and six DESNZ energy supply/demand series. No fictional Japan/China data or
automatic approval of new discoveries. The original 70 approvals remain intact.

Source/rights evidence is per ID in the plan. ECB euro reference FX is produced by
the central-bank concertation process, not licensed BoE/LSEG FX; it is information,
not an executable quote. See [ECB reference rates](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)
and [reuse policy](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html).
[Federal Reserve terms](https://www.federalreserve.gov/disclaimer.htm) permit own
Board statistics with attribution and third-party exceptions. [GOV.UK reuse](https://www.gov.uk/help/reuse-govuk-content)
and producer attribution cover these own DESNZ aggregate tables, not third-party
supplier microdata. Existing legacy commercial/secondary-source rights are inherited
and explicitly marked for review; this release does not recertify or broaden them.

## What changed

* Original 30: retain their existing release-aware persistent `source_cache` and
  supervised Discovery-triggered provider checks. Successful retrieval of an old
  economic reference period is distinct from a transport failure. Last-success,
  next-check and safe failure diagnostics persist inside existing payload metadata.
  Truncated histories or lost previously valid observations retain last-good data.
* Native sources: reuse one existing opt-in sequential worker, immutable source
  snapshots, full-history/definition/quality checks, partition cursors, revision
  history, conditional HTTP/content hashes, backoff and leases. Prepared but private
  refresh-only IDs are not scheduled. Revocation blocks already registered jobs.
* Federal Reserve: bounded official ZIP transport and streaming XML parser,
  explicit unit/frequency/adjustment attributes. The official DDP notice removes
  custom-package functionality, not the reviewed complete bulk ZIP route; no silent
  FRED substitution. Future endpoint retirement is an observable failure.
* DESNZ: documented GOV.UK Content API discovers exact current table attachments;
  logical producer-page identity and resolved artifact provenance are both retained.
  HTTP validators are reset on an artifact URL change. Both prefix and suffix
  `[provisional]`/`[revised]` labels are parsed and flagged; unknown monthly annotations
  fail instead of silently dropping new rows. This fixed omitted August 2026 data.
* BLS foundation: shared ten-year multi-series windows, durable daily reservations,
  retry/restart reuse and bounded immutable response cache. Failed requests consume
  quota. Metadata verification currently blocks publication (below).
* Schema 5: one additive `catalog_provider_requests` table and version marker; no
  drops, permission seeds, observation rewrite or automatic startup migration.

Native daily checks catch revisions between releases; exact native frequency,
reference periods and source release metadata remain independent. Legacy daily
series check every six hours, weekly twice daily, monthly/quarterly daily or closer
to a verified release hint. Native requests use conditional retrieval where supplied
and full semantic hashes otherwise; unchanged sources never create generations.
Full reconciliation remains necessary for unannounced historical revisions; this
release does not falsely describe every provider as supporting incremental APIs.

## Monitoring

Frontend `/data-health` is an administrator page. The existing admin token is entered
in memory only, never a URL, storage or report. Backend
`/api/v2/discovery/admin/data-health?offset=0&limit=100` requires admin authorization;
responses are no-store. It reports current public count, active coverage, verified
successful checks, latest observation, frequency, next check, errors, SQLite/WAL,
free disk and cgroup pressure. Source lag is a review signal, not a claim that an
unreleased observation exists. Disabled/uninitialized workers cannot appear healthy.

The existing scheduler logs a safe hourly health summary; individual refreshes log
last success/next due, failures and codes. No additional worker/service or paid
monitoring. The read-only CLI never assumes liveness from a shell process:

```bash
python -m backend.app.catalog.operations --database /var/data/macrolens-v2.sqlite3
```

## Remaining holds — not a claim that the whole catalog is complete

* **BLS 9:** actual full observation captures passed, but unregistered API catalog
  metadata is explicitly disabled, and `wp.series`, `ce.series`, `sm.series` official
  metadata requests returned HTTP 403. Unit/definition drift cannot be independently
  verified. Free registered catalog access or another approved official metadata
  route plus reviewed metadata fingerprints is needed. No header/proxy bypass.
* **UK materials 4:** official collection discovery contract and current DBT-owned
  table parsing tested, but latest available issue still returns May 2026 monthly/
  Q1 quarterly rows. Moving-issue/archive lineage, title/unit checks and publication
  lag need reconciliation before scheduler/publication approval; no BCIS/MPA data
  is assumed cleared by OGL.
* **USGS 5:** selected issues contain 18 months/five quarters only. Archive overlap,
  revisions, non-Q1 layouts and ScienceBase transition need a complete contract;
  do not silently turn a rolling issue into full history or splice historical units.
* **DOL 1:** current national form request failed XML parsing; year parameters now
  advance in the adapter contract but reliable complete-window transport is unverified.
* **SONIA 1 / EIA spot 1:** specific SONIA attribution/use review and underlying spot
  price redistribution evidence remain withheld. Technical download is not approval.
* **98 other planning IDs:** unresolved atomic selections, source authentication,
  rights/definition/access contracts, or private World Bank selections. Every ID has
  its source evidence/status in the CSV; these are not additional integrated series.

The ten previously blocked Board series and six DESNZ series are resolved for this
release. The original remaining 19 technical/definition holds plus two rights holds
stay unpublished. Complementary real/nominal/growth, SA/NSA, manufacturing/industry,
spot/futures and differently weighted dollar indices remain distinct; no semantic
overlap is resolved by silently retargeting saved IDs.

## Inputs and validation

Frozen source archive (outside git, no production/private data):
`C:/Users/algba/Documents/Codex/first-live-release/macrolens-universal.tar.gz`.
[archive.json](archive.json) records its SHA-256/size. It holds **94** source snapshots,
**123,370** observations. The original reviewed 70 baseline histories contribute
52,861 rows to the actual-source rehearsal (176,231 native total), plus 98,446
synthetic legacy observations. Never commit raw workbooks or database backups.
Inputs expire after seven days; recapture into a new directory and retest if delayed:

```bash
python -m backend.app.catalog.rollout prepare --bundle /NEW/OFF-RENDER/DIRECTORY
```

CI `Universal catalog release` captures actual sources, then rehearses schema 5,
100→private staging→194→100→194 under Python 3.14, 512 MiB, 0.5 CPU, no swap, network
disabled and a disposable 1 GiB ext4 disk, including independent staging CLI/API/
Discovery, all new ranges, 12 private denials, saved research and backup/restore.
`Catalog refresh capacity` tests repeated revisions/unchanged data and overload at
20/50/70/100/150/**164** native datasets alongside all 30 legacy datasets. Standard
Linux frontend build/lint/types/unit/browser and full Python CI remain enabled.
Final measured results and CI conclusions are attached to the PR; Windows RSS is
never labelled Linux evidence. No production access was used for these experiments.

Keep the 384 MiB DB/WAL, 96 MiB pending snapshot and 50k-generation guards; review disk
near 300 MiB. No larger Render plan is silently assumed. Failure of the maximum
capacity experiment blocks its activation. Do not extrapolate a safe 194 run into a
guarantee for arbitrary 200+ long daily histories: row count, revisions and proof
storage matter more than names. Canary actual production working headroom and
latency; separate workers/RAM will not fix a 1 GiB storage/proof ceiling. A larger
disk or bounded historical-rights/retention review is needed before that ceiling;
PostgreSQL is not required solely because the catalog has hundreds of names.

## Approved operator release — minimal routine steps

Nothing below has been run against production. Obtain approval for merge, both code
deployments, additive migration/private staging/display grants, backup writes if a
fresh backup is needed, and refresh activation. Reuse a current independent backup
receipt rather than repeating the manual process. If saved research changed since
that backup or it predates the 100-ID baseline, `apply` stops for renewal.

1. Merge the reviewed PR after final CI. Record its **resulting full deployment SHA**.
   Render backend: deploy that specific commit with catalog refresh paused. Preserve
   Python 3.14, existing pip build, one uvicorn process, WEB_CONCURRENCY=1, existing
   `/var/data` mount and database path; no legacy `render.yaml`. Backend first, then
   frontend same SHA using existing `frontend-v2` npm build/start and backend URL.
2. If renewal is needed, the following approved Windows command creates a new unique
   SQLite-backup-API copy, downloads it independently, compares SHA-256, integrity
   checks and disposable-restores it. It never replaces the live DB. SSH transport
   requires the existing registered key; this orchestration is locally tested,
   not an assertion of access to the Render shell from this release preparation.

```powershell
python -m scripts.catalog_backup --ssh srv-dbfb5g67bikc73crtb9g@ssh.oregon.render.com --identity "$env:USERPROFILE\.ssh\render_macrolens" --output-directory C:/Users/algba/Documents/Codex/first-live-release/backups --expected-revision FULL_APPROVED_DEPLOYED_SHA --approve-production-backup
scp -s -i "$env:USERPROFILE\.ssh\render_macrolens" C:/Users/algba/Documents/Codex/first-live-release/macrolens-universal.tar.gz srv-dbfb5g67bikc73crtb9g@ssh.oregon.render.com:/tmp/
```

3. Render Shell, after those approvals. Substitute the deployment SHA and backup
   path/hash from its verified independent receipt. No secret belongs in these values.

```bash
set -euo pipefail
cd /opt/render/project/src
echo 'd31dda06b4ba4be8facb9efcce0f1c02d724114a801f65f2df9a0259b641df4a  /tmp/macrolens-universal.tar.gz' | sha256sum -c -
test ! -e /tmp/macrolens-universal
tar -xzf /tmp/macrolens-universal.tar.gz -C /tmp --no-same-owner --no-same-permissions
REV='FULL_APPROVED_DEPLOYED_SHA'
BACKUP='/var/data/ACTUAL_VERIFIED_BACKUP.sqlite3'
BACKUP_SHA='ACTUAL_TRUSTED_INDEPENDENT_SHA256'
COMMON=(--database /var/data/macrolens-v2.sqlite3 --bundle /tmp/macrolens-universal --expected-revision "$REV")
APPROVED=(--approve-production --off-render-backup-verified --backup "$BACKUP" --backup-sha256 "$BACKUP_SHA")
python -m backend.app.catalog.rollout apply "${COMMON[@]}" "${APPROVED[@]}" --approve-migration --approve-publication
python -m backend.app.catalog.rollout verify "${COMMON[@]}"
python -m scripts.smoke_catalog --origin https://macrolens-v2-backend.onrender.com --approved-live-read-checks
python -m scripts.smoke_catalog --origin https://www.macrolensresearch.com --approved-live-read-checks
```

`apply` verifies backup/restore/revision/baseline/privacy/capacity, applies only the
additive migration, stages <=5 sequential IDs/16×250-row pages per ID per invocation,
resumes durable checkpoints, validates all frozen rows, then atomically grants only
the 94 reviewed IDs. There is no migration/ingestion/publication at startup. It
requires 128 MiB working-memory headroom after inactive cache and 150 MiB free disk.
An interruption is resumable with identical inputs; wait for any <=120s worker lease
to expire, never reset tables. The CLI never enables refresh or changes Render.

4. After both smokes pass, approve Render backend environment activation:
   `MACROLENS_CATALOG_REFRESH_ENABLED=1`; save/restart the same approved SHA.
   Keep `MACROLENS_INGESTION_ENABLED` absent/0 and `MACROLENS_AI_ENABLED=false`.
   Preserve `MACROLENS_V2_STATE_DB=/var/data/macrolens-v2.sqlite3`, WEB_CONCURRENCY=1,
   frontend `MACROLENS_V2_API_URL=https://macrolens-v2-backend.onrender.com`, existing
   disks, service sizes and auto-deploy setting. No additional workers.

Allow roughly three hours plus retries for 164 staggered initial native checks.
Require protected health active coverage **194/194**, then actual successful checks
for all IDs, no persistent source failures/OOMs/readiness failures, advancing next
checks, adequate disk reserve and acceptable latency over 24–48h. Never label mere
configuration as successful source verification. Failed providers remain visible
and retain last-good data. Routine subsequent refreshes need no shell commands.

## Rollback, separately approved

Disable catalog refresh in Render and restart first, then:

```bash
python -m backend.app.catalog.rollout rollback "${COMMON[@]}" "${APPROVED[@]}" --approve-rollback
```

Only these 94 new display grants/reviews are revoked; all observations, revisions,
research, original 100 grants and private pilots remain. Rollback is idempotent. If
necessary redeploy `7260bdcebcddbaba2298fe13a2bf567ef1434764`, backend then frontend,
with refresh paused until its existing 70-ID configuration is deliberately resumed.
Leave schema 5/table in place; old code ignores it. Do not restore/overwrite the live
database as a routine code rollback. Schema 4→5 backup/disposable restoration and
forward/backward reads are tested. Keep the off-Render backup independently; avoid
accumulating same-disk copies to the 1 GiB limit. No backup is deleted by this release.

## Adding the next dataset

Add a stable atomic ID/definition and source-owner evidence through the existing
manifest/override mechanism, implement/test its bounded official parser, validate
history/calendar/units/revisions, review rights/attribution, and add its explicit
entry to a new versioned publication plan plus refresh policy. Derive that plan's
baseline from verified current public IDs. Run capture, capacity/privacy tests and
review the PR. Availability, ingest success or a config entry never grants display,
AI or Discovery. No code-level 100/185 target needs changing for subsequent releases.
