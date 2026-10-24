# Discovery Radar

The integration pass in [release-readiness.md](release-readiness.md) supersedes
the original ranking defaults, retry/cache policies and deployment checklist
below. Review that document before merging or deploying.

## Compatibility gate for PR #5

Installed the existing requirements.txt in a workspace-only environment (Python
3.12, pandas 3.1, Streamlit 1.66). All fourteen Phase 1 tests pass. Baseline
Streamlit AppTest reached the existing OpenAI credential stop with no exception.
OPENAI_API_KEY, FRED_API_KEY and BLS_API_KEY were absent. Full credentialed
website/Ask MacroLens verification is blocked, not certified. The current Render
Python 3.10 dependency resolution was not exercised: requirements are unpinned
and config.py already uses union annotations. No dependencies were added.

## Workflow

Open `?page=DiscoveryRadar` from Research navigation. Provider results are cached
for 30 minutes, with an explicit refresh. Defaults show the five highest-ranked
distinct datasets in the last 90 days. Category/type/date filters precede ranking.
Each dataset contributes at most one result. This deliberately avoids one asset
dominating the default view. No-match and provider-failure states are explicit.

Investigate retains the selected observation in session state, displays its
history with an observation marker and full statistical evidence, then lists
curated relationships with non-causal rationales. Multi-select related series
and Begin comparison. Selection and date bounds persist across reruns. Comparison
uses shared-date native-unit panels in components.charts, without joining or
filling different frequencies. The repository had shared plotting functions but
no existing multi-series comparison flow; this adds the smallest reusable chart
extension rather than replacing any page. Ask MacroLens code remains intact.
Radar alone can load without an OpenAI key; other routes keep their existing gate.

## Real data and limitations

Initial universe: GC=F gold futures, BTC-USD, ^GSPC, BLS unemployment
LNS14000000 and CPI CUUR0000SA0. CPI YoY matches monthly periods with a 12-month
lag, including leap years; differences in rates remain percentage points.
Related FRED series DFII10/T10YIE and Yahoo DX-Y.NYB/SI=F use existing adapters.
Production has no fixture/demo fallback. Missing or failed datasets show an
unavailable message. FRED needs the existing key; BLS can attempt unregistered
requests. Provider caches may return stale data. Latest observation dates are
shown; >4-day market and >60-day monthly ages trigger heuristic stale warnings.
These limits do not claim release-calendar validation.

Today's UTC bars are excluded. Weekday calendars conservatively treat holidays
as gaps rather than calculate a false adjacent daily return. This may suppress
a legitimate post-holiday signal. Futures roll discontinuities and aggregate
crypto pricing remain provider limitations. Reference dates are not availability
dates. No historical-vintage or contemporaneous-release backtest is claimed.
Signals are recomputed from retrieved histories, without adding a background
service or requiring a writable production database. Phase 1's durable scanner
store remains available separately.

## Verification

18 automated tests pass: the original fourteen plus provider failure isolation,
distinct ranking/filtering, curated registry integrity/native-frequency panels,
leap-year CPI transformation, and a Streamlit investigation/comparison workflow.
Tests use controlled fixtures only in tests, clearly separated from production.
Baseline AppTest startup stopped on missing OpenAI credentials. Radar AppTest
startup reaches the real-provider page without an OpenAI key. Live economic
providers returned HTTP 503 in this environment; credentialed FRED and economic
success paths remain unverified. No deployment or merge was performed.

## Phase 3

Exact exchange/release calendars, source vintage envelopes, revision retractions,
broader historical quality benchmarks, durable user research state, statistical
relationship detection and advanced research tools. The current relationship
registry is a curated research aid, not an estimated causal model.

Live workflow verification: Streamlit AppTest opened the actual app.py Radar
route with real Yahoo history, selected Gold futures, inspected the evidence,
selected gold/dollar/silver, and rendered comparison without exceptions. Dates
2023-10-25 through exclusive 2026-10-24 and all three keys were preserved.
The only warnings were the two BLS HTTP 503 failures; no synthetic data was
substituted. FRED comparisons remain blocked by absent credentials. This is a
runtime interaction test, not a browser screenshot/visual sign-off.
