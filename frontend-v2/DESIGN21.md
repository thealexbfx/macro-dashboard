# MacroLens 2.1 presentation redesign

Base: reviewed Product PR #18 at `7bce9590268c32cc97de5d384dacfe97d8181deb`; its Research validation CI passed. No supplied reference image was attached, so the implementation follows the brief's restrained dark fintech direction.

## Information architecture

| Primary section | Default experience | Further detail |
| --- | --- | --- |
| Home | One question entry, three market cards, two findings, recent research | Source details and data library |
| Discover | Concise visual findings, one Investigate action | Original evidence, source timing, methods, history and administrator tools |
| Research | Question, datasets, unified chart area, observations, evidence and conclusion | Display settings, transformations, statistics, methodology and calculation history |
| My Research | Question-led library, related data, updated date, conclusion, Continue | Export and browser-local recovery |

Data library is a secondary tool accessible from the header and Research. AI is explicitly unavailable in Help; no AI capability is activated or implied. Mobile uses the same four destinations in a bottom navigation bar.

## Review slices

1. `feature/macrolens-21-shell-home`: tokens, reusable shell, navigation and Home.
2. Discover and search-first Data library, stacked on slice 1.
3. Progressive Research workspace and shared chart presentation, stacked on slice 2.
4. Research library, responsive polish and final consistency, stacked on slice 3.

All slices preserve the existing Next.js/FastAPI architecture, analytical logic, dataset gates, original findings, receipts, IndexedDB repository and revisions. No production changes, deployments, ingestion, accounts or public AI. No automatic merges.

## Design rules

Restrained navy surfaces; blue actions and cyan highlights; stable series colors; comfortable spacing and readable type. Every extra disclosure must reveal an actual existing capability. Material stale/unavailable/source warnings remain visible. Empty states never invent developments or research. Technical provenance belongs in detail panels, not the primary task flow.

Explore is the simple default. Investigate adds explicit evidence and interpretation. Advanced reveals full analytical tools without losing research context or changing data silently.

## Validation and screenshots

Each slice runs frontend unit/type/lint checks and the existing catalog, Research Journey, storage-conflict and UTC-boundary browser scenarios, plus focused presentation checks and desktop/mobile screenshots. Screenshots must be visually inspected before publishing that slice. The browser runner now uses isolated loopback ports, preventing a developer's running manual preview from being mistaken for the tested build. Existing manual-preview commands still default to their documented ports.

Use the existing `MACROLENS_NEXT_DIST_DIR` for separate local builds. Build the frontend, then run `python scripts/run_batch0_browser.py`; `ML_REDESIGN_PHASE` selects the presentation acceptance scope. Screenshots and summaries are written to `BATCH0_BROWSER_ARTIFACTS`. Standard CI continues to build with webpack; local Windows preview builds may use the existing Turbopack command.

## Completed review

Draft PRs #19, #20 and #21 contain slices 1–3; the library slice is stacked on #21. Review and merge in stack order only after approval, retargeting each dependent PR after its parent merges.

Final local validation: 83 frontend tests, 525 backend tests, 26 catalog browser checks, 16 foundation/UTC checks, 15 complete journey checks and the phase-4 presentation checks passed. Type checking, lint and the isolated Turbopack preview build passed. Desktop and mobile screenshots were inspected for each slice. Backend tests retain three existing dependency warnings.

The journey checks cover updating saved research, immutable original evidence, recalculated-result differences, draft recovery, exports and multi-tab conflicts. The library tests cover draft/saved deduplication, timestamp ordering and retaining meaningful chart-only drafts. Browser fixtures use synthetic observations; this is not a production-source validation.

Manual review: Home → Discover → Investigate; add a dataset, open Chart options and statistics, save evidence, add a challenge and conclusion, save to My Research, search and resume, update, reload and export. Repeat at a narrow viewport. Check source warnings and original-versus-latest results in their disclosures.

Research remains browser-local, with existing IndexedDB persistence and export/recovery. Section URLs contain only a view enum. No backend, registry, refresh schedule, production data, account or AI changes were made.
