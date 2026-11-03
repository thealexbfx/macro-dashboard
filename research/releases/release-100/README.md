# Coordinated release: 43 → 100 public datasets

Preparation only. No production changes have been executed. Reviewed deployed base:
`922af3849b53e470ddaab19a6839c545939e15fd`. Production is already schema 4: this
release **checks**, never automatically applies migrations. No database replacement.

## Exact scope and approvals

[Selection](selection.json) is the authority: **57 new display approvals**, plus
refresh approval for those 57 and the existing 13 native public IDs. All 30 legacy
public IDs and existing 13 grants stay intact. The [readable list](DATASETS.md)
includes names, countries, frequency and units via the linked machine manifest.
All 185 refresh-policy entries remain present; exactly **70** are ingestion-approved,
in `refresh` mode, which requires a pre-existing display grant. **115 stay denied.**
The global scheduler flag still defaults off. New grants always deny AI/Discovery.

The additions cover nine complementary macro concepts for DE/FR/IT/exact EA21
(inflation, unemployment, manufacturing, retail volumes, investment, consumption,
exports, imports, public debt); nine UK price/labour/consumer/construction series;
four US income/savings/GDP-level/investment series; four US construction/orders
series; UK Bank Rate/mortgage approvals; ECB deposit rate/M3. US real GDP level
does not replace the existing GDP **growth** ID. Currency units, chain-linked bases,
SAAR versus monthly flows, EA21 geography and ONS rolling labour periods remain
explicit. No Japan/China series are invented from unresolved catalog entries.

## Evidence and holds

[Audit](audit.json) covers all **185** integrations: **150** fresh official-source
technical checks passed; **35** retain explicit technical holds. An archived
successful download is not certification of current release eligibility.
[Rights](rights.json) records checked official terms and selected source-owner scope;
the per-ID selection binds the precise definition, source, attribution and evidence.
Unselected availability never grants permission. Eurostat third-country/restricted
trade exclusions, ONS third-party exclusions, BoE licensed FX exclusions and ECB
third-party exclusions are respected. No new EIA spot-price approval is included.
Existing physical EIA statistics retain the original dated acknowledgment, with
source-check/file-modified dates distinguished from publication dates.

Holds: BLS 9 (bounded multi-series quota/reconciliation), Federal Reserve 10 (DDP
continuity), DESNZ 6 and UK materials 4 (dated release discovery), USGS 5 (rolling
archive coverage), DOL 1 (year-window adapter/reliability). These remain disabled,
as do the three private World Bank pilots and their unreviewed rights.

## Reproducible off-Render inputs

The reviewed current captures contain **52,861** native rows: **43,569 additions**
and the existing **9,292** pilot-release rows. Source observations are not committed.
The frozen archive is outside git:

`C:/Users/algba/Documents/Codex/first-live-release/macrolens-release100.tar.gz`

SHA-256: `6350b683007ccc6a931e652e6b65b83ec725b6d40d8b5f91d9c36b705f818633`

Size: **457,566 bytes**. It contains only reviewed official-source captures, metadata
and checksums, no production database or private research. The canonical JSON plan
hash is independent of Windows/Linux line endings. Every snapshot hash, exact ID,
source URL, definition and row count is verified before use. Inputs expire after
seven days: recapture/rehearse if the release is delayed; do not override the gate.

To reproduce into a **new** directory, off Render only:

```powershell
python -m backend.app.catalog.release100 prepare --bundle C:/Users/algba/Documents/Codex/first-live-release/release100-new
```

This audits all 185 and downloads/parses the 150 current-route candidates, freezing
only the approved 70. Any selected failure prevents a complete manifest. A recapture
produces a new archive checksum: record it and rerun disposable validation before
using it. Do not mix snapshots/indexes from different captures.

## Operator approval gates — do not execute without approval

1. Merge the reviewed PR only after explicit approval and final CI. Record the
   resulting **full approved deployment SHA**, not the pre-merge PR SHA.
