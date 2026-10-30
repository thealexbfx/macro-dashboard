# MacroLens V2 — Phase 3.2

Phase 3.2 adds dynamic, persistent discovery to the isolated V2 application. Production Streamlit, its research engines/AI, deployment settings and credentials are unchanged. Work remains on `feature/macrolens-v2`; draft PR #8 targets `redesign-ui`. Do not merge or deploy.

## Preview and startup

Local preview: http://localhost:3032 · backend: http://127.0.0.1:8032/health.

Use two PowerShell terminals. From the repository directory:

```powershell
..\v2-venv\Scripts\python.exe -m uvicorn backend.app.v2.main:app --host 127.0.0.1 --port 8032
```

From `frontend-v2`, create the ignored `.env.local` with:

```dotenv
MACROLENS_V2_API_URL=http://127.0.0.1:8032
MACROLENS_NEXT_DIST_DIR=.next-phase32-live
```

Then (this Windows preview uses the installed Next.js Turbopack build path):

```powershell
npm ci
npm run build:preview
node node_modules/next/dist/bin/next start -p 3032
```

The current prepared preview already has dependencies and an optimized build. Leave the two server terminals/processes running. The optional custom build directory isolates previews; omit it to use standard `.next`. On this Windows host, Webpack intermittently returns EPERM while concurrently creating generated output directories. The final optimized preview uses `npm run build:preview` (Next 15.5.28 Turbopack; experimental production-build path in this pinned version). Standard `npm run build` remains available as the original Webpack build for other environments. No deployment is performed. Never remove unrelated previews. ESLint excludes generated `.next*` artifacts. TypeScript explicitly includes the active build's generated route types.

User saves remain in the browser's origin-specific `ml-research` storage. Port 3032 has its own browser origin; older ports' saves are not migrated or deleted. Version-two/version-three saves and old prototype notes remain compatible. Original discovery and historical comparison snapshots are deep-cloned; charts below them recalculate using latest revised data. Original snapshots can differ from later revisions intentionally.

## User workflow

Today presents up to three meaningful updates. Discovery Radar has Current and Historical sections within the existing navigation destination. Current promotes at most five New/Updated stories on their UTC update day; Following retains unchanged earlier stories. Empty categories stay empty. Check for updates checks only due sources and never requests AI. Cards show a short headline, key number, brief explanation, one primary chart, up to two validated research questions and Investigate/Save actions. Evidence, material history, notes, priority components and sources are collapsed. Historical cards place equal-length, same-unit transformed windows side by side, with precise source dates and two-decimal hovers.

Clicking a research question preloads actual datasets, transformations, horizon/session basis, date range, separate charts, alignment and rolling window. Investigate's Advanced Analysis exposes change horizons and daily observation basis, alongside previous alignment, rolling, axis and lead-lag controls. Default native workspaces retain their original calculation convention. Discovery explicitly opts into trading-session positions. CSV exports include horizon/basis and original source references without rounding underlying values.

## Architecture

Backend additive V2 modules:

- `expanded.py`: 15 audited free FRED definitions and dated prospective release hints.
- `movements.py`: explicit native-period horizons and conservative trading-session calendar positions; no filling or row compression of unknown gaps.
- `refresh.py`: persistent source cache, due-time scheduling, retry backoff and cross-process source leases around existing DataService/providers.
- `dynamic_scan.py`: same-horizon movement scans, curated relationship checks, grouped horizons, simple card text and actual previews.
- `state.py`: SQLite schema/transactions, lazy WAL initialization, leases and counters. Default `backend/.local/macrolens-v2.sqlite3`, ignored in Git; override with `MACROLENS_V2_STATE_DB`.
- `memory.py`: stable event/episode identities, material thresholds, immutable material versions, lifecycle and priority.
- `history.py`: selected retrospective findings, immutable first-capture snapshots and strict descriptive matching.
- `followups.py`: same-frequency, same-horizon actual-data validation and preconfigured research questions.
- `runtime.py`: fingerprinted scans, persistent reports, memory/history orchestration and deterministic suggestions. FastAPI's isolated V2 lifespan checks due sources every 60 seconds; no AI is scheduled.
- `ai_guard.py`: backend-only optional candidate generation and persistent atomic budget ledger.

Frontend: `components/discovery-radar.tsx` contains visual cards, historical comparison, Today highlights and protected optional admin panel; `lib/discovery.ts` defines evidence/snapshot/question contracts. `app/page.tsx` restores horizon/basis/history through Investigate and saves. Existing chart renderers, exact source values, alignment, transformations, recession context, lead-lag and Ask functionality remain available.

