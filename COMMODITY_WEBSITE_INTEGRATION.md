# Commodity website integration — local implementation

30 October 2026 · feature/macrolens-v2 · based on 4816ef8.
No production access, rights update, ingestion activation, AI call, deployment or merge was performed. The reviewed integration is prepared for a feature-branch commit and Linux CI; publishing the development branch is not a production deployment.

## Architecture and plan reported before editing

The existing ingestion writer owns five additive ingest_* tables. Its CLI, provider adapter, durable jobs/cursors, leases and captured revisions remain unchanged. Existing website research is served through ScheduledDataService and a fixed 30-entry SPECS registry; Dataset Explorer and Investigate consume GET /api/v2/datasets and POST /api/v2/compare. Discovery and AI use the legacy registry independently.

The implementation adds a read-only stored-dataset reader and composes it with the existing service. Publication requires BOTH a reviewed code registration and an approved database permission row. Production presentation registrations are empty. No real pilot is added to SPECS, the UI, Discovery or AI.

## Implemented behavior

- backend/app/v2/stored_datasets.py: PublicStoredDefinition, StoredDatasetReader and PermissionedDataService. Reviewed definitions specify native monthly units, benchmark, attribution, license and source URL. Unknown/unregistered/private/invalid IDs all fail with the same generic unknown-ID response.
- The reader uses SQLite mode=ro, query_only and a short snapshot transaction; it never invokes Store initialization or migrations. It closes connections and does not cache observations or permissions. Database flags are checked on every stored read. Missing databases are not created.
- It rejects incomplete backfills, missing reference-month rows, unit_review observations, invalid values, changed units/provider/source, inconsistent source hashes and malformed metadata. Explicit source nulls remain null. Provider failures/old references are labelled stale. No fallback provider or filling is introduced.
- Reads are capped at 1,200 monthly periods per series and 32 reviewed presentation definitions; catalogue previews contain at most 40 observations each. No archived research evidence is read.
- backend/app/v2/main.py composes the reader with the unchanged scheduled legacy service and resolves approved stored definitions in the existing comparison pipeline. Existing transformations, alignment, statistics and lead/lag calculations are reused.
- Optional stored_provenance distinguishes native units, benchmark, attribution, license, actual stored coverage and reference-month labels from publication dates. Metadata is explicitly allowlisted; arbitrary ingestion JSON/internal notes are not serialized.
- Website history retains the existing 1990 floor. Native pre-1990 storage is reported separately, not silently treated as chart coverage. Saved-research contracts are unchanged.
- DatasetMetadata displays provenance in the existing expandable source panel; Explorer and Investigate already consume catalogue datasets dynamically. No layout redesign or private-series placeholder was added.
- backend/app/v2/ai_guard.py rejects findings containing any nonlegacy dataset ID before cache or model handling. Public research approval never grants AI permission. All stored datasets remain AI-excluded, including future public-approved fixtures.

## Private production invariants

The three World Bank pilots retain public_display=0, ai_allowed=0 and rights_state=unreviewed. The production schema still has CHECK(public_display=0) and CHECK(ai_allowed=0); no migration or approval mechanism is added. Ingested observations and research records are not updated by this integration.

Synthetic tests simulate a future approved schema ONLY inside disposable test databases, using fixture_copper and an example.invalid source. Other tests use the unchanged production schema to prove private pilots remain denied. There is no environment flag, public endpoint or UI switch to activate these fixture registrations.

## Validation