2. Render backend → Manual Deploy → Deploy a specific commit → approved SHA.
   Preserve existing repository/root/build/start configuration, Python 3.14, one
   process/worker, `/var/data` disk and `/var/data/macrolens-v2.sqlite3`. Do not use
   the legacy `render.yaml`. Compatible V2 entry point is
   `uvicorn backend.app.v2.main:app --host 0.0.0.0 --port "$PORT" --workers 1`;
   the existing pip build installs `requirements.txt` and `backend/requirements.txt`.
   Do not edit settings merely to match example whitespace/options.
3. Keep `MACROLENS_CATALOG_REFRESH_ENABLED=0` (or unset),
   `MACROLENS_INGESTION_ENABLED` unset/0, `MACROLENS_AI_ENABLED=false`,
   `MACROLENS_V2_STATE_DB=/var/data/macrolens-v2.sqlite3`, `WEB_CONCURRENCY=1`.
   Auto-deploy remains disabled. Health/readiness and existing 43 must pass.
4. Frontend code is unchanged and already supports the dynamic catalog. No frontend
   deployment is required to expose grants. If deploying both services together,
   deploy frontend **second**, same approved SHA, using its existing `frontend-v2`
   root, `npm ci && npm run build`, existing start command/PORT and unchanged
   `MACROLENS_V2_API_URL=https://macrolens-v2-backend.onrender.com`. Check the site.
5. Confirm the independent fresh backup and successful disposable restore still
   cover the release baseline; keep the trusted backup hash and server-side backup
   filename. A same-disk backup alone is insufficient. Do not overwrite that backup.
   Check >=150 MiB free **after** inputs/backup, 384 MiB DB/WAL hard guard and >=128
   MiB effective working-memory headroom. The CLI refuses failed gates. File-cache
   saturation is distinct from application RSS; inspect cgroup inactive_file too.

### Transfer and verify (Windows PowerShell)

Use the existing registered key; enter any passphrase privately:

```powershell
scp -s -i "$env:USERPROFILE\.ssh\render_macrolens" C:/Users/algba/Documents/Codex/first-live-release/macrolens-release100.tar.gz srv-dbfb5g67bikc73crtb9g@ssh.oregon.render.com:/tmp/
```

### Render Shell — checks first

```bash
set -euo pipefail
cd /opt/render/project/src
echo '6350b683007ccc6a931e652e6b65b83ec725b6d40d8b5f91d9c36b705f818633  /tmp/macrolens-release100.tar.gz' | sha256sum -c -
test ! -e /tmp/macrolens-release100
tar -xzf /tmp/macrolens-release100.tar.gz -C /tmp --no-same-owner --no-same-permissions

REV='FULL_APPROVED_DEPLOYED_SHA'
BACKUP='/var/data/ACTUAL_VERIFIED_BACKUP_FILENAME.sqlite3'
BACKUP_SHA='ACTUAL_TRUSTED_SHA256_FROM_OFF_RENDER_VERIFICATION'
COMMON=(--database /var/data/macrolens-v2.sqlite3 --bundle /tmp/macrolens-release100 --expected-revision "$REV")
APPROVED=(--approve-production --off-render-backup-verified --backup "$BACKUP" --backup-sha256 "$BACKUP_SHA")
python -m backend.app.catalog.release100 check "${COMMON[@]}"
```

Replace only the three operator-specific placeholders with verified information.
Stop if hash, revision, schema, public IDs, rights, privacy or resource checks fail.
Do not delete an existing bundle directory: verify/reuse the identical inputs or
choose a new directory. CLI preparation is deliberately forbidden on Render.

### Separately approved private staging and publication

```bash
python -m backend.app.catalog.release100 stage "${COMMON[@]}" "${APPROVED[@]}" --max-invocations 64
python -m backend.app.catalog.release100 validate "${COMMON[@]}"
# Obtain separate approval for the exact 57 display grants before this command:
python -m backend.app.catalog.release100 publish "${COMMON[@]}" "${APPROVED[@]}" --approve-publication
python -m backend.app.catalog.release100 verify "${COMMON[@]}"
python -m scripts.smoke_release100 --origin https://macrolens-v2-backend.onrender.com --approved-live-read-checks
python -m scripts.smoke_release100 --origin https://www.macrolensresearch.com --approved-live-read-checks
```