No new infrastructure, paid provider, dependency or production migration is required. Back up the SQLite database with SQLite's backup API while running, or copy it with the service stopped (including WAL/SHM when applicable). Never discard state to recover from a failure: investigate permissions/corruption and restore a backup. Discovery fails visibly when persistent memory cannot be read rather than silently resetting event identities.

## Refresh and timing

Completed daily source data is checked every 6 hours, weekly every 12 hours, monthly/quarterly every 24 hours. Known near-release monthly hints tighten to 3 hours (within one day) or 12 hours (within seven days). These are dated distributor schedule hints, not a live publication calendar; fallback checks continue when hints expire. Failure/stale-source retries back off from minutes to one hour. The UI's manual action has a persistent five-minute cooldown and never bypasses per-source due times. Source leases prevent duplicate concurrent retrieval; report fingerprints exclude retrieval-only timestamps. Numerical data, source status, definitions/methodology invalidate scans. Cached scans preserve calculation time.

The UI separately exposes provider retrieval time, latest observation, actual publication date (only if verified), source check/next check and calculation time. FRED reference dates/distributor timestamps are never substituted for primary publication dates. Missing actual publication times remain unknown. A current reference period is not a claim that today's release was verified.

## Movement and relationship methodology

Daily 1/5/21/63/252 declared trading-session positions; weekly 1/4/13/52 calendar weeks; monthly 1/3/12 reference months; quarterly 1/4 quarters. NSA inflation uses its native year-over-year transformation, not an invented monthly convention. Existing quarter-on-quarter annualized GDP growth is a rate: discovery compares its percentage-point change; it is not re-annualized.

Percentage changes use positive endpoint levels; rate changes use percentage points (Treasury/mortgage/spread displays convert to basis points); payroll changes convert thousand-person differences to net jobs. Every horizon compares against its own preceding same-horizon distribution. Required absolute empirical midrank >=99%, descriptive |z|>=2.5, >=90% coverage, shorter-half percentile >=97%, and minimum samples: 252 daily, 104 weekly, 60 monthly, 20 quarterly, or eight times the horizon, whichever is larger. Reference target is 1260 daily /260 weekly /120 monthly /40 quarterly or 12×horizon. Overlapping horizons are dependent; ranks are not p-values or calibrated confidence.

NYSE closures use the declared US equity calendar plus documented exceptional closures. FRED daily rates use federal scheduled closures as a conservative convention. SIFMA Good Friday can be an early close, so it is not unconditionally removed from bond sessions. Actual valid observations always override calendar assumptions. Unknown missing dates retain slots and can invalidate endpoints; they are not assumed to be holidays. Compact previews connect consecutive known source observations and disclose unknown missing slots; analytical charts retain nulls and timestamps. Weekly data retains actual Thursday/Friday/Saturday labels and explicit missing-week positions. Native weekly pairs require exact source dates; explicit period-end alignment can compare common Sunday-ending weeks, retaining source labels.

The five original relationship pairs and eight additions are declared with economic rationale in the API/UI. No all-pairs scan. Phase 3.1 disjoint-window coverage, constant-series, alternate-window, influence and AR(1) effective-sample safeguards are retained. Extreme-sensitive divergences remain visibly flagged; no trimming/winsorization. WTI remains outside automatic discovery because percentage changes across signed futures history are unsafe; its existing audited level research and market widget remain intact. New series can be used manually in all existing comparison workflows.

## Persistent memory and material changes

Stable identities use movement/relationship type, canonical dataset definition hash and movement direction, with an episode identifier. Same-direction qualifying horizons are grouped; opposing movements and different relationship types remain separate records. Only one prominent card per exact dataset set is promoted; other retained stories remain accessible. A primary horizon already present among previous qualifying horizons does not count as a new event merely because its rank changes.

New episodes require prior archival plus a meaningful observation interval (45 daily /120 weekly /365 monthly /730 quarterly calendar days). Within an episode, compare with the last **material version**, not the latest tiny update, so small cumulative changes can eventually qualify. Material triggers include documented definition/methodology/type changes, new related signals, a newly qualifying primary horizon, |z| increase >=0.75, movement difference >=max(25% of original movement, 0.75 original reference standard deviations), correlation sign reversal with delta >=0.15, r/delta-r movement >=0.20, or divergence-z movement >=0.75. These are explicit heuristic thresholds, not hypothesis tests.

