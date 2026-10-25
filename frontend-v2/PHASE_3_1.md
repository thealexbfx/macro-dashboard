# MacroLens 2.0 — Phase 3.1 Discovery Radar

Implemented October 25, 2026 on feature/macrolens-v2. Preview: http://localhost:3031; backend: http://127.0.0.1:8031. PR #8 remains draft and unmerged. No production Streamlit, provider definitions, credentials, infrastructure or other branches changed. No generative AI or Phase 3.2–3.4 work.

## Product and workflow

Discovery Radar is a new navigation destination with category filters, ranked real-data cards, native-change previews, evidence, linked sources, methodology, notes, Investigate and Save discovery actions. Today links to it; other pages and Phase 2.4 charts remain intact. Empty categories show an honest empty state. Request failures clear the live report instead of presenting old findings as current.

Investigate preloads dataset IDs, audited transformations, native alignment, full baseline-to-recent dates, rolling window, chart mode/layout and zero lead-lag settings. The origin panel preserves the original evidence separately from recalculated charts. View baseline window, View recent window and View full discovery period reproduce the relevant periods.

Save discovery stores its type, evidence arrays, source reference dates/metadata/fingerprints, methodology version, calculation settings, workspace and research note. My Research has a Discovery Radar collection and snapshot label. Reopening preserves evidence and notes while charts fetch revised observations. Saving an adjusted investigation retains its original discovery. Old version-two/version-three investigations and Phase 1 notes remain compatible; unreadable storage is never overwritten.

Browser storage is origin-specific. Existing research on ports 3016/3024 was not moved or deleted. Snapshots consume normal browser-storage capacity; failed saves report the error and preserve previous records.

## Real examples

The October 25 scan surfaced two current findings:

- 10Y Treasury yield change, October 22: -17.00 basis points, approximately 99.1st absolute-movement percentile, signed z -2.76, with 1,152/1,260 preceding labels usable.
- Unemployment changes versus payroll jobs changes: recent r -0.104390597 from 22/24 monthly pairs (October 2024–September 2026), versus baseline r -0.983515497 from 120/120 pairs (October 2014–September 2024). Difference +0.879124901.

No current divergence qualifies. Nothing was invented to fill that category. Exact evidence is in phase-3-1-evidence.json; full input arrays accompany the local handoff. These are reproducible provider/API calculations, not independent certification of every historic input. Yahoo independent-verification and futures-roll limitations remain visible.

A separate retrospective replay for the window ending June 2020 surfaces unemployment/payroll divergence: baseline r -0.588671322, standardized three-period gap -5.256071105, descriptive z -10.490686839, absolute empirical percentile 100% of that finite reference sample. It is sensitive to one extreme observation: omitting the largest recent gap changes direction, so its stability ranking is reduced and the warning is explicit. The related PCE/core-PCE replay is also sensitivity-flagged.

Historical examples use today's revised observations, not information available then. June observations were not necessarily published by the July 1 cutoff. These are not historic alerts, availability backtests or predictions, and are not inserted into today's Radar. Two cutoff dates (July 1, 2020 and July 1, 2022) were declared before replay. Episode selection and repeated comparisons still create selection bias.

## Universe

Only existing canonical data are used. Twelve eligible change series:

| Dataset | Transformation |
|---|---|
| SA CPI, core CPI, PCE and core PCE | Native monthly percent change (mom) |
| U-3 unemployment and monthly-average FEDFUNDS | Percentage-point change (pp) |
| Payroll employment level | Adjacent monthly difference times 1,000 (jobs) |
| Already annualized quarterly GDP growth | Percentage-point change, not percent change of a growth rate |
| Nominal 10Y yield | Daily percentage-point change; card display converts to basis points times 100 |
| S&P 500, gold futures and DXY | Native per-observation percent change (percent) |

NSA CPI variants are excluded to avoid duplicate inflation variants. Signed WTI is excluded because its audited contract does not permit percent returns. No new transformation is invented. FEDFUNDS is not a FOMC target range; gold is not spot or verified settlement. No raw trending level is scanned as an anomaly or relationship.

Only five predefined pairs are scanned:

| Pair | Reason |
|---|---|
| CPI / core CPI monthly inflation | Separate food/energy exposure within related price measures |
| PCE / core PCE monthly inflation | Related consumption-price measures with different exclusions |
| U-3 change / payroll jobs change | Distinct household and establishment-survey labour measures |
| Gold futures return / DXY change | Dollar-pricing context; rolls and independent-verification limits remain |
| S&P 500 return / nominal yield change | Cross-asset co-movement, not bond returns or causal valuation evidence |

All pairs share native frequency. Mixed-frequency Discovery pairs are rejected rather than silently sampled or filled. Investigate's explicit alignment controls remain available. The API distinguishes single-series anomalies and curated relationships, reports zero exploratory pairs, and never searches every combination.

