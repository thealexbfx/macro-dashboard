# Phase 4B — staging-readiness report

28 October 2026 · `feature/macrolens-v2` · No production access, deployment, merge, hosting changes, AI enablement, new datasets or providers.

**Recommendation: conditional go for a controlled release with ingestion disabled. Do not treat ingestion-on operation as certified for Render's Linux memory/CPU limits.** First pass normal Linux CI, make a consistent SQLite backup, verify disk headroom and obtain release approval. Keep `MACROLENS_INGESTION_ENABLED` unset/disabled and all pilot public/AI permissions denied.

## What was exercised

A real single-process Uvicorn/FastAPI server ran on loopback with the existing Discovery engine/supervisor and ingestion worker enabled, using a newly created disposable SQLite database. A second run verified the disabled release default. Neither used the configured application database or contacted production.

The 30 existing public definitions were unchanged; **98,399 synthetic historical observations** exercised their existing API/calculation paths. The pilot used the actual Phase 4A World Bank workbook snapshot (SHA256 `ea1c350827878ea3bbe30e3cda16a13fd3bd5b409b8458940dc94a36b5a33154`), replayed through the existing adapter's streaming transport. No external provider or AI traffic was permitted. This validates parsing and application integration, not current provider availability, DNS/TLS or real network latency.

Backfill/retry scheduling was accelerated to one-second ticks and due times advanced only in the disposable database. Crash recovery explicitly simulated lease expiry after proving an unexpired lease blocked the replacement worker. **One actual 60-second scheduler cycle was also measured.** This is not a multi-day soak test.

## Measured resources

Windows, Python 3.12.14, SQLite 3.53.1. Sampling occurred inside the actual ASGI interpreter at approximately 0.2-second intervals. MiB means 1,048,576 bytes.

| Phase | Maximum sampled working set | Maximum private commit | Process CPU / measured wall time |
|---|---:|---:|---:|
| Ingestion disabled: entire control | 246.3 MiB | 483.0 MiB | Mixed startup/burst/accelerated-idle phases |
| Enabled: cold Discovery + backfill | 238.7 MiB | 477.6 MiB | 20.27 s / 27.77 s |
| Enabled: normal/revision updates | 262.2 MiB | 499.8 MiB | 3.08 s / 7.25 s |
| Enabled: concurrent API burst | 245.3 MiB | 481.9 MiB | 3.41 s / 3.20 s |
| Enabled: default 60-second idle/check cycle | 238.3 MiB | 474.8 MiB | 2.08 s / 64.02 s |

OS high-water counters captured **265.1 MiB peak working set enabled**, versus **248.5 MiB disabled**. CPU totals can exceed one core's wall time because they include all process threads. They cannot predict performance under Render's CPU quota. Windows private committed memory is not Linux RSS or cgroup usage; **499.8 MiB is a caution signal, not proof of either fitting or exceeding a 512 MB Linux limit**.

SQLite main/WAL/SHM peaked at **23.28 MiB enabled**, finishing at **16.33 MiB**, versus **15.86 MiB** for the control's final database. These include the synthetic public cache and Discovery state. A separate old-schema compatibility fixture required **52 KiB** for the additive schema; original records and a consistent backup remained intact. No raw workbook is retained by the production ingestion path. The existing 256 MiB ingestion admission guard and 64 MiB free-space minimum remain; unrelated research growth still needs monitoring on the 1 GB disk.

## Workflows, failures and boundaries

