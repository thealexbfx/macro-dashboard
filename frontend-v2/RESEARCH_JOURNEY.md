# Research Journey MVP — Product PR 2

## Review scope and base

Branch `feature/research-journey-complete` starts exactly at Product PR #17 head `ceee437b5dce492232e0954ed51e86af30bd5358` and targets `feature/research-journey-foundation`. It stays stacked on #17/#16/#15. No branch was merged or deployed. No production data, ingestion, refresh, permissions, public AI, accounts or cloud storage changes are included.

At foundation inspection, Research validation run 41757440940 passed. The live Universal catalog release job 126336777260 failed in source capture with `Incomplete capture; fix source or explicitly review a smaller plan`, before its release/API/rollback tests ran. Its logs include technical-held source captures. This is a separate live-source gate, not evidence of a passing release; it is documented rather than weakened or expanded into this product PR. The completed Catalog refresh capacity run 41757441028 also passed. The foundation therefore has passing Research validation and capacity checks, with a separate failing live-source capture gate. Workflow links: https://github.com/thealexbfx/macro-dashboard/actions/runs/41757440940, https://github.com/thealexbfx/macro-dashboard/actions/runs/41757441028, https://github.com/thealexbfx/macro-dashboard/actions/runs/41757440929.

## One investigation, one workspace

Existing Investigate now contains optional, editable question/hypothesis, the existing analytical charts and working notes, supporting/contradictory evidence, Challenge prompts, alternatives, uncertainty and a provisional user-written conclusion. Anchors connect these sections without a wizard. Save controls remain available even when current calculations cannot run. Save-and-return opens My Research only after the repository commit succeeds.

Radar preserves the original finding and limitations. Its first supported question suggestion seeds the research question; an explicit followup seeds its own question and configuration while retaining the original finding. If no suggestion exists, the question remains blank rather than inventing one. Editing the question never edits the original finding. Switching Radar/Explorer/Investigate retains the active object and its writing.

My Research shows meaningful questions/titles, saved revision, last saved update time, conclusion and local draft availability. Reopening continues the same ID; a new investigation intentionally creates a separate ID. All writing is optional. Hypotheses, classification, annotations and conclusions are the researcher's interpretation, never an automated verdict or causal claim.

## Evidence and persistence

The existing v4 `EvidenceReference` gains optional `capture`; no second investigation model, database or backend save route is introduced. Each new capture contains attachment time, dataset labels, timeframe, existing chart settings, and the compact comparison receipt with dataset/source/definition references, transformation/alignment/horizon/period settings, numerical summaries, calculation timestamp and fingerprints. Raw observations, rolling arrays and scatter arrays are not copied.

Attachment requires a successful current comparison with matching parameters/dataset references. Missing, failed, stale-parameter and duplicate calculations cannot be attached. The researcher can annotate, reclassify or explicitly remove an item. Existing captures are retained byte-for-byte across draft/save updates, including classification moves; only annotations change. Recalculation never replaces attachments. Old references with no receipt remain references, explicitly disclosed without reconstruction.

“Use saved settings with latest data” restores the analytical/chart settings into the current investigation and recalculates; it does not replay historical observations. The UI separates original Discovery evidence, attached saved numerical summaries and latest results. Matching parameters with a different result fingerprint is identified; different current parameters are also disclosed. Exact historical replay is unavailable.

The same IndexedDB repository, stores, transaction acknowledgements, draft/saved revision checks and recovery/export controls from #17 remain. Its browser database version moves from 1 to 2 with existing stores/records retained. This fences older #17 clients that otherwise discard unknown capture fields during serialization: existing connections close on version change and a v1 client cannot reopen the newer database. This is a browser-local compatibility fence, not a production migration. Reload old tabs onto the current build.

Saving unavailable-data research preserves the unchanged last-saved receipt even when current chart parameters differ; that receipt keeps its own old parameters. A newly supplied receipt must match current parameters. Writing can therefore continue without fabricating a new calculation. Same-ID saves increment the saved revision; stale multi-tab writes fail visibly. No automatic merge of concurrent writing is attempted.

Limits: local storage can be cleared/evicted and is not cloud backup. There is no authentication, cross-device recovery, arbitrary JSON import or frozen chart replay. The existing bounded record/receipt/text limits still apply and storage failures remain visible. Export a draft before resolving conflicts. The saved revision is a version counter, not a complete archive of every prior conclusion.

## Automated validation