Repeated scans retain first detection, last meaningful update and material version. Current evidence can refresh without promoting the story or changing its material-version AI cache key. Material versions remain immutable in `story_versions`. A story archives only after no longer qualifying and enough **newer healthy observations**: 10 daily /28 weekly /90 monthly /180 quarterly calendar days. Missing/stale sources never falsely resolve a story. Related discoveries and previous episodes are linked. First detection means this installation detected the pattern, not that the economic event happened on that date.

Priority components are magnitude 20, historical rarity 20, sample 15, completeness 15, stability 10, freshness 5, data quality 5, predeclared benchmark relevance 5 and meaningful novelty 5. The relevance component is explicitly a heuristic benchmark weight, not estimated economic impact. Scores are collapsed and are not probabilities. Unchanged stories are not promoted daily.

## Historical library and matching

Six predefined candidate cutoffs: May 2020 unemployment and retail sales, July 2022 CPI, January 2009 housing starts, March 2020 Treasury yields and November 2008 equities. Only those that pass the same anomaly/coverage screens enter the library; the API does not manufacture records for the other cutoffs. Current real data qualified two candidates: housing starts during the financial crisis and retail sales during the 2020 disruption. Selection cutoffs use reference observations, not verified release availability. Some cutoffs include a rebound rather than the first downturn; inspect the exact historical chart and observation dates.

Each first capture stores its full finding/configuration and the actual historical transformed window. These records are never overwritten by later source revisions and remain accessible when they do not match. Current comparisons require identical canonical definitions, transformation, native frequency, movement horizon and session basis. Windows are 60 daily /26 weekly /24 monthly /16 quarterly positions; complete equal-length windows and >=one year separation are required. No filling, constant windows or mixed conventions.

Similarity requires shape Pearson r>=0.90, standardized RMSE<=0.45, amplitude ratio 0.5–2, same terminal movement direction, each half-window r>=0.80 and conservative AR(1) effective observations >=8. Smooth highly autocorrelated patterns therefore cannot qualify simply because they trend alike. The tiny selected universe, retrospective selection, overlapping returns and repeated comparisons still create bias; these heuristic controls do not establish statistical significance, economic regime equivalence or predictive accuracy. There is no claim that a similar history predicts its subsequent outcome. The demonstrated current comparisons do **not** pass the match screens. Both charts stay visible with the explicit “No close match” result. No macro-condition similarity is inferred without supporting series.

## Expanded free catalogue

Definitions were checked against each FRED series page on 2026-10-25; all 15 series were retrieved through the existing public CSV provider. Exact adjustment/coverage appears in Dataset Explorer metadata. Platform units intentionally spell out the measured quantities.

