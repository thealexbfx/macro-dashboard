# First live release preparation

**Production gate: NOT YET CLEARED.** No merge, deploy, production migration,
ingestion or display activation has been performed. The approved operation remains
preparation only. See [the 13 exact datasets](DATASETS.md), [definitions and rights](selection.json)
and the existing [deployment instructions](../full-expansion/DEPLOYMENT.md).

## Verified independently

On 31 October 2026, the website, backend `/health` and `/ready` returned HTTP 200;
database readiness was true and scheduler consecutive failures were zero. These
endpoints do not identify the deployed SHA or prove ingestion/AI configuration.

PR #9: `1bf62919d1395149ffad8b39c0664adfee4d956d`, base `feature/macrolens-v2`
at `e70e338a546afb64bf1e427f12bd63532f7ec9b4`.
PR #10: `4f974da1f35092f8eebacaf0ac48979b881ecf12`, base #9's branch.
PR #11's preceding reviewed head: `002bce0e3d60ed7926eebb925df8aaf20c149a3c`,
base #10's branch. All were draft, unmerged and conflict-free, with all associated
CI runs successful at that check. Release-preparation changes add the Eurostat
modification disclaimer, dated EIA citations, this package and smoke checks;
the final updated SHA/CI conclusions are recorded on PR #11.

The local downloaded backup `macrolens-pre-deploy-20261030-164034.sqlite3` passed
SQLite integrity and a backup-API restore to a new disposable file. A complete
13-dataset migration/ingest/display/revoke rehearsal preserved every original
table's record fingerprint and all 2,403 private WB observations. Original backup
bytes were unchanged. The private local receipt is outside git at
`C:/Users/algba/Documents/Codex/first-live-release/rehearsal-03/receipt.json`.
No trusted Render-side checksum was available to compare, and freshness against
the running database was **not** established. This does not clear the fresh-backup gate.

Fresh official captures contain **9,292 rows / 8,502 non-null**. First, middle
and last non-null source samples matched SQLite. Same-snapshot reruns added no
observations. API tests passed with 30 IDs before activation, 43 after activation
and 30 after revocation, including 12 WB denial cases at each phase, two native
comparisons and independently denied AI/Discovery scopes.

The restored 4.51 MiB backup grew to **17.80 MiB SQLite**, with **6.71 MiB WAL**
and 32 KiB SHM; sampled combined peak was 24.54 MiB. Allow at least **50 MiB of
additional working storage** for this batch, separately from the existing DB,
backup retention and emergency reserve. Require at least 150 MiB confirmed free
disk before proceeding and keep the default 384 MiB software guard. This is a
conservative release gate, not a measured production free-space claim. Current
Render memory must also be checked; pause if less than 128 MiB operating headroom
is available or recent OOM/worker failures exist. CI measures standalone ingestion
for the exact thirteen under 512 MiB/no swap/0.5 CPU, separately from the existing
eight-history loaded-backend workload. It does not reproduce production's cache.

## What to copy from Render — read only