Local validation: 525 backend tests and 79 frontend tests pass; typecheck, ESLint, Ruff and the Turbopack production preview build pass. Browser acceptance passes the existing 26 catalog checks, 16 foundation/midnight checks and the 15-stage full journey, with no page errors. Desktop/mobile screenshots are retained with browser artifacts. Standard webpack builds on this Windows workspace encountered EPERM; the unchanged Linux CI build remains the standard build gate. No production checks or new live-provider requests were run locally.

From the repository root with the existing Python/frontend development dependencies installed:

```powershell
python -m pytest backend/tests -q
python -m ruff check --isolated --select E9,F63,F7,F82 .
cd frontend-v2
npm ci
npm run lint
npm run typecheck
npm test
$env:MACROLENS_NEXT_DIST_DIR='.next-phase-journey-check'
npm run build:preview
cd ..
python -m playwright install chromium
python scripts/run_batch0_browser.py
```

The same build-directory environment must be present when starting the runner. Normal CI retains the standard `npm run build`; local Windows `build:preview` uses the existing Turbopack option because webpack attempts encountered filesystem EPERM. No production URL or provider is used in the browser runner: it starts a temporary synthetic SQLite fixture with external providers/AI disabled and loopback Next.js.

New unit cases cover independent compact captures, bad/missing/stale/duplicate evidence, classification and annotations, immutable captures during same-ID saves, unavailable-data writing, legacy references, malformed captures, concurrent revisions, Discovery question/origin separation and the v1-to-v2 compatibility fence. The existing catalog/browser and foundation/midnight scripts remain in the runner; the full-journey script adds all 15 requested acceptance stages, including real shared-storage tab conflicts. Revision simulation modifies a synthetic observation and recalculates its numerical summary/fingerprint, not the saved attachments. Revocation is simulated at the existing public catalog/compare boundary.

## Exact manual journey (synthetic, local only)

Start in this branch's repository root with Python 3.12+ dependencies from `requirements.txt`, `backend/requirements.txt`, and Playwright installed. `BATCH0_CHROME` can optionally name an installed Chrome executable instead of a Playwright browser.

Terminal A, keep running:

```powershell
python scripts/validate_batch0_catalog.py --serve --port 8139
```

Terminal B, keep running after building:

```powershell
cd frontend-v2
npm ci
$env:MACROLENS_V2_API_URL='http://127.0.0.1:8139'
$env:MACROLENS_NEXT_DIST_DIR='.next-phase-journey-manual'
npm run build:preview
node node_modules/next/dist/bin/next start -p 3039
```

Terminal C, launch a visible disposable browser with the synthetic Radar finding. The helper derives the finding's comparison from the permitted fixture dataset endpoints and intercepts only the browser's Discovery response. It never registers/publishes data or modifies the production application:

```powershell
python -m playwright install chromium
python scripts/test_research_journey_browser.py --manual
```

1. In Radar, open **A synthetic relationship worth investigating → Investigate**. Confirm the suggested question, two synthetic datasets, 2000–2009 period, line/separate display and original finding/limitations.
2. Write a working hypothesis. Wait for the current chart calculation; select **Attach supporting calculation**. Add an annotation that explains your interpretation.
3. Open **Individual series displays**, change the first dataset to percentage change, wait for recalculation, and select **Attach contradictory calculation**. Confirm the first attachment retained its original level settings/results.
4. Enter alternatives, limitations, working notes and a provisional conclusion. Leave any unneeded fields blank.
5. Visit Dataset Explorer and Radar through navigation; return using the **Investigate navigation tab**. Confirm the writing and evidence remain. A Radar card's Investigate action intentionally starts/opens that finding's investigation; the navigation tab resumes the active one.
6. Select **Save and return to My Research**. Confirm the question/title, local-storage disclosure, saved revision and updated time. Reload, visit My Research and **Open investigation**.
7. Edit the question/conclusion and **Save research**. Confirm one saved investigation with an incremented revision. Reopen to confirm the update.
8. On an attachment choose **Use saved settings with latest data**. Confirm the charts recalculate while the annotation, attached summary, original finding and conclusion remain unchanged. This action promises settings reuse, not historical replay.
9. Use a 390px-wide viewport to repeat navigation/save. Select **+ New investigation**, enter your own question and save; confirm it is a separate record.
10. Close the disposable browser window to finish. Ctrl+C both local servers. This manual browser context is disposable; use **Export active draft** before closing if you want its JSON. The automated runner independently exercises numerical revisions, revoked references, storage failures and two-tab conflicts against the same fixture.

To reproduce all error/revision/conflict checks without manual interception, stop the manual servers and run `python scripts/run_batch0_browser.py` with the matching built directory. Screenshots and JSON summaries are written to `BATCH0_BROWSER_ARTIFACTS` (default temporary browser-artifact directory).
