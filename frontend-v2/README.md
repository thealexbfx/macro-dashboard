# MacroLens V2 — Phase 2

The approved navy UI remains the same. This isolated application retrieves real observations through a separate FastAPI process. Nothing is deployed, and the existing production Streamlit/Next.js/API services are not changed.

## Launch together

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
npm run dev
```

Open http://localhost:3001. The current review preview uses http://localhost:3016 (launched with `node node_modules/next/dist/bin/next start -p 3016` after a successful build).

The Next.js server proxies `/api/v2/datasets` and `/api/v2/compare` to `http://127.0.0.1:8016`. Optional **server-only** `MACROLENS_V2_API_URL` can select another trusted backend; it is not a NEXT_PUBLIC variable. No keys are needed for public FRED CSV or Yahoo Finance. No paid model or API is connected. Do not use the old production backend entry point for V2.

## Reuse audit and implementation

Before implementation, reviewed the existing JavaScript Next.js frontend, `backend/app/main.py`, economic and market registries, PublicTimeSeriesProvider, historical relationship service, chart-workspace loader, HTTP helpers and `macro_engine/research/analytics.py`.

Reused:
- EconomicIndicatorRegistry and MarketRegistry for identities and provider keys.
- PublicTimeSeriesProvider's FRED CSV and Yahoo daily-close parsers, with bounded network timeouts.
- Existing pure `clean`, `align`, `relationship` and SeriesMetadata utilities, including Pearson/rolling correlations and missing-period counts.

New:
- `backend/app/v2/main.py`: independent FastAPI entry point, enriched validated catalogue, Pydantic contracts, in-memory caching, typed comparison request/response, compatible transformations and error isolation.
- V2-only FRED transport uses canonical public exports and the default requests client header; the existing dated/custom-header request timed out in this environment. Parsing is reused, and source bounds are applied after retrieval. Production provider code is unchanged.
- `frontend-v2/lib/contracts.ts`: typed frontend contracts and request adapter; `lib/server-api.ts` plus two Next.js handlers provide a same-origin server proxy.
- Existing workspace now renders returned observations, source metadata, statistical evidence and CSV exports. Ask is visibly unavailable. Discovery signals are unavailable pending Phase 3.
- Investigation version 2 saves dataset IDs, per-series transformations, start/end, alignment, rolling window and note in the existing browser key. Legacy prototype notes remain in place, with no automatic reinterpretation of mock IDs.

No changes to the Streamlit app, existing `frontend`, production API entry point, research engines, providers, Ask services, Render, DNS, credentials or production research records.

## Validated catalogue

| ID | Provider ID | Source | Frequency | Original representation |
|---|---|---|---|---|
| cpi | CPIAUCSL | FRED / BLS | Monthly | SA index, 1982–84=100 |
| core_cpi | CPILFESL | FRED / BLS | Monthly | SA index, 1982–84=100 |
| pce | PCEPI | FRED / BEA | Monthly | SA index, 2017=100 |
| core_pce | PCEPILFE | FRED / BEA | Monthly | SA index, 2017=100 |
| unemployment | UNRATE | FRED / BLS | Monthly | SA percent |
| payrolls | PAYEMS | FRED / BLS | Monthly | SA thousands of persons, employment level |
| fed_funds | FEDFUNDS | FRED / Federal Reserve | Monthly | NSA effective rate, percent |
| real_gdp_growth | A191RL1Q225SBEA | FRED / BEA | Quarterly | Quarterly growth, seasonally adjusted annual rate |
| sp500 | ^GSPC | Yahoo Finance | Daily | S&P 500 price index, unadjusted close |
| gold | GC=F | Yahoo Finance | Daily | Continuous futures close, USD/troy oz |
| us10y | DGS10 | FRED / Federal Reserve | Daily | Treasury constant maturity yield, percent, NSA |
| dxy | DX-Y.NYB | Yahoo Finance | Daily | US Dollar Index, index points |
| wti | CL=F | Yahoo Finance | Daily | Continuous futures close, USD/barrel |

