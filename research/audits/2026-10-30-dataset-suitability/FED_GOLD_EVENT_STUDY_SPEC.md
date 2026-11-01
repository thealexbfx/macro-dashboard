# Fed-cycle and gold event-study data specification

Version 1, 30 October 2026. **Specification only: no event-study algorithm, source
registration, ingestion, permission change or result calculation is implemented.**

## Research design and preferred dataset combination

Question: how does a precisely identified gold price behave before and after the
first hike or cut in a defined policy cycle? Report descriptive conditional
patterns, not an automatic causal effect or a profitable strategy.

**Core daily design:** official timestamped FOMC actions + policy target states +
licensed London gold PM benchmark history, with explicit pre/post auction
alignment. AM is a separate sensitivity panel. **Intraday design:** an authorized
timestamped spot feed, or a named single futures contract with no within-window
roll, matched to the policy statement and (separately) press conference.

Add DFII10 real yields and a separately identified broad nominal dollar index as
context; add DGS2 for the expected policy path. Preserve `fed_funds` as monthly
funding-regime context and `gold` as the existing futures-proxy history. Neither
existing ID is retargeted. A licensed explicit futures strategy is a separate
research question, requiring its own roll/financing/collateral convention.

## Why the existing pair is insufficient

`FEDFUNDS` is a calendar-month average of realized overnight rates, not a
decision calendar or target. A mid-month decision blends regimes in one value.
`DFF`/`EFFR` improve implementation frequency but their observation/publication
dates still do not establish the policy announcement. Keep the March 2016
effective-rate methodology break in metadata. [H.15](https://www.federalreserve.gov/releases/h15/),
[New York Fed](https://www.newyorkfed.org/markets/reference-rates/effr).

`GC=F` is Yahoo's front/continuous contract product. The adapter takes
`indicators.quote.close`, not verified exchange settlement, and supplies no
auditable per-bar contract/roll map. Vendor metadata reports 30 August 2000 as
the first trade date; older cycles are outside that reported history. Different
contracts embed different carry/delivery exposures, so the ratio of two chained
closes can include a contract switch. This does not establish the roll return of
a specified investable futures strategy. See `yahoo_metadata_check.json` and
`backend/app/v2/main.py:V2PublicProvider.market_series`.

An `XAU/USD` label alone is also insufficient: OTC bid/ask/mid, location, fixing,
vendor and timestamp conventions differ. Choose and license the exact benchmark.
London fixes are unallocated loco London spot references, not retail physical
premiums, a universal continuously executable spot price, or a total-return asset.

## Timing: do not label a pre-announcement fix as the reaction

London gold auctions are at 10:30 and 15:00 Europe/London. The usual PM fixing is
before a typical 14:00 America/New_York FOMC statement. US/UK daylight-saving
transition weeks alter the offset. Store local time, IANA zone and UTC instant;
use the auction's actual final/publication time where available, not merely its
scheduled start. [IBA](https://www.ice.com/iba/lbma-precious-metals).

COMEX's documented normal active-gold settlement window is 13:29–13:30 ET,
also before that statement time. The 2010 rule change and historical/holiday
exceptions must be versioned; Yahoo close is not established to be that settlement.
[Exchange advisory](https://www.cmegroup.com/tools-information/lookups/advisories/market-regulation/SER-5147.html),
[current exchange times](https://cmegroupclientsite.atlassian.net/wiki/spaces/EPICSANDBOX/pages/457085528/Daily+Settlement+Time+Details).

Therefore a same-date PM fix or settlement may be a **baseline**, not an outcome.
A next eligible benchmark captures a longer interval with overnight/other news.
Label it fix-to-fix, not an isolated 30-minute FOMC shock. Do not infer the bar's
pricing instant from Yahoo's trading-date timestamp or UTC midnight.

Do not assume every historical statement occurred at 14:00: scheduled releases,
older communication regimes, emergency/intermeeting decisions and weekend
announcements differ. Use the original statement and implementation note, not
minutes released later, to establish the event and action.

## Required data contracts

### `policy_action` — one row per decision, including no-change actions

| Field | Requirement |
|---|---|
| `event_id`, `source_event_key`, `source_version` | Stable decision identity; a document correction is a revision, not another event. |
| `announcement_at_utc`, `announcement_local`, `timezone` | Source-supported exact instant; null and an explicit precision/confidence flag when unknown. Never invent 14:00. |
| `effective_from`, `publication_at`, `retrieved_at` | Distinct effective, announcement/publication and retrieval concepts. |
| `scheduled`, `intermeeting`, `emergency`, `decision_type` | Include unscheduled and no-change events; do not select only meetings with large gold moves. |
| `target_regime`, `before_point`, `after_point` | Single-target regime; retain historical uncertainty flags. |
| `before_lower/upper`, `after_lower/upper` | Range regime, both bounds in percent per annum. |
| `lower_change_bp`, `upper_change_bp`, `midpoint_change_bp` | Midpoint is a mechanical summary, not necessarily an announced point-target change. |
| `statement_url`, `implementation_url`, `document_hash`, `evidence` | Exact source, integrity, extracted passage locator and human reconciliation record. |
| `review_status`, `rights_evidence`, `source_flags` | Independent source/timing/permission approval; unknown values remain unknown. |

Official entry points: [current action documents](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm)
and [historical archive](https://www.federalreserve.gov/monetarypolicy/openmarket_archive.htm).

### `policy_state`

Separate point target (comparison key DFEDTAR, 1982-09-27–2008-12-15) and lower/
upper ranges (DFEDTARL/U, from 2008-12-16). The supplied daily calendar-day state
is valid state information, not fabricated market observations. A changed
effective-day value does not identify the preceding announcement timestamp.
Daily realized DFF (from 1954-07-01) and NY Fed EFFR (checked history from
2000-07-03) are separate datasets with different calendar/publication conventions.
Use original-producer delivery or an explicitly approved transport.

### `gold_observation`

Required: canonical dataset ID, original symbol/benchmark, economic concept,
currency, unit (USD per **troy** ounce), bid/ask/mid/fix/close/settlement type,
reference/trading date, actual price instant and zone, publication/retrieval
instants, source version/hash, correction flag and licence scope. A futures row
also needs actual exchange contract, maturity, delivery/roll status and adjustment
method. Keep raw and adjusted continuations separate; never rewrite `gold`.

Store absent records separately from explicit missing values. Distinguish a
scheduled market holiday, provider outage and a genuinely unavailable historical
observation. No forward-fill, interpolation or invented pre-event quote.

### `control_observation`

DFII10/DFII5: original-government inflation-indexed constant-maturity yields,
percent per annum, checked source range from 2003-01-02. They include liquidity/
term-premium effects, not a pure expected short real rate. T5YIE is inflation
compensation, **not** this real-yield control. A separately labelled GSW fitted
TIPS curve begins in 1999 and is revised research-model output, not a backfill
of DFII10. [H.15 comparison metadata](https://fred.stlouisfed.org/data/DFII10),
[GSW source](https://www.federalreserve.gov/econres/feds/the-tips-yield-curve-and-inflation-compensation.htm).

DTWEXBGS: nominal broad trade-weighted dollar, daily labels from 2006-01-02 in
the checked comparison feed. Economic observation and weekly publication clocks
differ. Legacy DTWEXM (1973–2019, major currencies) and DTWEXB (old goods basket)
are separate sensitivity panels, not a continuous extension. ICE DXY has a fixed
six-currency basket/euro concentration; do not relabel it broad USD.
[Fed weights](https://www.federalreserve.gov/releases/h10/weights/default.htm).

The balanced primary control sample cannot start before the latest required
series' actual coverage. Publish a gold-only longer sample and explicitly smaller
control subsets, rather than inventing pre-2003 real yields or pre-2006 broad USD.

## Cycle identification — predeclared, reproducible and revision-safe

Primary announcement study starts in **1994**; older intended targets and
communication conventions are a separate historical stratum. Import enough
pre-sample target history to establish the prior direction. If unavailable, mark
the first in-sample move left-censored rather than claiming it starts a cycle.

1. Order reviewed decisions by announcement instant (or retain a separate
   date-only, lower-precision panel). Reconcile target states/effective dates.
2. Classify hike/cut using the actual point-target change, or consistent movement
   in both range bounds. No-change decisions do not reset direction.
3. First hike is the first positive policy action after a negative-direction
   cycle; first cut is the reverse. A long pause alone does not reset a cycle.
   Sensitivity definitions (for example a 180-day pause rule) must be separate,
   labelled, predeclared alternatives, not tuned to gold outcomes.
4. A change in range width, one-bound adjustment or point-to-range transition
   requires reviewed classification. Retain both announced bounds. Do not call
   a mechanical midpoint difference an exact announced change when that was not
   the policy object. Tag the 2008 transition; allow separate regime results.
5. Keep emergency decisions, reversals, target-regime changes and missing-time
   events visible. Provide inclusion/exclusion reasons, rather than quietly
   deleting awkward episodes. Never use gold prices to determine the cycle.

No event roster or cycle count has been calculated by this audit. Every eventual
row requires official-document reconciliation. Pre-1994 timestamps/intent are
not uniformly reconstructible: [Board historical evidence](https://www.federalreserve.gov/foia/files/20190829-changes-intended-federal-funds-rate.pdf).

## Windows and estimands

For each event let `P[0]` be the **last eligible observed benchmark strictly
before** the announcement, with its actual timestamp retained. `P[1]` is the
first eligible observed benchmark afterward. Negative indices are earlier
source benchmark observations, not filled US calendar days.

* Pre windows: `100*(P[0]/P[-5]-1)` and `100*(P[0]/P[-20]-1)`.
* Post horizons: `100*(P[h]/P[0]-1)`, `h in {1,5,20,60}` eligible source sessions.
* Plot levels relative to `P[0]=100`; retain exact raw source values separately.
  Optionally report log returns only for strictly positive prices. Do not imply
  storage, financing, lease income or transaction costs are included.
* Store both session counts and elapsed calendar time. A known holiday can make
  the next eligible fixing later; an unexplained missing required record produces
  an unavailable window or explicit sensitivity exclusion, not an invisible skip.
* Report sample size and exclusions **per horizon**, including right-censored
  recent events. Longer windows can overlap later policy actions and contain
  unrelated news; flag overlaps and show a nonoverlapping sensitivity panel.

Intraday sensitivity windows can be predeclared as `[-10,+20]` and `[-10,+60]`
minutes around the actual statement. Require a quoted observation within a
documented tolerance (for example 60 seconds) of each endpoint; otherwise mark
missing. The +60 window may include the press conference, so name that exposure.
Do not manufacture a minute-level series from daily gold prices.

For risk context use **pre-announcement** real yields, dollar conditions and
policy state that were actually available by that time. Contemporaneous changes
can be consequences/mediators of policy; include them only in a separately
labelled explanatory/mediation analysis, not as innocuous controls for a total
causal policy effect. A causal surprise design additionally needs independently
reviewed policy-expectation/shock data, often with additional licensing.

First-cycle events are few and clustered. Report individual episodes, median,
mean, dispersion and missingness. Treat cycles as clusters, distinguish scheduled
and emergency events, and predeclare horizons/multiple comparisons. Daily rows
inside one event window are not independent policy experiments.

## Rights and practical implementation

London daily gold benchmark access is a **real blocker**, not a reason to pause
Fed target, government real-yield, dollar or construction integrations. The old
GOLDPMGBD228NLBM route redirects to a removal notice: FRED removed IBA data on
2022-01-31. World Gold Council also reports restricted historical availability
since 2025-03-18; monthly gold averages do not repair daily event timing.
[FRED notice](https://fred.stlouisfed.org/news/2022/01/ice-benchmark-administration-ltd-iba-data-to-be-removed-from-fred),
[WGC](https://www.gold.org/goldhub/data/gold-prices).

Use the Batch 0 native event calendar/observation contracts, immutable source
hashes, checkpoints and per-dataset completeness receipts. Curate action events
in small reviewed files; use bounded incremental producer adapters for daily
states/prices. No automatic publication: underlying rights, transport, website,
API/export and AI uses must be reviewed separately. Cached raw data rights are
not implied by a chart permission. See `sources.json` for the transport issue.

Initial release acceptance, after a separate implementation approval:

1. Every action reconciles with a cited official statement and effective target;
   two independent reviewers/checks confirm cycle boundaries and left censoring.
2. Pricing endpoint timestamps prove the intended pre/post relation, including
   DST mismatches, holidays, weekends, emergency events and older release times.
3. Fixtures cover a pause within a cycle, a reversal, width-only changes, the
   point/range transition, simultaneous/corrected documents and missing prices.
4. No event-window contract roll is hidden. Sensitivity panels never splice
   different benchmarks, currencies, maturities or scopes into the original IDs.
5. Results reproduce from frozen source versions and are labelled descriptive;
   macro covariates use their actual release/vintage availability.
6. Source-specific rights evidence and independent public/AI/Discovery approval,
   bounded Linux resource checks and backup/restore tests pass before release.

Existing saved research and all public/private permissions remain unchanged.
