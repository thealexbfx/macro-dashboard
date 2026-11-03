# Read-only Data Quality and Research Readiness Audit

Milestone 1 only. No ingestion, migrations, grants, worker initialization, AI calls,
application changes, merges or deployments. No production audit was run during
implementation. Local evidence below is synthetic and must not be described as
194 production datasets passing.

## Run against the existing Render deployment without deploying this PR

Review `backend/app/catalog/readiness.py` at immutable commit
`871f10c35660ae351325a0c6689aa4e0852f2360` first. The script imports only existing
libraries from the specified deployed release. It does not import the FastAPI app
or instantiate Store, providers, workers or ingestion services. Importing the
existing catalog modules defines their classes but does not run their writers.

In the **backend Render Shell**, paste this exact block. It verifies the deployed
revision, downloads only the audit program into a new `/tmp` directory, verifies
its SHA-256, and reads the persistent SQLite database using the deployed Python
environment. It does not check out a branch, install packages or restart anything.

```bash
set -eu
cd /opt/render/project/src
test "$(git rev-parse HEAD)" = 'cb7a03cded7113231fe1bac42beadff0e92a274a'
AUDIT_WORK="$(mktemp -d /tmp/macrolens-readiness.XXXXXX)"
printf 'Audit working directory: %s\n' "$AUDIT_WORK"
curl --fail --silent --show-error --location --max-time 60 \
  'https://raw.githubusercontent.com/thealexbfx/macro-dashboard/871f10c35660ae351325a0c6689aa4e0852f2360/backend/app/catalog/readiness.py' \
  --output "$AUDIT_WORK/readiness.py"
printf '%s  %s\n' \
  'b66a0749a3741a26e3b9ece2e8c7f2bd88980c2deef182248ba3eea36fca04e8' \
  "$AUDIT_WORK/readiness.py" | sha256sum --check -
PYTHONPATH="$PWD" PYTHONDONTWRITEBYTECODE=1 python -B "$AUDIT_WORK/readiness.py" \
  --database /var/data/macrolens-v2.sqlite3 \
  --output "$AUDIT_WORK/reports" \
  --expected-public 194 \
  --evidence-origin production \
  --max-seconds 90
printf 'Review/download reports from: %s/reports\n' "$AUDIT_WORK"
```

If the deployed revision or checksum differs, **stop**. Do not change the expected
hash or deployment to make the command pass. Reconcile the new deployed revision
and audit-library compatibility first. The checksum is for the exact UTF-8 script
bytes in the pinned commit, not for a branch name.

The only network request in the block downloads the reviewed audit program. The
audit itself makes no network requests and never checks a data provider. If GitHub
is unavailable from Render, transfer those same checksum-verified script bytes to
the new `/tmp` directory using the existing approved transport; do not deploy the
application as a workaround. No credentials are needed by the audit.

Generated files:

- `summary.md`: counts, severity-ranked fixes, affected IDs, dataset table and limits.
- `datasets.csv`: one row per public ID; flattened history, metadata, research-use,
  refresh and freshness fields, plus reason codes. UTF-8 BOM and formula protection.
- `audit.json`: complete structured report with evidence origin, production library
  revision, audit-script checksum, schema versions, scope reconciliation and methods.

`/tmp` is temporary. Download the three files through the existing Render/SSH
transport before restarting the service. No database download is required. No
automated upload, report publication or cleanup is included. Reports contain public
metadata and diagnostic summaries, not raw observation arrays or private records.

Exit codes: **0** = reports written and actual public count matches expected;
**2** = reports written but public scope differs; **1** = audit stopped, no complete
audit certified. Exit 0 is **not** a claim that datasets passed quality checks.
Read the classifications and findings. Keep scope-mismatch reports for investigation;
never lower `--expected-public` to conceal a missing public dataset.

## Resource and SQLite safety

Run once during a low-traffic period, after checking existing protected Data Health
for memory/disk pressure. Do not run concurrently with a release, staging operation
or another audit. This tool does not pause or reconfigure the refresh worker.

- Uses `mode=ro`, `PRAGMA query_only=ON`, and a SELECT/READ/FUNCTION/TRANSACTION-only
  SQLite authorizer. No schema migration, checkpoint, VACUUM, grant change or DB copy.
