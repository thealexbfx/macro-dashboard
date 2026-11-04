# Research Journey — Investigation Foundation

Product PR 1 extends the existing Next.js investigation and FastAPI comparison flow. No accounts, cloud sync, ingestion, refresh schedule, production data, AI activation or deployment changes.

## Review base

`feature/research-journey-foundation` starts at PR #16 head `b98246b920858285fa6bf7c82cc76914ec69d6f6` and targets `feature/targeted-readiness-corrections`. PR #16 in turn depends on PR #15. This keeps the product diff separate while retaining the stable application and targeted refresh corrections. Do not merge/deploy any predecessor automatically. After predecessors integrate sequentially, retarget/rebase this product PR onto `feature/macrolens-v2` and rerun validation before merging it.

## Contract and migration

`InvestigationV4` extends the existing investigation contract, rather than creating a parallel chart-save model:

- Stable `id`, `version: 4`, saved `revision`, `created_at`, `updated_at`, and `migrated_at`.
- `research_question`, `working_hypothesis`, `supporting_evidence`, `contradictory_evidence`, `alternative_explanations`, `limitations_and_uncertainty`, existing `note`, and user-written `conclusion`.
- Dataset IDs, periods, transformations, horizons, observation basis, alignment, effective rolling window, and existing workspace/chart settings.
- Existing original `discovery` and `historical_context` snapshots, plus `original_calculation` and `saved_calculation` compact receipts.

Evidence references contain an ID, dataset references, optional period/fingerprint, and note. They refer to evidence; they do not imply an automated judgement that a hypothesis is supported. This PR exposes question and existing notes; the remaining structured fields are persisted groundwork for Product PR 2.

Numeric v2/v3 records are validated, conservatively defaulted and migrated. Unknown/revoked dataset IDs remain references and still pass through existing backend access checks. Legacy creation/update timestamps remain null because they were never recorded; only migration time is recorded. New investigations receive actual client creation/update times. Unknown versions, malformed records and oversized data are retained and reported, never silently overwritten. Unversioned prototype notes stay in the original backup and are not represented as validated research.

## Browser-local persistence

The existing `ml-research` localStorage array becomes a retained, read-only migration backup. IndexedDB is the single active repository for saved investigations, drafts and the active ID; the application no longer appends new saves to localStorage. The repository boundary can later be implemented by authenticated storage without changing the research contract.

- A draft is acknowledged only after its IndexedDB transaction completes. Debounced writes, explicit navigation flushes, and active-ID restoration support reload recovery.
- Saving updates the same ID and increments its saved revision. Separate investigations have separate IDs. My Research shows drafts as well as saved records.
- Import is add-only/idempotent: an old backup never overwrites an edited canonical record. Unseen legacy IDs can still import on later visits.
- Draft and saved revisions are checked in one transaction. Stale same-ID writes from another tab fail visibly; independent IDs do not overwrite each other. Reload or export before resolving a conflict.
- Original Discovery/historical evidence and the first saved calculation are preserved across updates. Last-saved calculations change only on explicit save. Recalculating/reopening never rewrites the stored receipts or user conclusions.
- Storage failures keep the active draft in memory, expose retry/export, and never acknowledge a failed write. Navigation within the same object remains usable; starting another object requires persisting the active one. An unload prompt warns about unacknowledged edits.

These guarantees cover acknowledged browser commits, not permanent backup. Browser/device clearing, private browsing, browser eviction, a device failure, or switching origins can remove or isolate local records. No cloud sync or cross-device recovery is claimed. Export produces a local JSON backup; importing arbitrary exports is deferred. Multi-tab conflicts are detected, not automatically merged. An edit made after an acknowledgement still needs its own acknowledgement.

## Calculation receipts

The existing compare response gains optional additive `provenance` (schema 1, method `macrolens-comparison-1`). Both legacy and native/mixed paths retain the existing comparison conventions and access checks.

Receipts record request parameters and hash, UTC calculation time, dataset/source identifiers, definition hash (native) or registered metadata fingerprint (legacy), units/frequency, actual retrieval and successful-source-check times when recorded, validated native generation references (up to 16, with total count), input fingerprints/count/coverage, effective output ranges, compact relationship statistics, limitations and an output fingerprint. Creating the receipt performs no additional provider calls or database writes.