- All **2,403 pilot observations** backfilled; unchanged checks inserted/revised zero rows. A synthetic copper revision and restoration produced retained revisions.
- Six concurrent clients issued 36 mixed requests: Discovery refresh/read, catalogue, comparisons, history and readiness. Successful warm-phase requests had nearest-rank p95 **1.016 s**, maximum **1.438 s**. Fifteen warm-phase requests received the existing deliberate **503 busy** response; three further 503s came from injected Discovery failure/recovery. There were **no unhandled HTTP 500s**. This is an admission-control test, not a production throughput guarantee.
- Provider timeout, malformed workbook and unexpected exception retained last-good observations/last-success and respected durable backoff. The supervisor recovered from unexpected Discovery failures; ingestion continued independently.
- Graceful shutdown during a three-second stalled replay completed in **3.297 s**; idle shutdown took **0.968 s**. Abrupt termination/restart preserved SQLite integrity, backfill cursor and committed records, and recovered an abandoned job after simulated lease expiry. An immutable historical research snapshot and note survived both restarts.
- All 30 public definitions were compared field-by-field. All three pilot IDs were rejected by public comparison requests (422), absent from public catalogue/Discovery, and retained denied database permissions. Optional AI returned its disabled fallback and created no request-ledger entries. Saved-investigation reopening also passed the existing frontend/legacy workflow tests.
- Disabled control created **no ingestion definitions, runs or observations**. Five empty additive tables are the only database schema addition when the worker is off.

## Focused fixes and tests

1. Dispatch ingestion before a potentially slow Discovery scan; optional dispatch failure cannot prevent Discovery.
2. Add cooperative cancellation before/after provider streaming and before commit. Restart creates a fresh cancellation token; an already-running atomic commit may finish.
3. Bound ingestion SQLite waits to two seconds; keep existing callers' default timeout unchanged. Contention does not monopolize the optional worker.
4. Tolerate SQLite sidecars disappearing during capacity measurement, rather than falsely recording an ingestion failure.
5. Fix an existing legacy workflow test's UTC/local-date mismatch by freezing its test clock; no legacy application/UI behavior changed.

**561 Python tests passed; 5 opt-in live tests skipped.** Nine new Phase 4B regression tests cover lifecycle, contention, dispatch isolation, pilot/AI exclusion, additive upgrades/backup and WAL races. **46 frontend tests passed.** Repository fatal-error lint, full lint for the new ingestion/staging files, formatting and Python compilation passed.

## Remaining requirements and release safeguards

- **Unverified:** this machine has no usable Docker/WSL environment. Linux cgroup RSS plus page-cache/native-library accounting, OOM behavior, CPU throttling, actual deployed worker count/runtime, real persistent-disk latency/free space and a prolonged soak remain untested. The measured burst limit already refuses concurrent analysis; do not raise it or expand the catalog on these results.
- Before enabling ingestion, run this same harness under a 512 MB Linux limit with the deployed CPU/runtime configuration and controlled network-stall/SIGTERM tests. Cancellation checks occur between reads; a real blocked socket can still wait for its read timeout. Actual Render shutdown grace was not exercised.
- Public redistribution/AI permissions and the iron-ore unit-description conflict remain unresolved; all three pilots stay hidden and AI-denied. These are not bypassed by worker opt-in.
- For the disabled release: preserve the current one-worker service/disk configuration, take/verify a SQLite backup, check mounted-path/headroom, release only after approval, then smoke-test readiness, the 30 datasets, Discovery and saved research. Roll back code if needed; **leave additive ingestion tables and all history in place**, with ingestion disabled. Do not replace/reset the live database.

## Review and reproduction

Phase 4B changes: `backend/app/ingestion/runner.py`, `world_bank.py`, `backend/app/v2/main.py`, `state.py`, `backend/tests/test_phase4b_staging.py`, the clock fixture in `tests/test_discovery_integration.py`, `scripts/validate_phase4b.py` and this report. No dependencies or Render configuration changed.

From the repository root, with existing backend dependencies and the previously verified snapshot:

```text
python scripts/validate_phase4b.py --output ../phase4b-staging/new-enabled-run --workbook ../wb-pilot-inspect.xlsx
python scripts/validate_phase4b.py --output ../phase4b-staging/new-disabled-run --workbook ../wb-pilot-inspect.xlsx --disabled
```

The harness requires a new directory under `work/phase4b-staging`, uses loopback only, blocks external HTTP/AI, and stops its own test servers. Evidence: [enabled run](../phase4b-staging/release-candidate/results.json), [disabled control](../phase4b-staging/disabled-final-02/results.json), [compact measurements](../phase4b-staging/readiness-summary.json), [schema compatibility](../phase4b-staging/compatibility-results.json). Artifacts are local, outside application state and Git. No production release was performed.

