# MacroLens 2.0 — Phase 2.4

Completed October 25, 2026 on `feature/macrolens-v2`. Frontend refinement only; backend code, datasets, API contracts, providers and production Streamlit are unchanged. No merge, deployment or Phase 3 work.

## Improvements

- Today sparklines use the last 22 supplied date labels, retaining only finite observations for the compact session-spaced visual. Consecutive valid values connect across weekends, holidays and empty sessions. Dates and values are original; no new observation is inserted. This intentionally compresses empty sessions in the compact view. Investigate still retains nulls, breaks lines and preserves exact statistical alignment.
- Source & methodology opens to the dataset name, definition, linked source, latest observation date, frequency, units, adjustment, freshness and a concise verification limitation. Advanced source details remains collapsed and retains the former audit panel, exact values, revisions and retrieval details. A further full provenance record exposes the complete verification, release and provider metadata. Actual source discrepancies remain visible on cards; ordinary successful verification badges are removed. Today's market limitation is stated once in plain language; independent verification is not implied.
- Incompatible shared overlays offer immediate actions: dual axes, standardization, eligible index-to-100, or separate charts. Two-series dual axes assign the first dataset left and second right, colour axis ticks/units to match the legend and retain a concise independent-scale warning. Indexing is offered only when both dataset contracts permit it; CPI/unemployment does not offer economically invalid indexing of the rate.
- Market, overlay, separate, scatter and rolling hover values use one two-decimal formatter. Missing values remain unavailable; calculations and CSV exports retain full precision. Statistical summary r retains three decimals.
- Statistical Insights adds fixed, deterministic plain-English interpretation, readable comparison dates and counts, a 190px rolling chart with dates and fixed [-1, 1] scale, and a common-trend caution for original, indexed and standardized levels. No AI interpretation. Daily comparisons default to 60 observations; monthly/quarterly to 12. Explicit user windows and reopened saved windows take precedence. New single-dataset investigations return to frequency defaults.
- Existing chart types, layouts, four-series comparisons, transformations, lead-lag, recession context, notes and saved research remain available.

## Browser demonstrations

1. Investigate → CPI/unemployment → Overlay. The shared-scale safeguard offers visible actions without opening Advanced Analysis. Choose **Use left/right Y-axes**: CPI index left (blue), unemployment percent right (green).
2. Hover May 2024: CPI **313.18** and unemployment **3.90**. Scatter Nov 2021: **278.92**, **4.10**. Separate charts show synchronized March 2024 tooltips **312.35**, **3.90**. Rolling hover Feb 2024: **0.84**.
3. Source & methodology shows a concise economic definition and source facts. Advanced source details opens to the retained original audit record; closing it restores the concise view.
4. Save and reopen retains dual-axis CPI/unemployment, dates and original values. Standardize both datasets changes both transformations and returns to a safe shared axis. Gold/DXY exposes eligible Index to 100; its daily rolling default is 60.
5. Desktop charts remain 380px high. At 390px viewport the page measured 375px wide, with no horizontal document overflow. All five real market sparkline paths contained a single connected segment. Null observations remain in the analytical series.

## Validation

| Check | Result |
|---|---|
| Frontend deterministic tests | 30 passed (5 new usability tests) |
| Real-provider integration | 18 passed |
| Backend tests | 96 passed |
| Complete Python suite | 425 passed, 5 skipped |
| Frontend optimized build / ESLint / strict typecheck | Passed |
| Browser | Dual-axis, standardize, eligible actions, source disclosure, tooltip precision in all chart modes, rolling hover, saved reopening, desktop/mobile, sparkline continuity passed |

Full Python command: set TEMP and TMP to the workspace `work/v24-temp`, then `python -m pytest -q -p no:cacheprovider --basetemp ../v24-pytest-02`. The first attempt used the system app-container temporary directory and Streamlit AppTest failed with PermissionError writing generated scripts; that attempt was stopped. The complete rerun passed without modifying tests or production. Upstream deprecation warnings remain. The UTC/local Discovery failure recorded in Phase 2.3 did not recur in this daytime run; its production code was not changed.

The five new tests cover session continuity/source preservation, exact tooltip display precision and nulls, the actual dual-axis state transition plus shared-axis rejection, frequency defaults/descriptive interpretation, and rolling renderer constraints. Existing backend and integration tests continue to cover numerical accuracy, transformations, gaps, lead-lag, timeframes and integrity checks. UI interactions were additionally exercised in the real browser.

## Screenshots

Before images were captured from an isolated archive of unchanged Phase 2.3 HEAD `ed4a7cf157636fbbf157e887136ef64845ca4fff`, rebuilt separately, using the same backend and a 1440px desktop viewport. After images use the refined frontend at the same viewport. They are genuine browser captures, not mockups.

| View | Before | After |
|---|---|---|
| Today | phase-2-4-before-today.jpg | phase-2-4-after-today.jpg |
| Investigate | phase-2-4-before-investigate.jpg | phase-2-4-after-investigate.jpg |

Additional captures: phase-2-4-dual-axis-tooltip.jpg, phase-2-4-source-summary.jpg, phase-2-4-statistics.jpg, phase-2-4-mobile.jpg. Screenshot deliverables are in the task outputs folder.

## Preview and startup

The Phase 2.4 preview uses **http://localhost:3024**; port 3016 was already occupied by the earlier preview. Backend remains **http://127.0.0.1:8016**. Use the new link to review this build. Browser storage is origin-specific: saved research from port 3016 remains there; changing the preview port does not migrate or delete it.

From the repository root, start the existing Python environment with `python -m uvicorn backend.app.v2.main:app --host 127.0.0.1 --port 8016`. In frontend-v2 run `npm run build`, then `node node_modules/next/dist/bin/next start -p 3024`. Keep both terminals running. No new dependencies or credentials.

## Files

Changed only frontend-v2: `app/page.tsx`, `app/globals.css`, `components/data-widgets.tsx`, `components/research-charts.tsx`, `components/investigation-workspace.tsx`, `lib/presentation.ts`, `lib/workspace.ts`, `tests/usability.test.mjs`, and this guide. Existing source and analytical contracts are reused.
