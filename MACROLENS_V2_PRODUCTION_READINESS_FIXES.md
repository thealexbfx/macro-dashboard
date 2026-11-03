# MacroLens V2 production-readiness fixes

Implemented on `feature/macrolens-v2`, based on the production-readiness audit. The initial implementation was validated locally. The user subsequently approved committing and pushing these 24 files for GitHub Actions validation and confirmed that Render auto-deploy is disabled for both V2 services. No merge, deployment, Render/DNS/environment change, production request, database reset, or paid AI call was made. Optional AI remains disabled by default and was explicitly disabled in the isolated test backend.

## Changes and behavior

1. **Credential protection:** the shared Next.js proxy forwards request credentials upstream only. Responses allowlist `Content-Type` and `Retry-After`, then set `Cache-Control: no-store` and `X-Content-Type-Options: nosniff`. Authorization, cookies, and unrelated upstream headers are excluded. All V2 backend API responses also receive no-store/nosniff headers. Synthetic-token tests cover successful, forbidden, unavailable, and transport-error responses.
2. **Supervised scheduler:** an unexpected refresh exception records its type and retries on the next 60-second tick. Exception text is excluded from diagnostics/logging at the supervisor boundary. Heartbeat, last attempt/success/failure, consecutive failures, in-progress state, and busy skips are observable. A successful scheduler attempt means the local operation completed; it does not mean all providers are current.
3. **Readiness:** `GET /ready` checks SQLite schema, JSON functions, and a writable transaction, plus scheduler thread/heartbeat health. It makes no provider requests. It returns 503 for a dead/stale scheduler, three consecutive engine exceptions, or database failure; later successful execution recovers readiness. `/health` remains liveness. Admin-authenticated `/api/v2/discovery/admin/diagnostics` adds source-check timing/failures and local limits. Normal provider failures remain explicitly represented by source freshness/status, rather than making readiness depend on an external service.
4. **Bounded Discovery reads:** the ordinary report retains its existing research fields and includes at most five promoted findings, ten following findings, and six curated historical records. `archived` is now empty; `archived_total`, `following_total`, `historical_total`, and page limits describe available history. Full archived evidence is loaded only when requested. IDs, versions, stored evidence snapshots, and saved-research formats are preserved.
5. **Historical retrieval:** `GET /api/v2/discovery/stories?state=archived|following&kind=all|unusual|correlation|divergence&limit=20&offset=0` returns summaries and total/next-offset metadata. `GET /api/v2/discovery/stories/{id}` returns one full preserved story. `GET /api/v2/discovery/historical?limit=6&offset=0` pages curated historical comparisons. Archive UI opens summaries on demand, then existing evidence cards on request. Following and historical sections retain their investigation/save actions.
6. **Unchanged-data work:** a maximum 30-second local report cache is bounded by the next scheduled source check and UTC date rollover. SQLite revision metadata invalidates analysis after another worker updates sources. Numerical scans reuse the persisted fingerprint; enrichment is reused when data and active research revisions are unchanged. Archive-only additions do not trigger suggestion calculations. Cold starts rebuild the in-memory cache from preserved SQLite state.
7. **Workload limits:** one expensive research operation per process, eight in-flight V2 API requests per process, 64 KiB request bodies, and a ten-second body-receive deadline. Excess work returns 429/503 with `Retry-After: 2` instead of growing an analytical queue. Read requests and pure comparisons retry a rejected operation at most twice; refresh and admin actions do not retry. Cancellation stops retries. Readiness/liveness bypass the API admission limit. Existing cross-process SQLite leases remain in place.
8. **Research correctness:** cached values returned while another process holds a source lease now undergo freshness assessment. Historical similarity rejects intersecting source evidence windows, including transformation lookback. Daily anchors follow actual declared sessions; weekly anchors preserve actual reference labels. Existing historical snapshots are not rewritten.
9. **CI:** the existing Python and legacy frontend jobs are preserved. A separate Node 22 `frontend_v2` job installs the lockfile, runs lint, a standard production build, type-check, and unit tests. Provider integration checks remain explicit local/opt-in checks rather than adding unreliable network calls to CI.

## Validation

- Full backend suite: **189 passed** (23 new readiness/security/performance/correctness cases).
- Full V2 frontend unit suite: **46 passed** (10 new proxy-security/retry cases).
- V2 frontend integration suite: **25 passed**, run serially against an isolated backend with a copy of cached real observations. This validates source reconciliation, all eight timeframes, custom dates, historical memory, transformations, and recession context. It is not a fresh production-provider availability check.
- Frontend lint and strict type-check: passed.
- Backend Ruff checks, repository CI fatal-error Ruff check, and Git whitespace validation: passed.
- Production build: standard Next.js/Webpack build passed before the final retry-helper addition. Subsequent Windows Webpack builds failed creating generated `types/app/api/v2` with `EPERM`. The final code passes a complete optimized **Turbopack production build** (`npm run build:preview`), including static generation and build-time lint/types. No source/configuration workaround was introduced. Standard Webpack remains the Linux CI command and must be confirmed there before release.
- Full repository Python suite: **517 passed, 5 skipped, 1 failed**. The legacy Streamlit `test_full_today_gold_queue_save_and_restore` fails with missing button key `discovery_ccff76f0eb89b012554db809`; the same isolated test fails on untouched starting commit `006d7ac6e396de1e7dd07535d47a59b715b8ace6`. Legacy application/test files were not changed.
- Actual local HTTP smoke checks: `/health` and `/ready` return 200; readiness reports a live scheduler and writable database. Archive pages contain 20/20/10 summaries for 50 records; single-story retrieval retains evidence. Unauthorized admin response is 403, no-store, and contains no synthetic token in headers.
- The backend smoke process uses `outputs/readiness-preview.sqlite3`, a separate SQLite backup of the benchmark fixture. Existing application state was not used for writes. Its copied source observations are real; its 50 archive rows are synthetic test records.
- A new frontend browser smoke session was not started: automatic approval review rejected launching the local production frontend process with `approval required by policy` while sandbox approval is disabled. Backend HTTP integration, proxy regressions, frontend unit tests, and production-build validation completed. No browser-interaction or Render load-test claim is made for this change.

