# MacroLens Phase 2.1 — UI refinement

The navy visual identity, Python providers, research calculations and API contracts are preserved. Changes are confined to frontend-v2 on feature/macrolens-v2. No deployment or PR merge.

## Changes

- Body copy is 15px, controls 14px, secondary metadata generally 12–13px. Content is capped at 1,400px.
- Market widgets show two-decimal prices/percentage changes, Treasury changes in basis points, observation dates and explicit delayed/stale/unavailable labels. Yield colours describe yield direction, not bond returns. Gold and WTI remain explicitly continuous futures, not spot prices.
- Sparklines use the last 22 supplied source observations, retaining nulls and excluding dates after the reported latest observation. No synthetic curves or filling. Decorative Radar strokes are removed; detection remains unavailable.
- Expandable source panels retain identifiers, raw values, prior dates, units, definitions, adjustment, coverage and retrieval timestamps.
- Economic formatting respects percent rates, index levels, thousands of persons and monthly/quarterly reference periods. Unknown publication dates remain unknown.
- Timeframes: 1M, 3M, YTD, 1Y, 3Y, 5Y, 10Y, MAX and custom dates. Presets reset their endpoint to yesterday UTC. Calendar subtraction clamps month ends/leap days. YTD begins January 1 of the endpoint year. Charts and statistics use the same existing start/end API fields.
- MAX uses the existing retrieval limit of 1990 onward, subject to actual provider coverage; it does not claim every series exists since 1990.
- Advanced Analysis is collapsed by default, offered only for multiple datasets, and retains frequency alignment and rolling windows. Single datasets use native alignment without irrelevant controls.
- Desktop comparisons use side-by-side charts: single panels 360px tall, comparisons 340px, mobile 320px. Legends, date axes and exact-value tooltips are clearer. Reported nulls break lines; source observations remain exact.
- Statistical data facts are separate from user-authored interpretation. Saved-investigation records and storage keys are unchanged.

## Display conversions

Price change is `(latest / previous - 1) * 100`, using the source dates identified by the existing backend. Percent-quoted Treasury yield differences are multiplied by 100 to display basis points. WTI's API absolute difference is unchanged; its widget displays the equivalent percentage for positive prior prices. Nonpositive prior futures prices use labelled absolute changes. Rounding affects display only; observations and downloads are unchanged.

Verified October 24 observations: gold 4,007.90 / -1.29%; S&P 500 7,623.68 / -0.52%; US 10Y 4.96% / -17.00 bp; DXY 101.81 / +0.20%; WTI 103.27 / +3.82%. These are delayed observations.

## Run

From the repository root, start `python -m uvicorn backend.app.v2.main:app --host 127.0.0.1 --port 8016`. In frontend-v2, run `npm ci` then `npm run dev`; open http://localhost:3001. The review preview uses http://localhost:3016 after building and starting Next.js on port 3016. No new dependencies, credentials or paid services are required. See README.md for the existing architecture and API setting.

## Verification

- `npm test`: 10 deterministic tests covering preset boundaries, month ends/leap years, YTD/MAX, precision, yield basis points, WTI changes, negative prior prices, stale/missing states, sparklines and economic periods.
- `npm run test:integration`: 11 explicit real-provider checks through the running V2 API. All preset windows and custom dates bound charts/statistics, and widget movements reconcile with source differences. These are separate from fixture-based tests.
- Frontend build, lint and strict typecheck passed without errors or lint warnings.
- Full Python regression: 368 passed, 5 opt-in live checks skipped, 19 non-failing dependency/deprecation warnings. The first run hit restricted old temporary folders; the successful run used a fresh workspace-local basetemp/cache. Ruff passed. No Python source changed.
- Real Gold/DXY verification produced 23 gold observations (1M), 66 (3M), 204 (YTD), 252 (1Y), 757 (3Y), 1,258 (5Y), 2,515 (10Y), 6,563 (MAX). Custom calendar 2024 returned 252.
- Browser checks exercised every preset, custom dates, single-series controls, expanded Advanced Analysis, rolling/alignment changes, and reopening both existing and new research. Responsive checks are tool-driven acceptance checks, not a committed browser test suite.

Phase 2 limits remain: latest revised observations, unknown publication/vintage history, futures roll effects, conservative stale flags and browser-local reference saves. No Phase 3 functionality is enabled.