| Dataset | Series | Frequency / convention | Units and caveat |
|---|---|---|---|
| Initial claims | [ICSA](https://fred.stlouisfed.org/series/ICSA) | weekly Saturday, SA | Number of new claims, not continuing claims |
| Job openings | [JTSJOL](https://fred.stlouisfed.org/series/JTSJOL) | monthly, SA | Thousands of openings, not net jobs |
| Participation | [CIVPART](https://fred.stlouisfed.org/series/CIVPART) | monthly, SA | Percent of civilian noninstitutional population |
| Hourly earnings | [CES0500000003](https://fred.stlouisfed.org/series/CES0500000003) | monthly, SA | Dollars/hour, all private employees; nominal, composition sensitive |
| Five-year breakeven | [T5YIE](https://fred.stlouisfed.org/series/T5YIE) | daily, NSA | Percent; includes inflation-risk/liquidity premia, not pure expectations |
| Retail sales | [RSAFS](https://fred.stlouisfed.org/series/RSAFS) | monthly, SA | Millions nominal USD; not inflation adjusted |
| Real consumption | [PCEC96](https://fred.stlouisfed.org/series/PCEC96) | monthly, SAAR | Billions chained-2017 USD; retrieved coverage starts 2007 |
| Consumer sentiment | [UMCSENT](https://fred.stlouisfed.org/series/UMCSENT) | monthly, NSA | Index 1966Q1=100; FRED can lag primary publication |
| Housing starts | [HOUST](https://fred.stlouisfed.org/series/HOUST) | monthly, SAAR | Thousands of units at an annual rate |
| Building permits | [PERMIT](https://fred.stlouisfed.org/series/PERMIT) | monthly, SAAR | Thousands of units at an annual rate |
| 30-year mortgage | [MORTGAGE30US](https://fred.stlouisfed.org/series/MORTGAGE30US) | weekly, NSA | Percent; historical Thursday/Friday labels and November 2022 method change |
| Industrial production | [INDPRO](https://fred.stlouisfed.org/series/INDPRO) | monthly, SA | Output index 2017=100, distinct from price indices |
| Yield curve | [T10Y2Y](https://fred.stlouisfed.org/series/T10Y2Y) | daily, NSA | Percent: 10Y minus 2Y, can be negative |
| High-yield OAS | [BAMLH0A0HYM2](https://fred.stlouisfed.org/series/BAMLH0A0HYM2) | daily close, NSA | Percent; licensed ICE series, retrieved history ~3 years |
| Investment-grade OAS | [BAMLC0A0CM](https://fred.stlouisfed.org/series/BAMLC0A0CM) | daily close, NSA | Percent; licensed ICE series, retrieved history ~3 years |

SAAR levels remain reported at annual rates; percent changes do not imply an additional annualization. Retrieval history since 1990 is a request floor, not an assertion that every provider returns that full history. The credit spread references consequently may not meet long-horizon discovery sample requirements. Market closure references: [NYSE](https://www.nyse.com/markets/hours-calendars), [SIFMA](https://www.sifma.org/resources/general/holiday-schedule/). Unlisted closures remain unclassified missing slots.

## Optional OpenAI setup and budget

Disabled by default. Do not paste keys into chat or put them in any `NEXT_PUBLIC_*` variable. Configure environment variables **in the backend terminal only**, using your normal local secret mechanism:

```dotenv
MACROLENS_AI_ENABLED=true
OPENAI_API_KEY=your-own-backend-environment-secret
MACROLENS_ADMIN_TOKEN=your-own-long-random-local-admin-token
MACROLENS_AI_MONTHLY_BUDGET_USD=2.00
# Optional absolute path for durable local state:
# MACROLENS_V2_STATE_DB=C:/your-local-data/macrolens-v2.sqlite3
```

These are examples, not committed real secrets. The V2 backend does not automatically load an arbitrary `.env` file: export variables before launching it. Restart only the local V2 backend after configuring. Keep it bound to 127.0.0.1. Open Radar → Optional AI → enter your **admin token**, View usage, then explicitly click Generate suggestions for meaningful updates. Never enter the OpenAI key in the browser. The browser sends the admin bearer header through its same-origin Next proxy; it is kept only in component memory, not local storage, URLs or logs. Unconfigured/wrong admin tokens receive 403.

The chosen optional model is `gpt-6-luna` with reasoning disabled, Responses structured output, no tools, standard/default service tier, `store:false`, max 800 output tokens and no retries. The official [model pricing](https://developers.openai.com/api/docs/models/gpt-6-luna) and [pricing guide](https://developers.openai.com/api/docs/pricing) were checked during implementation. The model page currently lists $0.10/1M input tokens, $0.125/1M cache-write tokens and $0.50/1M output tokens. The guard fetches/parses the official model Markdown at most once per 24 hours before optional paid work; a format/model/network/rate uncertainty blocks generation. It uses the larger input/cache-write rate and a 2× safety multiplier, ignoring discounts. No regional/priority/tool tiers or custom endpoints are enabled.

The whole serialized JSON request is capped at 20,000 UTF-8 bytes, evidence at 14,000 bytes, with a 24,000-input-token conservative allowance (including schema/framing) and 800-output-token cap. At the verified rates, the maximum reservation is $0.0068. Input tokenization is conservatively bounded by bytes plus framing allowance; reported usage outside the bounds pauses further optional AI. Reservations and integer nano-USD accounting use SQLite `BEGIN IMMEDIATE`, making the $2 UTC-calendar-month admission check atomic across processes. Each batch has a unique evidence/version key; pending/uncertain reservations count at full maximum. After verified usage, account the conservative token cost, retaining the 2× price margin. Pending requests cannot be duplicated and cannot silently expire into free budget. Month is fixed at admission in UTC; a response finishing after midnight reconciles against its original month.

Provider failures, timeouts or missing/out-of-bounds usage keep the full reservation and mark usage uncertain. Further optional AI is paused. Do not clear uncertain rows to obtain more budget. Reconcile against the provider usage/billing record offline; inspect the retained SQLite ledger and establish actual cost before an audited administrator repair. No unsafe reset/retry button is provided. Invalid structured output with valid usage is charged conservatively and falls back to deterministic suggestions. Other normal research remains available.

Only an explicit authenticated POST to `/api/v2/discovery/admin/generate` can generate. Page load, refresh, scan, hover, timeframe selection and card expansion never call OpenAI. Up to five New/Updated discoveries are batched. Cache keys combine stable discovery ID, **material evidence version/fingerprint**, prompt version and model. Tiny ongoing changes do not regenerate. The structured model response can only propose story/dataset IDs, never values, dates, correlations or free-form factual explanations. Python validates availability, definitions, frequency, horizon, actual paired movements and coverage before rendering fixed-template questions labelled **AI-suggested hypothesis**. Candidate suggestions are not statistical findings. Unsupported ideas disappear in favour of deterministic questions.

Protected usage view: current UTC month, conservative accounted spend/reservations, remaining budget, requests, lifetime cache hits, model, last successful generation and uncertainty pause status. It exposes no key, admin token, prompt or sensitive ledger content. The application budget covers only this new optional V2 path, not other applications or legacy services using the same account/project. It is an admission guard, not an OpenAI account billing limit. Set the provider's own project controls separately if desired.

No paid request was made during implementation or automated testing. AI functionality was verified with mocked transport/usage/pricing and the live optional feature remains disabled until you configure it. Official structured output reference: https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses.

## Validation and known limitation

- Optimized Next.js build, strict TypeScript, ESLint and Ruff pass. The final optimized preview build uses Turbopack because of the documented Windows Webpack EPERM issue.
- Frontend deterministic suite: 36 passed, including material-horizon/session/save/historical snapshot and one-click question contracts.
- New Phase 3.2 deterministic Python fixtures: 47 passed. Tests cover all daily horizons, monthly/quarterly/weekly conventions, closures and unknown gaps, exact source calculation, grouping, restart identities, cumulative material updates, lifecycle/archive/reappearance, immutable history, strict shape/amplitude/missing/constant/serial-dependence screens, unrelated shapes, cache/backoff and optional AI.
- Budget fixtures cover concurrent admission (only two conservative reservations admitted when budget covers exactly two), same-batch concurrency (one request), UTC month rollover, usage reconciliation, caching, invalid responses, missing usage/full reservation/pause, disabled fallback, unverified pricing and admin denial. No paid calls.
- Separate real-provider integration suite: 25 passed. Covers all 30 catalogue records, all daily horizons reproducing exact Investigate results, actual source/units/dates, stable manual refreshes and historical snapshots, existing 1M/3M/YTD/1Y/3Y/5Y/10Y/MAX/custom chart windows, source movements, scatter/correlation reconciliation, lead-lag, mixed frequency and recession context.
- Full Python suite: **494 passed, 5 skipped, 1 existing legacy Streamlit UI failure**. `tests/test_discovery_integration.py::test_full_today_gold_queue_save_and_restore` raises StopIteration because the expected Related comparison queue is absent during the known UTC/local-date boundary scenario (UTC October 26 while local October 25). This existed/documented in Phase 2.3; production date logic was not changed. Other warnings are upstream Streamlit/Pandas/Starlette deprecations. Phase 3.2 and isolated V2 tests pass separately.

Run fixtures from repository root:

```powershell
New-Item -ItemType Directory -Path ..\v32-temp -Force
$env:TEMP=(Resolve-Path ..\v32-temp).Path
$env:TMP=$env:TEMP
..\v2-venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp ..\v32-new-test-run
..\v2-venv\Scripts\python.exe -m ruff check backend/app/v2 backend/tests/test_v32_dynamic.py
```

Use a fresh workspace `--basetemp` on this Windows host to avoid the system-temp permission issue. From `frontend-v2`: `npm run build:preview` (Windows handoff), `npm run build` (standard Webpack), `npm run lint`, `npm run typecheck`, `npm test`. Opt-in real-source checks with the backend running: set `MACROLENS_V2_API_URL=http://127.0.0.1:8032`, then `npm run test:integration`. Regenerate the compact real-data evidence with `python -m backend.tools.dynamic_examples --origin http://127.0.0.1:8032`. No paid calls are made by these commands.


Final proof artifacts: `phase-3-2-evidence.json` contains 100 actual horizon calculations, current findings, immutable historical comparisons, repeated-scan identity checks and explicitly labelled isolated fixtures. The lifecycle fixture demonstrates New → Ongoing → Updated with versions 1 → 1 → 2 and unchanged original evidence. The reservation-only $2 concurrency fixture admitted 294 of 500 attempts, reserved $1.9992 and blocked the other 206, with $0.0008 remaining and zero OpenAI requests. These fixture reservations are in a temporary database, never the application ledger. All 166 backend tests pass independently.

Browser verification covers Today summaries, current/historical tabs, filters, evidence expansion, actual related-question navigation, five-session recalculation, immutable origin panel, saving/reopening discoveries and historical comparisons, desktop/tablet/mobile layout, shared historical vertical scales and two-decimal source tooltips. Navigation returns to the top of the newly selected section. The local first-detection date is explicitly labelled UTC.