- A single SQLite read transaction gives a consistent logical snapshot across the
  public enumeration, metadata, histories and refresh evidence. Existing writers
  can continue in WAL mode. Normal SQLite read locks/shared-memory bookkeeping still
  apply; no observation/database contents are written by the audit.
- Sequential datasets, at most 100,000 points per dataset, 16 MiB per legacy payload,
  at most 1,000 public IDs, two-second SQLite lock timeout and a 90-second default
  wall-time/SQL progress deadline (maximum permitted 120 seconds). No parallel workers.
- Budget-exceeding or malformed dataset histories become explicit Needs attention
  rows; query/deadline/schema failures stop the audit rather than certify a partial
  report. A long read snapshot can delay WAL reclamation. Stop with Ctrl-C if service
  health deteriorates; the read transaction closes without rollback work or repair.
- Reports require a **new** directory outside the database directory. Existing
  output directories are never overwritten. There is no `immutable=1` on the live
  DB: that would ignore active WAL semantics and can produce incorrect reads.
- Do not copy only the live `.sqlite3` file while WAL is active. An already verified
  consistent standalone backup may instead be audited with `--evidence-origin
  production-backup`, clearly dated to that backup. Creating a new production
  backup is outside this tool and retains its existing separate approval process.

No Render memory/latency certification is claimed from the Windows tests. Resource
usage is bounded but should be observed on the actual service. If 90 seconds is
insufficient, retain the stop result and review resources or use an existing verified
backup before increasing the bound. Do not silently remove safety limits.

## What is measured, and what is not

### Public scope and reuse

The canonical `catalog.operations.registry()` supplies IDs/metadata/refresh rules.
The original 30 remain public through the existing legacy policy. Native public
flags and `catalog_release_grants` are independently enumerated before validation,
so a broken granted dataset does not disappear just because the chart reader rejects
it. Private/ungranted rows are not included. Every enumerated ID gets one report row.
The default expected count is 194, not a hard-coded limit of 30 or 194.

The existing `NativeReader._permission()` validates native definition-bound rights,
active generation and completeness in the **same** read snapshot. Failed/unknown
public boundaries remain Needs attention; their observations are not accessed.
This is not a cryptographic rehash of every source payload or an independent check
against the provider. Existing ingestion receipts remain the source-evidence layer.

The audit reuses legacy `validate_frame()`, `assess_freshness()`, `session_frame()`,
native `native_period()`, publication metadata/transformation rules, Data Health lag
thresholds and the existing 2026-10-30 suitability matrix. The latter is explicitly
dated documentary evidence for 30 series, not fresh production numerical validation.
No new parallel registry, permission model, scheduler or dashboard is introduced.

### Separate dimensions

- **Historical quality:** actual stored rows, valid/null/invalid values, duplicate
  analytical periods, first/last stored and valid dates, coverage days, expected
  periods within those endpoints, absent periods, completeness and longest complete
  run. No inferred missing prehistory and no expectation of unreleased future rows.
- **Research suitability:** per-use eligibility and reasons, independent of whether
  refresh is configured. Uses reviewed definitions, units, adjustment, scaling,
  source-date conventions, existing source-use restrictions and native frequency.
- **Refresh configuration:** reviewed policy, configured interval and registered
  job/cache evidence. This never proves a live worker is enabled or healthy.
- **Actual source checks:** stored successful-check timestamp separately from
  attempts/completed checks, last observed change, next due, failures and error state.
  A recent successful check with no new release is still a successful check.
- **Inserts versus revisions:** inserts are not separately counted in current
  refresh telemetry, so the report says `not_separately_recorded`. Native revision
  rows and legacy revision counts are reported separately. Zero revisions is not
  proof that revisions were independently tested. Initial ingestion and automatic
  refresh verification are not treated as equivalent.

Raw provider errors and arbitrary stored provenance are not exported. Errors are
reported as safe review classifications; detailed troubleshooting remains in the
existing protected Data Health path. The audit cannot inspect another process's
worker state and reports `unknown_offline_audit`, rather than fabricating liveness
or marking all refresh disabled as the older standalone health CLI does.

### Calendars, suspicious values and readiness