Legacy input hashes cover validated fetched data through the requested end, including historical lookback; native hashes cover the bounded fetched native inputs. That scope can include unused earlier history, so an input change does not necessarily mean the result changed. A compatibility adapter with no provenance is explicitly labelled as hashing visible observations only. Result hashes exclude retrieval/calculation timestamps, allowing changed numerical outputs to be distinguished from a successful unchanged source check. Fingerprints are audit identifiers, not cryptographic signatures proving external source authenticity.

No raw observation, rolling-correlation or scatter arrays are duplicated in receipts. Existing bounded Discovery preview snapshots remain original evidence. A saved receipt must match current calculation parameters; stale results cannot be silently saved under new settings. The UI separates original Discovery evidence, original calculation, last-saved calculation and fresh recalculation. Exact historical replay is explicitly unavailable: fingerprints/generation references do not create a frozen-vintage read API. Old records without receipts are disclosed as such.

## Deterministic rendering and validation

Server rendering and the first client rendering use the same fixed placeholder and deterministic seed. Date/UUID/storage initialization occurs after mount. This avoids separately evaluated server/client dates at UTC midnight.

Validation commands (repository root):

```sh
python -m pytest backend/tests -q
python -m ruff check --isolated --select E9,F63,F7,F82 .
cd frontend-v2
npm ci
npm run lint
npm run build
npm run typecheck
npm test
cd ..
python -m playwright install chromium
python scripts/run_batch0_browser.py
```

The browser runner uses a disposable synthetic SQLite fixture, disables external providers/AI, starts only loopback servers and runs both the existing catalog acceptance script and the research foundation acceptance script. CI already invokes this runner. `BATCH0_CHROME` optionally selects an installed Chromium browser; `MACROLENS_NEXT_DIST_DIR` can isolate Windows preview build artifacts. It must match between build and runner.

Unit coverage includes migration, unsupported/corrupt data, acknowledged transaction recovery, same-ID updates, concurrent conflicts, aborted/quota writes, unavailable storage, immutable origins, compact receipts and stale parameter rejection. Backend checks cover legacy/native/mixed receipts, lookback, actual validated generation IDs, timestamp/fingerprint consistency and existing permission/revocation regressions. Browser checks cover navigation/reload, acknowledged drafts, same-ID updates, numerical revision separation, recovery after quota failure, corrupt legacy storage, unavailable storage and UTC-boundary hydration. Existing catalog checks retain missing/revoked references and test all native chart frequencies.

Local results: 525 backend tests pass; 71 frontend unit tests pass; lint and Ruff pass. The broader Python suite has 863 passes, 5 skips and one inherited Streamlit test failure (`test_full_today_gold_queue_save_and_restore`: query parameter list versus string), reproduced against untouched base `b98246b`. The standard production build passes (isolated Windows build directory); browser checks pass: 26 existing catalog checks plus 16 research foundation checks, with no page/hydration errors. Midnight test: capture the server response at a simulated 2026-11-02 23:59:59 UTC and hydrate that same response at 2026-11-03 00:00:01 UTC; the new investigation correctly ends on November 2. No live-provider integration or production checks were run.

## Product PR 2 — complete one research journey

Reuse this contract/repository and existing pages. Add a small investigation editor around the current chart workspace: question + hypothesis, explicit actions attaching the current calculation as supporting/contradictory references, alternatives + uncertainty, and a user-written conclusion. Link Discovery directly into that editor, make the current investigation resumable from My Research, and label unsaved edits versus saved revisions. Keep calculation receipts visible when interpreting evidence; no generated conclusions.

Acceptance: one Discovery finding becomes one ID; question/hypothesis survive navigation/reload; user attaches both supporting and contradictory evidence to a known receipt; changed parameters/revised data never alter those references; user records alternatives/limitations/conclusion; save updates the same record; reopen shows the saved conclusion and receipt alongside a separately labelled current calculation. Missing data preserves the user's writing with a visible limitation. Include the same path starting from Dataset Explorer. No frontend rebuild, accounts, ingestion or AI is required.