## Calculations and safeguards

The scanner gets validated observations through existing DataService and reuses the existing transform function. Up to 15 years are prepared, bounded by completed dates and latest valid source reference. No filling, instrument substitution, winsorization of reported inputs or changes to existing research calculations.

### Unusual movements

Compare the terminal native change with preceding reference values: up to 1,260 supplied daily labels (minimum 252 valid), 120 monthly periods (minimum 60), or 40 quarterly periods (minimum 20). Require at least 90% completeness, a present terminal movement and nonconstant reference values.

Absolute empirical midrank is (count(abs(reference)<abs(latest)) + 0.5*count(equal))/n; require at least 97.5%. Signed standardized magnitude is (latest-reference_mean)/reference_sample_std; require absolute value at least 2. The recent half of valid reference values must also place the absolute movement at or above its 95th percentile.

Percentiles describe the finite sample, not p-values or event probabilities. Z is descriptive, with no normal-tail claim. Explicit null daily labels and holidays reduce completeness; they are not fabricated into observations or silently removed from analytical inputs. Existing strict per-observation transformations can suppress daily candidates when supplied gaps are frequent.

### Changing correlations

Daily recent window: 60 supplied labels versus preceding 504; baseline minimum 252 valid pairs. Monthly recent window: 24 periods versus preceding 120; baseline minimum 60 pairs. Baseline and recent windows are disjoint. Alternate recent windows are 90 daily or 36 monthly, each with its own preceding baseline.

All four windows need at least 90% completeness. Terminal pair must be valid. Pearson r uses pairwise-complete rows within declared windows; missing periods remain on the grid and count against coverage. Constants and inadequate samples are rejected.

Require absolute recent-minus-baseline difference at least 0.50. Alternate windows must support the same direction with difference at least 0.30. An influence diagnostic removes the single largest combined absolute standardized change in each window; the difference must retain direction and magnitude at least 0.30. Reported correlations retain all observations. Nonfinite influence diagnostics are rejected.

An AR(1) diagnostic uses n_eff=n*(1-p)/(1+p), where p=max(0,min(0.99,rho_left(1)*rho_right(1))), bounded to [3,n]. Recent and alternate-recent effective n must be at least 8, baselines at least 24. This conservative screening heuristic is not a significance calculation or a complete treatment of serial dependence.

Alternate windows overlap and are not independent replications. Common shocks such as the pandemic can still influence relationships. No structural regime-change claim is made.

### Divergences

Baseline absolute r must be at least 0.40, retaining direction and absolute r at least 0.30 under its influence diagnostic. Standardize native changes using only disjoint baseline means/sample standard deviations. Gap = standardized_right - sign(baseline_r)*standardized_left.

Compare the latest three-period mean gap against historical baseline three-period means. Require absolute descriptive z at least 2.5 and absolute empirical midrank at least 97.5%. The six-period mean must retain direction with absolute z at least 1. Terminal six periods must be complete. Missing baseline windows are not compressed into adjacent rows.

Another diagnostic omits the largest absolute centered gap from the last six periods. A sign change or diagnostic absolute z below 1 flags extreme-observation sensitivity and halves stability points. Original reported gaps, z-scores and evidence arrays remain unchanged. Cards warn explicitly; this is not a hidden data adjustment.

### Ranking, duplicates and inference limits

Research priority is a visible sum, not confidence or economic importance:

| Component | Points |
|---|---|
| Magnitude | Up to 25: min(abs(z)/4,1) for movements/divergences; min(abs(delta_r),1) for correlation changes |
| Historical rarity | Absolute empirical percentile times 20; zero for correlation changes, for which rarity is not estimated |
| Sample | Baseline valid / nominal reference size, capped at 1, times 15 |
| Completeness | Coverage times 15; minimum recent/baseline coverage for correlation changes |
| Stability | 15 for passed alternate-window screen; 7.5 for extreme-sensitive divergence |
| Freshness | 10; stale/unavailable/discrepant sources are excluded before ranking |

Maximum 100. Correlation findings have a lower attainable total because no rarity claim is assigned. Cross-category scores are heuristic priorities, not comparable statistical confidence estimates. Sort by score with deterministic ID tie-breaker. Keep one finding per series/unordered pair, including competing correlation/divergence descriptions. Collapse related monthly CPI/PCE anomalies to the highest-ranked inflation movement. Return at most eight findings.

Several predefined tests and repeated refreshes are examined. No formal multiple-testing-adjusted significance, p-values or probability claims are reported. Minimum samples, change-based inputs, coverage, predeclared windows, influence diagnostics and deduplication reduce noise; they do not remove serial dependence, selection bias, revisions or publication lags. Every candidate remains an exploratory research question.

## Architecture and provenance