1. Open [Render Dashboard](https://dashboard.render.com). Select
   **macrolens-v2-backend**, service `srv-dbfb5g67bikc73crtb9g`.
2. Open **Deploys** (some dashboards label this **Events**). Open the currently
   **Live** successful deploy. Copy its full commit SHA and deployment time.
   Repeat for the frontend service identified by `www.macrolensresearch.com` in
   **Settings → Custom Domains**. Copy that service's name/ID too.
3. Open **Settings** for each service. Copy repository, branch, root directory,
   runtime, build command, start command, instance count/plan and auto-deploy
   setting. Do **not** click Edit/Save or any deployment controls. Backend should
   use the V2 entry point `backend.app.v2.main:app`, one worker and `/var/data`;
   frontend should build `frontend-v2`. These are expectations, not verified
   dashboard settings. The repository's `render.yaml` is legacy Streamlit: do not use it.
4. Backend **Disk/Disks**: copy mount path, configured capacity and usage/free
   space. **Metrics**: select the last hour, then last 24 hours; copy current and
   highest memory/CPU values, and note any restart/OOM events. Repeat memory/CPU
   for the frontend. Do not restore a disk snapshot.
5. **Environment**: check only `MACROLENS_INGESTION_ENABLED` and
   `MACROLENS_AI_ENABLED`; report unset/disabled/enabled, without copying other
   variables or secrets. Verify the backend DB path and frontend
   `MACROLENS_V2_API_URL` point at the existing V2 services. Copy only non-secret
   host/path information, not credentials, tokens or deploy hooks.
6. Backend **Shell**: the following optional command reads only sizes, resource
   files and explicitly named non-secret configuration. Copy its JSON output.
   It neither opens nor modifies SQLite. If Shell is unavailable, say so.

```sh
python - <<'PY'
import json, os, platform, shutil
from pathlib import Path
p = Path('/var/data/macrolens-v2.sqlite3')
def text(name):
    try: return Path('/sys/fs/cgroup', name).read_text().strip()
    except OSError: return 'unavailable'
def flag(name, enabled):
    v = os.getenv(name)
    if v is None: return 'unset'
    if v.lower() not in {'0','1','true','false',''}: return 'unrecognized; value withheld'
    return 'enabled' if enabled(v) else 'disabled'
d = shutil.disk_usage('/var/data')
workers = os.getenv('WEB_CONCURRENCY', 'unset')
print(json.dumps({
  'revision': os.getenv('RENDER_GIT_COMMIT', 'unavailable'),
  'python': platform.python_version(), 'cwd': os.getcwd(),
  'web_concurrency': workers if workers == 'unset' or workers.isdigit() else 'unrecognized',
  'configured_db_matches': os.getenv('MACROLENS_V2_STATE_DB') == str(p),
  'ingestion': flag('MACROLENS_INGESTION_ENABLED', lambda v: v == '1'),
  'ai': flag('MACROLENS_AI_ENABLED', lambda v: v.lower() == 'true'),
  'sizes_bytes': {s or 'database': Path(str(p)+s).stat().st_size if Path(str(p)+s).exists() else 0 for s in ('','-wal','-shm')},
  'filesystem_bytes': {'total':d.total,'used':d.used,'free':d.free},
  'memory_current':text('memory.current'),'memory_peak':text('memory.peak'),
  'memory_max':text('memory.max'),'memory_events':text('memory.events'),
  'swap_current':text('memory.swap.current'),'cpu_max':text('cpu.max')
}, indent=2))
PY
```

The Render-side backup SHA and timestamp must match the independently downloaded
file before any production database operation. If the old backup cannot be shown
to cover current research/history, a fresh consistent SQLite backup and off-Render
download/restore are required. Backup creation is a separately approved operation;
do not overwrite the database or an existing backup. Do not send the backup to GitHub.

## Approval-gated execution order

1. Clear the dashboard, resource, backup and rights gates above. Verify auto-deploy
   is disabled **before any merge**; otherwise merging can deploy implicitly.
2. Obtain explicit approval to mark ready/merge #9 into `feature/macrolens-v2`.
   After it merges, retarget #10 to that release branch, wait for the new-base CI
   and review checks, then merge only with approval. Repeat for #11. Do not merely
   merge #10/#11 into their old feature bases. Preserve reviewed history with merge
   commits. Record and verify the **final release merge SHA**, not a guessed SHA.
3. After explicit deployment approval, backend **Deploys → Manual Deploy → Deploy
   a specific commit**: use that exact release SHA. Verify health/readiness and the
   same persistent mount/database; allow for a brief disk-backed backend restart.
   Then deploy the frontend at the same SHA. Do not change commands/environment,
   run a blueprint sync, or replace `/var/data`. Check that only 30 IDs are visible.
4. Capture the exact selected histories to **ephemeral** `/tmp`, check all thirteen
   completed and match the reviewed definitions/vintage, then obtain/confirm the
   additive-migration and bounded-ingestion approvals. If counts/units/citations
   have changed, stop and validate the new source vintage before ingestion.
   The preferred inputs are already frozen in the operator-held local archive
   `C:/Users/algba/Documents/Codex/first-live-release/first-live-13-inputs.tar.gz`
   (95,032 bytes, SHA-256
   `d84997750a2111c04778e9679ed5e55283c8fe44c22263833bdbb2312df1a617`).
   Its index uses `/tmp/macrolens-first-live/snapshots/` paths and contains only
   the thirteen public-source histories, never production records. Keep this
   off-Render copy throughout the release so a restart cannot destroy the only
   recoverable job inputs. After approval, transfer it using an existing approved
   Render SSH/SCP method, verify the hash, and extract only into `/tmp`:

```sh
echo 'd84997750a2111c04778e9679ed5e55283c8fe44c22263833bdbb2312df1a617  /tmp/first-live-13-inputs.tar.gz' | sha256sum -c -
tar -xzf /tmp/first-live-13-inputs.tar.gz -C /tmp --no-same-owner --no-same-permissions
```

   Do not overwrite a different existing capture or lose the frozen index during
   retries. If transfer access is unavailable, the official collector below is an
   alternative, but retain an off-Render copy of its **exact** index/snapshots
   before ingestion. Do not substitute a newly generated snapshot for a failed job.
5. Run the following commands **only after the corresponding approvals** from
   the checkout root containing `backend/`. `IDS` contains only this reviewed batch.

```sh
IDS="eurostat_e4b0591cf148660f3349 eurostat_eca8a799de8d6687fe33 eurostat_6e1c74c102959c0ded7b eurostat_fcab9c3216a8c2d01fc9 eurostat_3e9b736c08d1e26f46f5 eurostat_c94d6677ff350bbc29aa ons_27271ab0b950200f5401 ons_a007e11b21ed0f67ccf1 ons_24df6f5df34ca52bac40 ons_f069edbcf1bc4e7ff9c5 eia_4922b423fe8b2b32866f eia_4f9f06aabda8ff167d48 eia_feda97c6fccc3ab58f53"
python -m scripts.collect_expansion --workspace /tmp/macrolens-first-live --providers eurostat,ons,eia --only-ids $IDS
# Skip the collector when using the already verified frozen input archive.
# STOP if any capture failed, or if the reviewed vintage/definitions differ.
python -m backend.app.catalog.release_cli --database /var/data/macrolens-v2.sqlite3 --operation migrate
python -m backend.app.catalog.release_cli --database /var/data/macrolens-v2.sqlite3 --operation ingest --source-index /tmp/macrolens-first-live/source-results.json --ids $IDS
python -m scripts.smoke_first_release --origin https://macrolens-v2-backend.onrender.com --approved-live-read-checks
```

6. Verify all thirteen complete/quality-passed, correct counts/source hashes and
   original research/WB preservation. New registrations must still be private and
   AI/Discovery-denied. Rerun only the **same immutable source index** after a
   reported failure/backoff. Do not replace an incomplete generation with a new
   snapshot. All thirteen remain hidden until separate display approval.
7. After explicit approval to publish **only these thirteen**:

```sh
python -m backend.app.catalog.release_cli --database /var/data/macrolens-v2.sqlite3 --operation activate --approve-display --ids $IDS
python -m scripts.smoke_first_release --origin https://macrolens-v2-backend.onrender.com --approved-live-read-checks --activated
python -m scripts.smoke_first_release --origin https://www.macrolensresearch.com --approved-live-read-checks --activated
```

These query-only smoke checks verify all 30 legacy metadata IDs, the exact public
set of 43, all thirteen bounded histories/attributions, two comparisons and twelve
private denial cases. They make no AI requests or research writes. Existing live
CPI/gold charts and Discovery should also be opened after approved deployment;
normal legacy read-through cache refreshes remain the existing behaviour.

For automated UI checks from a disposable local/CI browser with Playwright installed:

```sh
EXPANSION_BROWSER_ORIGIN=https://www.macrolensresearch.com \
EXPANSION_BROWSER_LIVE_APPROVED=1 EXPANSION_BROWSER_EXPECTED_PUBLIC=43 \
EXPANSION_BROWSER_DATASET=eia_4922b423fe8b2b32866f \
EXPANSION_BROWSER_NAME='US commercial crude stocks excluding SPR' \
EXPANSION_BROWSER_ARTIFACTS=/tmp/first-release-browser \
python -m scripts.test_expansion_browser
```

The browser uses a new isolated context and synthetic saved-research/favourite
records. It never overwrites the user's Chrome profile or server research, and
checks unavailable old IDs, desktop/mobile Explorer and Investigate rendering.

## Rollback and stop conditions

Stop on missing backup/headroom/permissions, failed CI, capture/definition mismatch,
unhealthy readiness, source-proof failure, unexpected public IDs, WB exposure,
AI/Discovery enablement, OOM/restarts or persistent user-facing errors.

After separate rollback approval, revoke the exact batch using the same `IDS`:

```sh
python -m backend.app.catalog.release_cli --database /var/data/macrolens-v2.sqlite3 --operation revoke --ids $IDS
```

All observations, revisions, research and provenance remain. Roll back frontend,
then backend **code** to the recorded pre-release successful deploys via
**Deploys → Rollback → Rollback to this deploy**, or deploy the recorded previous
SHAs if the build artifacts expired. Never restore a disk snapshot, overwrite the
SQLite file, delete additive tables or enable AI/scheduling as routine rollback.

Official operational references: [deploys](https://render.com/docs/deploys),
[rollback](https://render.com/docs/rollbacks), [persistent disks](https://render.com/docs/disks).