Staging uses at most five sequential datasets / sixteen 250-row pages per dataset
per invocation; checkpoints are durable. It never touches the existing 13 histories,
legacy caches, research or WB tables. Repeat the **same** immutable input command
after a bounded deferral/interruption. If a lease is still held after a killed
process, wait for its <=120s expiry; never reset/delete staging tables. Investigate
any provider/quality/integrity error before retry. Validation compares every stored
new observation/label/flag with its frozen input and complete receipt. Publication
is one atomic transaction; a repeated completed command is a no-op. Staging after
publication skips public IDs, so an old bundle cannot overwrite refreshed data.

### Separately approved refresh activation

Only after both 100-dataset smokes pass, Render backend → Environment: set
`MACROLENS_CATALOG_REFRESH_ENABLED=1`, keeping WB ingestion/AI disabled. Save/restart
the backend on the **same approved SHA**; verify the deployment revision. Do not
just export a shell variable: that does not change the running server's environment.
No other settings or services change. This step is manual; no script enables it.

All 70 check official sources daily because revisions can arrive between scheduled
statistical releases. Source native frequencies and supplied release metadata are
retained independently. Initial checks are staggered by source URL, one/minute;
allow ~90 minutes for the first pass plus bounded retries. Adjacent selections
share responses, HTTP validators/content hashes avoid unnecessary work, Retry-After
is respected, 429 pauses the provider, and failures retain last-good public data.

## Monitoring and rollback

Protected `/api/v2/discovery/admin/diagnostics` reports catalog-refresh enabled state,
jobs, last-check/success/change, failures/error codes and next due. Existing admin
authorization is required; never paste its token into reports. Render logs use the
existing uvicorn INFO stream; errors contain safe codes, not bodies/credentials.
Read-only DB diagnostics:

```bash
python -m backend.app.ingestion.catalog_refresh --database /var/data/macrolens-v2.sqlite3 --operation status
```

After the first pass require 70 registered jobs, each last_success set, no persistent
failures, original 43+57 visible and 12 WB denial checks passing. Recheck after 24–48h:
success age <48h, next_due advancing, no OOMs/restarts/readiness failures, acceptable
latency (investigate sustained p95 >1s or steady read refusals), disk reserve intact.
No paid alerting or new cron service is required. Partial failures are per dataset,
observable and retryable, never a reason to publish an incomplete history.

Rollback requires approval: disable the **catalog refresh** flag in Render and
restart first; verify it is off, then:

```bash
python -m backend.app.catalog.release100 rollback "${COMMON[@]}" "${APPROVED[@]}" --approve-rollback
python -m scripts.smoke_first_release --origin https://macrolens-v2-backend.onrender.com --activated --approved-live-read-checks
python -m scripts.smoke_first_release --origin https://www.macrolensresearch.com --activated --approved-live-read-checks
```

Only the 57 new grants/reviews are revoked. Current observations, revisions,
research, WB data and the original 43 grants remain intact. Repeat is safe. If code
rollback is needed, manually deploy `922af3849b53e470ddaab19a6839c545939e15fd`, backend
first, with refresh disabled; no schema rollback/DB restore. Do not replace the live
database as routine rollback. Back up pending snapshot files too if checkpoint
recovery after a full disk loss is required; completed data/proofs are in SQLite.

## Validation evidence and limits

`scripts.validate_release100` exercises real frozen 70 histories through separate
CLI subprocesses alongside a real backend/Discovery/API with 98,437 synthetic legacy
observations. It tests 43→private stage→100→43→100, idempotency, exact source values,
privacy, saved history, integrity and backup/restore. CI uses Python 3.14, 512 MiB,
0.5 CPU, no swap, and a disposable 1 GiB ext4 filesystem; input capture is separate
and official, while the mutation rehearsal is network-isolated. Existing frontend,
backend, source and larger catalog capacity workflows remain enabled.

The prepared selection needs no paid credentials or new hosting. Existing framework
limits remain 384 MiB DB/WAL, 96 MiB pending snapshots and 50k rows per generation.
Retain independent backups without filling the 1 GiB disk; review storage near
300 MiB before hitting the hard stop. Current measured Linux results cannot certify
Render's exact warmed cache: canary the first refresh and stop further expansion if
working-memory or latency margins fail. Long daily Investigate histories retain the
existing 2,000-point analysis budget: narrow the range rather than interpolate data.