- backend/app/v2/discovery.py: reusable detection, alignment, evidence, ranking/deduplication and cached orchestration.
- backend/app/v2/main.py: additive GET /api/v2/discovery; existing dataset/comparison contracts unchanged.
- Existing DataService provider cache remains authoritative (normally 15 minutes). Radar report cache is up to five minutes, invalidated by full source-payload fingerprint changes, including revisions, status and metadata. Reports are deep-copied. Concurrent provider refreshes can legitimately change fingerprints. Refresh scan checks cached inputs; it does not imply live ticks or force repeated provider calls.
- frontend-v2/app/api/v2/discovery/route.ts: existing server proxy pattern.
- frontend-v2/components/discovery-radar.tsx: display, filtering, evidence, notes and actions; no statistical detection in the browser.
- frontend-v2/lib/discovery.ts: typed contracts and deep-cloned snapshot construction. Existing investigation type gains an optional discovery property.
- Page integration and scoped styles preserve the design. At narrower desktop/tablet widths, navigation scrolls inside the header. Local environment files are ignored.
- backend/tools/discovery_examples.py: current and predeclared retrospective examples through the running cached API. Fixtures never enter live results.

Source records contain canonical/provider IDs, definitions, units, seasonal adjustment, freshness status, reference/retrieval dates, revisions, quality notes, verification limits and input fingerprints. Full source evidence stays accessible. Historical release-time vintages and exchange-calendar reinterpretation are not introduced. Yahoo independent-verification limits remain visible.

## Validation

| Check | Result |
|---|---|
| New deterministic backend Discovery cases | 23 passed |
| Complete Python suite | 448 passed, 5 skipped |
| Frontend deterministic tests | 33 passed, including 3 new snapshot/configuration cases |
| Separate real-provider checks | 21 passed, including 3 new Discovery reconciliation/cache/quality checks |
| Optimized Next.js build, ESLint, strict typecheck | Passed |
| Ruff and formatting for changed/new Python code and tests | Passed |
| Browser | Filters, honest empty state, evidence panels, notes/save, origin banner, baseline/recent reproduction, saved reopening, tablet navigation and mobile layout passed |

Browser reproduction showed recent r -0.104 and baseline -0.984 with expected counts. Existing Investigate rolling correlation retains its stricter complete-window requirement: a 24-period rolling value can be unavailable while descriptive recent-window Pearson r has 22/24 pairs. No filling makes them match.

No unrelated failures occurred in the final run. Existing upstream deprecation warnings remain. The old UTC/local-date Discovery failure from Phase 2.3 did not recur in this daytime run; production code was not changed. Workspace TEMP/TMP avoids the previously observed Windows system-temporary-folder permission problem.

Tests cover unusual changes, correlation shifts, divergence arithmetic, short/constant samples, native/mixed-frequency handling, missing periods/terminal nulls, autocorrelation/one-point influence guards, ranking, duplicate/related findings, revisions/cache/stale handling, additive endpoint, investigation handoff, snapshot immutability and older saved research. Real-provider checks separately reconcile findings with the canonical observations through Investigate.

## Preview and reproduction

Keep two terminals running. From repository root, use the existing virtual environment to run:

    python -m uvicorn backend.app.v2.main:app --host 127.0.0.1 --port 8031

In frontend-v2, configure MACROLENS_V2_API_URL as http://127.0.0.1:8031 in the local environment (or ignored .env.local). The current local preview file contains only that localhost URL. Then run:

    npm run build
    node node_modules/next/dist/bin/next start -p 3031

Open http://localhost:3031 and select Discovery Radar. Backend health: http://127.0.0.1:8031/health. No new dependency, production configuration or credential is required. Existing previews use other ports and were left alone.

Checks: frontend npm test, npm run lint, npm run typecheck, npm run build. Set the local API origin to 8031 for npm run test:integration. Python pytest uses workspace TEMP/TMP, -p no:cacheprovider, and a fresh workspace --basetemp.

To regenerate complete real evidence from repository root:

    python -m backend.tools.discovery_examples --origin http://127.0.0.1:8031 --output outputs

This uses existing cached API observations. Historical replay dates are predeclared in the tool and explicitly marked as latest-revised retrospective research, not historical publication-time alerts.

## Handoff artifacts

- phase-3-1-evidence.json: compact committed dated results and source evidence.
- phase-3-1-real-discoveries.json: full current observations/change arrays in task outputs.
- phase-3-1-historical-examples.json: two explicitly retrospective replays in task outputs.
- Genuine browser captures: phase-3-1-radar.jpg, phase-3-1-investigate.jpg, phase-3-1-saved-discovery.jpg, phase-3-1-divergence-empty.jpg, phase-3-1-mobile.jpg.

These screenshots and findings are real calculated results, not generated mockups. The application is ready for research-methodology and design feedback before later phases.
