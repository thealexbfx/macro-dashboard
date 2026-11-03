# MacroLens Phase 2.3 — Advanced research workspace

The optimized local preview is running at http://localhost:3016. Open **Investigate** or reopen a Phase 2.3 example in **My Research**. This work remains on `feature/macrolens-v2`, in draft PR #8 targeting `redesign-ui`. No production changes, merge, deployment, paid service, Discovery Radar or AI integration.

## New capabilities

- **Overlay:** one chart for 1–4 selected datasets, stable dataset colours, a clickable visibility legend, and exact-value tooltips. Incompatible units or unrelated index bases are blocked from sharing an axis. Use an eligible common indexed/z-score transformation, separate charts, or explicitly configured left/right axes. Dual axes carry a visible warning about independent scaling.
- **Separate:** vertically stacked charts with one date domain and synchronized crosshairs/tooltips. A responsive 2 × 2 grid is available for multiple datasets and becomes one column on small screens.
- **Scatter:** exactly two datasets, exact aligned observation pairs, original source dates for each point, Pearson correlation and overlapping sample count. Only the scatter chart type is offered in this mode. No fitted regression line is added in this phase.
- **Chart types:** line, area and grouped bar for time-series views. Bars include a zero baseline. Area fill starts at the displayed data minimum and is explicitly described as not encoding a total. No smoothing, interpolation or filling is introduced.
- **Timeframes:** 1M, 3M, YTD, 1Y, 3Y, 5Y, 10Y, MAX and custom dates feed the same backend comparison used by charts and statistics. MAX retains the existing 1990 retrieval floor and actual provider coverage.
- **Transformations:** existing dataset-specific validation remains in force. Common display offers only transformations allowed for every selected dataset; Individual series displays retains independent choices. Indexing is not offered for ineligible rate/signed series merely to enable an overlay.
- **Advanced Analysis:** explicit frequency alignment, rolling-correlation window, axis assignments and ±12-period lead-lag controls. A prominent analytical-shift banner remains visible when the section is collapsed.
- **Recession context:** optional US-only historical shading from [FRED USREC](https://fred.stlouisfed.org/series/USREC), the St. Louis Fed interpretation of NBER chronology. Its monthly NSA indicator shades the month following a peak through the trough month, inclusive. It is retrospective context, not causal explanation or real-time detection. Context has its own source, coverage, retrieval time and stale/unavailable handling. The structured period contract supports future event adapters without adding them now.
- **My Research:** new version-three records preserve mode, chart type, timeframe/dates, transformations, axes, layout, shading, shift, visibility and notes. Versions one/two remain intact; version two opens with conservative separate-chart defaults. Saving appends to the latest storage contents so another tab's new records survive. Unreadable storage is not overwritten.

## Review examples using real observations

Choose datasets through Dataset Explorer, then Compare selected. The selection is limited to four datasets.

1. **Annual inflation and unemployment:** select `cpi_nsa` (CPIAUCNS) and `unemployment` (UNRATE). In Individual series displays, choose YoY for CPI and original levels for unemployment. Separate mode compares independent scales directly. For Overlay, explicitly assign CPI and unemployment to different axes in Advanced Analysis. Enable US recession shading and choose 10Y.
2. **Lead-lag scatter:** use the same two datasets, select Scatter, and in Advanced Analysis shift unemployment by **+6 months**. Hover a point to see the comparison period and both original source dates. The saved Phase 2.3 example preserves this configuration.
3. **Comparable market scales:** choose gold and DXY, then Common display → Indexed to 100 or Standardized deviations. Use Overlay or Separate and switch line/area/bar. The original market-price verification limitations remain disclosed in Source & methodology.
4. **Four-series grid:** select CPI, unemployment, PCE and core PCE, choose standardized deviations, Separate → 2 × 2 grid. With more than one statistical pair, a pair selector keeps all six pairwise results accessible without rendering six expanded rolling panels at once.

Dated provider/API consistency evidence is in [phase-2-3-real-checks.json](phase-2-3-real-checks.json). For the fixed 2016-10-24 through 2026-10-24 window:

| Comparison | Pearson r | Paired observations |
|---|---:|---:|
| Unemployment level / annual NSA CPI, no shift | -0.3602161498 | 118 |
| Unemployment leading annual NSA CPI by six months | -0.0666242898 | 111 |

These are descriptive results from latest revised observations, not independent verification of every historical input or predictive evidence. The same feed produced the recorded March–April 2020 USREC interval. Primary/distributor verification limits from Phase 2.2 remain in force, including the four independently unverified Yahoo closing prices.

## Lead-lag methodology

For a selected series `S`, positive offset `h` relabels its value at reference period `t` onto comparison period `t+h`. It is paired with the other series at `t+h`: **S(t) versus Other(t+h)**. A negative offset compares S with earlier observations of the other series. The selected series is described as leading for positive offsets and lagging for negative offsets.

1. Validate the original observations and apply the existing native-frequency transformation. Growth transformations can use their required historical lookback before the visible window; they are not recalculated from truncated chart rows. Indexed values use the first valid selected observation. Z-scores use the selected-period mean and sample standard deviation.
2. Same-frequency comparisons retain native reference labels. Mixed frequencies require explicit common period-end sampling: the last native observation in each coarser month/quarter is selected, with reported nulls and missing periods retained. Transformed daily changes sampled monthly remain daily changes, not newly calculated monthly returns; frequency is shown and incompatible per-observation horizons cannot silently share an axis.
3. Shift analytical labels by complete calendar months/quarters at that common frequency. Daily shifts mean **calendar days**, including weekends, not a fabricated trading calendar. Only exact matching dates are paired. Missing calendar periods are never compressed into available-row positions.
4. Preserve original source reference dates alongside every analytical label. Both the displayed value's source reference and shifted label must be inside the chosen range. This can reduce overlapping coverage. Raw provider observations are unchanged; CSV exports add source-reference, shift-period and shift-unit columns.
5. Charts, scatter points, Pearson correlation and rolling correlation use those same prepared series and aligned pairs. Native monthly/quarterly statistical labels now match reference-period starts; explicitly sampled series use period ends. Comparison labels are bounded by the selected dates. A period-end label after the endpoint is omitted rather than shown outside the requested range.
6. Pearson r is unavailable below three nonconstant paired observations. Rolling r requires a complete window, with missing cells breaking completeness. Recession shading stays on its unshifted historical calendar, even when a series is analytically shifted.

This is observation-period research using revised data, not a publication-time backtest. Release lags, revisions, autocorrelation, sample selection, common trends and searching multiple offsets limit interpretation. No significance, forecasting or causal claims are added.

## Validation results

- **V2 backend: 80 passed**, including 28 new workspace tests covering shifts/direction, source-date provenance, scatter/statistical consistency, calendar gaps, daily units, mixed-frequency consent, selected-window bounds, normalization, absent coverage, recession boundaries and stale/outage behavior.
- **Frontend: 25 deterministic tests passed**, including axis compatibility, indexed/z-score scales, chart-type switching, shared tooltip rows, missing values, stable colours, version-two restoration, complete version-three round trips, storage preservation and invalid-storage protection.
- **Real-provider integration: 18 passed**, covering all eight timeframe presets, custom dates, existing Phase 2.2 headlines/movements, compatible overlays, exact scatter pairs, lead-lag samples, common-quarter sampling and FRED USREC alignment. These are separate from deterministic fixtures and do not certify independent market-price inputs.
- **Build, lint, strict typecheck, Ruff and Python formatting checks passed.** Recharts is reused; no new charting dependency or package-lock change.
- **Browser acceptance passed:** incompatible raw-unit overlay rejection; explicit dual axes; four-series overlay; legend hiding; four-panel grid; line/area/bar switching; two synchronized crosshairs with identical exact tooltip values; scatter source-date tooltips; preserved advanced saves; original Phase 2 saves; custom 2020–2022 scatter window (36 matching points/statistical pairs); mobile layouts without horizontal overflow. At the tested 390px viewport, stacked charts were 316px wide and 320px high. Screenshots of Overlay, Separate and Scatter accompany the local handoff.

### Existing full-suite failure, independently reproduced

The full Python run returned **424 passed, 5 skipped, 1 failed**. The failure is the untouched production Streamlit test `tests/test_discovery_integration.py::test_full_today_gold_queue_save_and_restore`: the Related comparison queue is absent because the Discovery link uses the UTC date while its receiving workspace validates against the local date. At 19:42 CDT on October 24, UTC had rolled to October 25, and the generated October 24 endpoint failed the local strict-before-today check.

The identical failure was reproduced from an isolated archive of the unchanged Phase 2.2 commit **0a75c528eb84caca73dbfbfc6237e4dcaa2b207e**. No production code or existing test was changed to hide or repair it. A separate run excluding that known baseline failure returned **424 passed, 5 skipped, 1 deselected**, with upstream deprecation warnings. All 80 affected V2 tests subsequently passed after the final provenance refinements. This task does not claim the complete legacy suite is green.

## Architecture and files

- `backend/app/v2/workspace.py`: pure analytical-label preparation, source-date provenance, recession interval construction and isolated context caching.
- `backend/app/v2/main.py`: additive lead-lag request fields, chart provenance, aligned scatter response, bounded statistical labels and context route. Empty selected coverage is explicitly empty rather than fabricated.
- `frontend-v2/lib/workspace.ts`: conservative axis compatibility, stable colours, tooltip rows, workspace restoration and safe append-only saves.
- `frontend-v2/components/investigation-workspace.tsx`: approachable controls, statistics, coverage and notes.
- `frontend-v2/components/research-charts.tsx`: shared Recharts time-series/scatter rendering and synchronized tooltips.
- `frontend-v2/app/api/v2/context/recessions/route.ts`: existing server-side proxy pattern for optional historical context.
- Relevant backend/frontend deterministic and real-provider tests accompany the implementation.

Existing research engines, data providers, canonical dataset definitions and Phase 2.2 quality checks remain unchanged. The response extensions are additive; existing dataset IDs, underlying values and saved record contents are preserved.

## Run locally

Use Python 3.12+ and Node 22+. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
.\.venv\Scripts\python -m uvicorn backend.app.v2.main:app --host 127.0.0.1 --port 8016
```

In a second terminal:

```powershell
cd frontend-v2
npm ci
npm run build
node node_modules/next/dist/bin/next start -p 3016
```

Open http://localhost:3016. The separate backend defaults to http://127.0.0.1:8016 through the existing Next.js proxy. No credentials or paid services are required. Keep both processes running. `npm run dev` remains available on port 3001 for normal development.

Checks: `npm test`, `npm run lint`, `npm run typecheck`, `npm run test:integration` (running backend required), and Python `pytest`. Use a fresh workspace-local `--basetemp` and `-p no:cacheprovider` in this restricted Windows environment. See the explicit legacy-suite failure above when assessing the full Python result.