- Full local Python suite: **627 passed, 5 live-provider checks skipped**.
- New integration/security suite: **24 passed**, including API catalogue/Investigate calculations, permission revocation after a previous read, private-pilot denial, read-only logical database preservation, malformed metadata, partial backfill and unit rejection, nulls, freshness and AI-send exclusion.
- Frontend: **48 tests passed**, ESLint passed, TypeScript type-check passed.
- Python fatal lint passed; full Ruff rules passed for new reader/tests.
- Local Windows production build: unavailable because Windows returned EPERM when Next.js created generated API directories, including a separate short-path source copy. An encoding defect found in an intermediate build was corrected; final source passes type-check and tests. EPERM is not evidence of a code defect. The existing Linux frontend_v2 Actions job must pass on the release commit.
- The existing venv's Pandas DLL was blocked by Windows Application Control. Backend tests succeeded with the bundled Python/Pandas 3.0.1 runtime and existing remaining test dependencies. No security setting or package policy was changed.
- Default empty registrations add no stored-series queries; future approved registrations remain bounded. The existing Phase 4C Linux workflow is available to rerun 512 MiB, no-swap, half-core validation on the release commit; its recorded result is authoritative, not the earlier Windows measurement.

All test state is disposable under C:/Users/algba/Documents/Codex/wb-tests-1029. Source copies/build artifacts are outside the Git checkout. No production SQLite file or backup was opened.

## Remaining blockers

1. **Rights:** source-specific redistribution/commercial and AI-use review remains unresolved. A future rights grant must be separately approved; this code grants none.
2. **Units/benchmark:** iron ore's source-header USD/dmtu versus descriptive dry-ton spot units and historical benchmark transitions remain unresolved. unit_review data cannot pass the public reader. Monthly commodity benchmarks must not be labelled as live spot quotes or continuous futures.
3. **Publication migration:** the current database CHECK constraints intentionally prevent any public flag from becoming 1. A reviewed migration, permission decision and explicit presentation definition are all prerequisites to future real-series publication. They are outside this change.
4. **Native history:** exposing pre-1990 observations requires a separate API/UI date-contract review; the existing boundary is preserved.
5. **Release validation:** obtain a successful Linux frontend production build, test the actual release dependency set and repeat the relevant 512 MiB resource/smoke checks before deployment. No deployment or merge is authorized by this report.

## Files

New:
- backend/app/v2/stored_datasets.py
- backend/tests/test_stored_datasets.py
- frontend-v2/tests/stored-datasets.test.mjs
- COMMODITY_WEBSITE_INTEGRATION.md

Modified:
- backend/app/v2/main.py
- backend/app/v2/ai_guard.py
- frontend-v2/lib/contracts.ts
- frontend-v2/lib/presentation.ts
- frontend-v2/components/data-widgets.tsx

The pre-existing untracked Phase 4C/4D reports were left untouched. Only the nine integration source/test/report files belong in the release commit. Rollback of this implementation is code-only; it introduces no database changes requiring reversal.

## Release checklist — execution requires separate approval

1. Check successful Research validation (including frontend_v2 standard Linux Next.js build, lint, types and tests) and Phase 4C Linux resource jobs for the exact feature-branch release SHA. Review both tracked and newly added files; omit the unrelated historical untracked Phase 4C/4D reports.
2. Obtain explicit deployment approval. Record each currently deployed backend/frontend revision; the latest operator-provided backend revision is bd0a01cc15ad11a398ac46c6080f1b6c53313e5a, not independently rechecked here.
3. Confirm a recent independent backup and restore verification, persistent /var/data path, disk headroom and existing disabled ingestion/AI settings. Make no permission, environment or hosting changes.
4. Manually deploy the approved release SHA through the existing V2 backend and frontend services/build settings. Do not merge, use the legacy render.yaml blueprint or run an ingestion/migration command. This integration has no schema migration.
5. Verify /health and /ready, scheduler health, exactly the existing 30 public datasets, Explorer, comparisons and saved research. All three wb_* IDs must remain absent from public catalogue/frontend and rejected by comparison. Confirm unchanged public_display=0, ai_allowed=0 and rights_state=unreviewed using approved read-only operator checks; do not change those values.
6. Monitor memory, errors and busy responses. On a regression, roll back each affected service to its recorded previous code revision. Preserve the database and commodity/research history; do not restore over newer research as a routine code rollback.