Economic metadata checked against the [FRED catalogue](https://fred.stlouisfed.org/series/CPIAUCSL), including [UNRATE](https://fred.stlouisfed.org/series/UNRATE), [PCEPI](https://fred.stlouisfed.org/series/PCEPI), [core PCE](https://fred.stlouisfed.org/series/PCEPILFE), [payrolls](https://fred.stlouisfed.org/series/PAYEMS), [FEDFUNDS](https://fred.stlouisfed.org/series/FEDFUNDS), [GDP](https://fred.stlouisfed.org/series/A191RL1Q225SBEA), and [DGS10](https://fred.stlouisfed.org/series/DGS10). Economic price indices are served as levels, not silently relabelled as inflation rates. Select YoY or MoM explicitly.

## Analytical semantics

- Rate/growth series: levels, percentage-point changes, standardized deviations. No percent-of-percent or indexed-rate comparisons.
- Positive economic price indices/payroll counts: levels, percent per observation, YoY, MoM, indexed to 100, standardized deviations. MoM/YoY require the monthly frequency and calendar-grid lags; missing months are not bridged.
- Positive market prices/indices: levels, percent per source observation, indexed, standardized. Signed WTI futures support levels and standardized deviations only.
- YoY is 12 monthly periods; MoM is one month. Percent change is one native observation. Percentage-point change is an arithmetic difference in percent-quoted rates.
- Index base is each series' first usable selected observation. Standardization uses that series' selected sample mean and sample standard deviation (ddof=1); constant inputs fail explicitly.
- Mixed frequencies are rejected unless the user chooses period-end alignment. Transformations happen at native frequency first, followed by last-observation sampling at the lowest common frequency across ALL selected datasets. Charts and statistics use the same sampled series. Values are not filled, interpolated or annualized. Partial terminal periods are disclosed.
- Correlations use pairwise complete observations, minimum 3. Rolling correlation requires a complete selected window (6/12/24/60 periods). Missing grid cells break windows. Exact transformation, overlap count, period, missing periods and frequency appear beside each result. No causal/predictive claims or significance tests.
- Source values and transformed values are included in CSV with IDs, dates, units and transformation names. Raw downloads cover the selected range; lagged transformation warm-up observations may precede that range and remain available from source history.

## Reliability and limits

- Retrieval occurs server-side. Backend TTL is 15 minutes; failed/stale retries are cached up to 60 seconds. Five concurrent catalogue workers and four comparison workers bound fan-out; provider timeout is 8 seconds and frontend proxy timeout is 45 seconds. The catalogue fetches once at startup and offers Refresh; cached history is shared with comparison requests in the same process.
- Provider failures never substitute synthetic values. Previously retrieved values may be shown as stale, retaining their original retrieval timestamp. Cold failures return unavailable metadata and null values. The initial catalogue returns the last 40 observations for sparklines, with full cached retrieved history used for comparisons.
- History retrieval is bounded to 1990 onward. Reported coverage means successfully retrieved observations, not the complete provider archive.
- Economic dates are reference periods; publication dates/vintages are unknown and remain null. Data may be revised. No point-in-time backtest is claimed.
- Completed market observations exclude the current UTC date. Daily source labels are not precise exchange timestamps. Holidays and missing provider observations can widen change intervals; previous observation date is shown. Gold/WTI continuous futures include roll effects. No exchange calendar or futures-roll adjustment is invented.
- Stale-age heuristics are >7 days daily, >95 days monthly, >200 days quarterly measured from the source reference date. These are conservative indicators, not a release-calendar judgment (quarter-start GDP references may be flagged even when they are the latest release).
- Saves are browser-local references/settings, not data snapshots; revisions affect reopened results. There is no cross-device sync or durable database. Old prototype notes remain labelled and unmodified.
- The public catalogue is deliberately bounded to supported US economics and five market series; no fabricated UK/euro metadata. Paid AI, actual Discovery detection and database persistence remain deferred.

## Validation

Frontend: `npm run lint`, `npm run typecheck`, `npm run build` in `frontend-v2`.
Python: install root, backend and dev requirements plus `httpx`, then `python -m pytest -q`. New V2 tests are in `backend/tests/test_v2_research.py`; `ruff check backend/app/v2 backend/tests/test_v2_research.py` checks the new Python code.

Controlled automated tests cover every transformation, missing monthly observations, incompatible transforms, constants/zero inputs, duplicates, invalid/future ranges, cache hits, stale fallback, cold outages, current-day market exclusion, mixed-frequency consent, three-series shared frequency, Pydantic validation and HTTP routes. Fixture observations exist only in tests.

Real-provider verification is separate: all 13 datasets retrieved successfully on October 24, 2026. S&P/gold/DXY/WTI latest completed labels were October 23; DGS10 October 22. CPI/unemployment September 2026, PCE/core PCE August 2026, GDP Q2 2026. These are observations, not live quotes. Real CPI YoY vs unemployment percentage-point changes produced a valid comparison via the HTTP API.

Browser verification: Today real observations, CPI search, unemployment search, selection, historical charts, 3Y preset, CPI YoY/unemployment percentage-point changes, CSV download, save with a note, My Research reopen with settings/note retained. Downloaded CSV parsed successfully: 138 rows (68 raw, 70 analytical including explicit null cells). Desktop/mobile verification and final totals are recorded in the task handoff.

No production deployment or merge. Draft PR #8 continues to target `redesign-ui`.

Final local validation: **368 passed, 5 skipped** Python tests; 19 non-failing upstream/deprecation warnings. New V2 tests: **23 passed**. Python dependency consistency (`pip check`) and Ruff on new Python code passed. Frontend lint and strict typecheck passed without warnings; production build passed. Browser exercised the complete real-data acceptance workflow, mixed-frequency rejection and explicit quarterly recovery, disabled Ask, and responsive desktop/mobile layouts (no page-width overflow at the tested mobile viewport). Browser checks are tool-driven acceptance checks, not a committed browser automation suite. External-provider tests skipped by pytest were separately verified via the V2 API; no paid AI calls were made.