Monthly/quarterly/annual gaps use calendar periods. Weekly rows retain native source
conventions. Legacy daily series use the existing US calendar approximation. Native
daily sources use a weekday envelope plus declared holidays and actual observed
dates, explicitly marked unverified; missing weekdays require review, not automatic
declaration of data loss. Unlisted closures and sparse early publication remain
limitations. Event/irregular series are not certified by regular-period methods.

Existing legacy definition validation catches invalid price-index/employment levels
and date conventions. A robust 12-scaled-MAD screen of adjacent changes flags large
jumps for inspection; genuine crises, policy moves and futures rolls must not be
deleted as outliers. Constant series are flagged without assuming corruption.

Initial descriptive minima are **consecutive nonmissing native periods**:

| Frequency | Comparisons | Anomaly screening | Historical relationships |
|---|---:|---:|---:|
| Daily | 30 | 756 | 1,260 |
| Weekly | 13 | 156 | 260 |
| Monthly | 12 | 60 | 120 |
| Quarterly | 8 | 32 | 40 |
| Annual | 5 | 15 | 20 |

These are conservative, inspectable screening policies, **not significance claims**,
universal economic-cycle requirements or guarantees of stationarity. A complete
recent segment may support research despite gaps elsewhere in the full history.
The report preserves full-history gaps separately. Eligible datasets are labelled
`eligible_with_limitations`; others include exact insufficient/unsupported reasons.
Each actual comparison still needs compatible definitions/units/transformations,
transformation warm-up, overlapping paired samples, effective-sample/stability checks
and control of exploratory/multiple-screening bias. No pairwise correlation mining.

Classifications:

- **Needs attention:** invalid/unreadable history, duplicates, missing observations
  entirely, or invalid publication/completeness evidence.
- **Usable with limitations:** gaps/outliers requiring review, missing metadata,
  source-check uncertainty/failure/lag, short use-specific history, approximate
  calendars or documented suitability restrictions.
- **Research ready:** the stored checks and all three descriptive sufficiency
  screens pass without recorded review findings. This is scoped readiness, not
  independent provider or historical-vintage certification.

Freshness distinguishes explicit future native releases, existing release-aware
legacy assessments and coarse lag-review thresholds. It does not invent publication
dates or label every old reference stale. Exact unknown release schedules remain
unknown and must be reconciled with producer evidence before a stale-data verdict.
No readiness status grants public, AI or Discovery access.

## Local use and validation

From a checkout with the existing backend dependencies:

```bash
python -m backend.app.catalog.readiness \
  --database /PATH/TO/EXISTING/CONSISTENT.sqlite3 \
  --output /NEW/REPORT/DIRECTORY \
  --evidence-origin local --expected-public 194 --max-seconds 90
python -m pytest backend/tests/test_readiness_audit.py backend/tests/test_catalog_operations.py -q
```

Implementation validation on Windows/Python 3.14:

- **488 backend tests passed**, including **24 new audit tests**. Existing warnings:
  Starlette/httpx deprecation and two NumPy degenerate-correlation warnings.
- Full 194-public release fixture audited within the existing staging/publication/
  rollback test: exactly 194 IDs, all present, source verification not fabricated,
  and logical database dump identical before/after audit. All data/approvals there
  are disposable **synthetic fixtures**, never production.
- Tests cover missing cache, corrupt public grants, private exclusion, invalid values,
  duplicates, gaps/nulls, native versus legacy checks, frequency-specific thresholds,
  weekends/closures, legitimate actual holiday values, constant/irregular series,
  denied write attempts, concurrent WAL snapshot consistency, deadline stops,
  malformed cache, report overwrite/path protection, CSV injection and exit code 2.
- Standalone `/tmp`-style script execution tested locally against a clearly labelled
  synthetic 30-public database, producing all three reports with a matching scope.
- Ruff checks and formatting pass for the audit and new tests; `git diff --check`
  passes. Windows temporary directories were redirected into the workspace after
  initial unrelated backup tests hit OS temporary-directory permission errors.

No frontend/API contract, catalog manifest, source adapter, refresh policy, grants,
database schema, production settings or application runtime entrypoint was changed.
Review the actual production reports before approving Research Journey work.