## Matched Discovery benchmark

Same frozen source observations, same SQLite fixture, 50 synthetic archived records, three calls per implementation. Elapsed time includes obtaining the report and standard JSON serialization; bytes are uncompressed serialized JSON, not compressed network transfer. Timing is local Windows, not a Render measurement.

| Measurement | Before | After |
| --- | ---: | ---: |
| Serialized report bytes | 2,348,582 | 241,382 |
| First request | 1.455176 s | 0.390660 s |
| Warm request 2 | 1.403884 s | 0.007089 s |
| Warm request 3 | 1.400659 s | 0.006941 s |
| Full archives in ordinary response | 50 | 0 |
| Stored identities/versions/evidence retained | Yes | Yes |

Payload reduction: **89.7%**. The regression fixture asserts bounded response growth and no archived suggestion calculation/unchanged rescan, rather than relying on a flaky wall-clock threshold. Pagination tests retrieve all 50 unique IDs and verify that opening evidence leaves stored snapshots and versions unchanged.

Reproduction tool: `python -m backend.tools.readiness_benchmark --database <new-fixture.sqlite3> --source-db <read-only-existing-cache.sqlite3> --output <result.json> --label after`. It refuses to overwrite the destination when preparing a fixture and forbids provider requests. Omit `--source-db` to measure an already prepared benchmark fixture. Never point the benchmark destination at an application database.

## Deployment considerations — approval required

- **No destructive migration or history reset.** SQLite adds only `CREATE INDEX IF NOT EXISTS story_status_order ON stories(status,last_meaningful DESC,id)` during normal initialization. Existing tables, rows, discovery IDs, evidence versions, and saved research stay in place. Index creation may briefly take a write lock on a large history.
- Before an approved release, take a consistent backup of the existing SQLite database including committed WAL contents using SQLite backup facilities. Keep the current persistent `/var/data` path and mounted disk. Do not copy this synthetic benchmark/preview database into production.
- SQLite JSON functions are now used for summary retrieval and are verified by `/ready`. Local SQLite 3.53.1 passed. Confirm the deployed runtime supports them; do not reset a database to remedy a readiness failure.
- Release compatible backend/frontend revisions together, with the backend routes available before the updated frontend. Older clients expect bulk `archived`; the new frontend uses the on-demand endpoints. Existing investigate/save data contracts are unchanged.
- No new environment variables, paid services, worker processes, cron, Valkey, Streamlit dependency, or hosting resources are required. Do not enable AI. No production configuration was changed.
- Per-process limits are not a cross-instance memory guarantee. Actual 512 MB Render RSS/CPU behavior, concurrent-user load, restart durability, mounted-disk configuration, and the Linux CI build still need release verification. This work does not claim those were exercised in production.
- Release preparation is authorized: commit and push only `feature/macrolens-v2`, then verify the new Linux `frontend_v2` job. Render auto-deploy is disabled per the user. No manual deployment or merge is authorized. The commit and GitHub Actions records provide the final SHA/check status. Stop for approval before production deployment.

## Exact repository file manifest

Generated from Git status after implementation; includes this document. Local benchmark databases and output evidence are outside the repository and are not application files.

| File | Status |
| --- | --- |
| `.github/workflows/research-validation.yml` | Modified |
| `MACROLENS_V2_PRODUCTION_READINESS_FIXES.md` | Added |
| `backend/app/v2/history.py` | Modified |
| `backend/app/v2/main.py` | Modified |
| `backend/app/v2/memory.py` | Modified |
| `backend/app/v2/refresh.py` | Modified |
| `backend/app/v2/request_bounds.py` | Added |
| `backend/app/v2/runtime.py` | Modified |
| `backend/app/v2/scheduler.py` | Added |
| `backend/app/v2/state.py` | Modified |
| `backend/app/v2/workload.py` | Added |
| `backend/tests/test_v32_readiness.py` | Added |
| `backend/tools/readiness_benchmark.py` | Added |
| `frontend-v2/app/api/v2/discovery/admin/diagnostics/route.ts` | Added |
| `frontend-v2/app/api/v2/discovery/historical/route.ts` | Added |
| `frontend-v2/app/api/v2/discovery/stories/[id]/route.ts` | Added |
| `frontend-v2/app/api/v2/discovery/stories/route.ts` | Added |
| `frontend-v2/components/discovery-pages.tsx` | Added |
| `frontend-v2/components/discovery-radar.tsx` | Modified |
| `frontend-v2/lib/contracts.ts` | Modified |
| `frontend-v2/lib/discovery.ts` | Modified |
| `frontend-v2/lib/server-api.ts` | Modified |
| `frontend-v2/tests/proxy-security.test.mjs` | Added |
| `frontend-v2/tests/request-bounds.test.mjs` | Added |
