# Discovery integration on the live application

Base: `redesign-ui@01161c8c242d52b925a03b967d51c480223a3116`.
Branch: `feature/discovery-redesign-integration`. This replaces the proposed
main-based rollout: do not merge PR #5/#6 into redesign-ui to obtain Discovery.
No Render configuration, existing branch, Ask/backend or Next.js source changed.

## Scope and reuse

The UI-independent `discovery/engine.py`, `store.py` and analytical tests were
selectively ported from Phase 1 and adapted. No obsolete app.py, old navigation,
chart module, providers or dependency manifests were copied. Existing three-page
navigation, styling, cached chart-workspace loaders, registry, pair charts and
version-1 research storage remain authoritative. No new dependency or service.

Today contains a compact Radar (Latest / Most unusual, up to five distinct
datasets in the last 90 days). Each card shows the measured change, observation,
prior-history percentile, persistence, source/latest observation and expandable
methodology. Failed sources are isolated and labelled unavailable; raw provider
URLs/exceptions are not displayed. Missing release/revision/cache provenance is
explicit. The cached scan is on demand (15 minutes), not background polling.

Signals use prior-only mean/sample volatility and absolute-change empirical
midranks, with half credit for ties (1e-9 relative/1e-12 absolute roundoff
tolerance). Standardized return and centered z-score are distinct. Thresholds
compare each instrument to its own history. Moving averages/momentum, significant
reversals, acceleration context and persistent episodes are included. Trend IDs
are anchored to episode starts; continuing snapshots retain observation history.
Standalone SQLite deduplication/versioning/feedback remains available but does
not replace or migrate existing research records. Radar itself uses cached
snapshots and does not require a production writable database.

## Identities and source semantics

| Dataset | Exact identity | Change unit |
|---|---|---|
| Gold | GC=F continuous futures, unadjusted close, USD/troy oz | percent return |
| Bitcoin | BTC-USD aggregate quote, unadjusted close | percent return |
| S&P 500 | ^GSPC price index, excludes dividends | percent return |
| CPI | `us_cpi_sa_yoy`: CPIAUCSL seasonally adjusted CPI-U index, existing loader's 12-month percent transformation | percentage points of YoY inflation |
| Unemployment | `unemployment_sa`: UNRATE seasonally adjusted U-3 rate | percentage points |

The CPI identity deliberately differs from the NSA CPIAUCNS prototype. Existing
loader/registry behavior is not silently replaced. Data comes through the
existing chart workspace (Yahoo HTTP and public FRED CSV for its special cases),
not the earlier yfinance/BLS wrappers. Economic month-start dates are reference
dates, not releases. No vintages or causal explanations are inferred.

Market bars dated today are excluded using UTC on Today. Weekday calendars
conservatively introduce holiday gaps rather than bridge missing sessions.
Staleness warnings use >4 days for market series and >60 days for monthly
series; these are heuristics rather than release-calendar guarantees. Futures
roll discontinuities remain a provider limitation. Long trends clipped by the
three-year scan boundary can acquire a new episode anchor.

## Gold to saved research

1. Today → significant Gold discovery → Investigate.
2. Existing workspace opens with Gold, a default related series, requested
   history and the discovery observation marker. Context is encoded in validated
   query parameters, so the link remains usable across a new session.
3. Select dollar and silver in Related comparison queue. Switching the active
   pair keeps Gold, the dates and observation; no manual reconstruction.
4. Save each pair through the existing Save this comparison action. Source CSVs
   and existing evidence fields are unchanged; optional `discovery` metadata
   records the signal/observation/queue within the same version-1 record.
5. My Research opens either comparison with its original evidence. Existing
   records without discovery metadata remain readable and untouched.

Normal Investigate visits retain their existing three selectors. Discovery
visits show a Discovery window rather than misleadingly applying a new date
preset. Invalid handoffs fall back to the standard workspace. Relationships
have economic rationales and are not causal claims. Real yields and breakevens
are not registered in this Streamlit comparison catalogue; the UI says so and
does not present nominal 10Y yields as a substitute. No relationship engine or
changes to Ask's existing explanatory behavior are included.

## Validation

Baseline on exact Python 3.12.15 with all root/backend/dev requirements:
331 passed, 5 live checks skipped; existing lint passed; pip check passed.
Root/backend dependencies resolved together with OpenAI 2.54 (<3), preserving
the live backend's bound. Initial test collection attempted before installation
completed was rerun after completion; the baseline above is the completed run.

Final local regression: **345 passed, 5 live checks skipped**; lint and pip check
passed. Integration tests cover prior-only distribution comparisons, gold -2.5% against
different volatility, unemployment persistence, inflation percentage points,
zero/short history, gaps/frequency errors, numerical ties, episode grouping,
significant reversals, ranking, CPI identity, provider isolation and the complete
Today → gold → dollar/silver queue → save both → My Research → saved evidence
workflow. Test data are controlled fixtures only; production has no fake-data
fallback. The existing complete pytest suite includes backend/Ask, research
storage, provider transport and page compatibility tests. CI's inherited Linux
Python and frontend jobs are required before review.

Live verification separately retrieved all five scanner datasets successfully:
market data through 2026-10-23 and economic reference periods 2026-09-01. This
uses public FRED CSV, not authenticated FRED. Opt-in existing live-provider tests
passed ECB's three checks plus Eurostat sentiment; authenticated FRED skipped
because its key is absent. No paid OpenAI call or Redis-backed check was made.

The unchanged frontend installs from its frozen lockfile and compiles locally,
but Windows standalone packaging fails with EPERM when creating symlinks.
Do not misreport that local build as passing: the inherited Ubuntu frontend CI
job is the build gate. Existing non-failing deprecation warnings remain.

## Deployment and outstanding limitations

This PR targets redesign-ui and is a separate selective integration, not a merge
of #5/#6. Review against the live base and require green Python/lint/frontend CI.
Do not merge/deploy automatically. No Render runtime/start/branch/auto-deploy
settings were copied or modified. Actual service settings must be checked by
the owner before an approved release: the existing manifest still names main,
while the live service follows redesign-ui according to the deployment audit.

Keep existing API/frontend services, CORS/API URL configuration, AI opt-in/model
settings, Redis configuration and credentials unchanged. Production deployment
must validate the combined root/backend dependency constraints and its selected
runtime, including providers and actual Ask endpoints. Server-local research and
optional scanner SQLite are not durable on an ephemeral Render filesystem;
existing export warnings remain, and no paid storage was provisioned.

Exact exchange/release calendars, authenticated provider/model behavior, Redis
integration, point-in-time validation and broader event benchmarks remain
unverified/deferred. This is a discovery/investigation integration, not a causal
research or prediction engine.
