# MacroLens dataset suitability and research-quality audit

Checked **30 October 2026**, based on Batch 0 commit
`1bf62919d1395149ffad8b39c0664adfee4d956d`. Audit and disclosure changes only, on
`feature/macrolens-dataset-suitability-audit`; the expansion branch and PR #9 are
not modified. No production database, public/AI/Discovery permissions, data
providers, series identities, calculations, ingestion, hosting or deployment
settings are changed.

## Decision summary

All **30 public IDs** were reviewed: **4 KEEP, 19 KEEP + SUPPLEMENT, 5 FLAG,
2 REPLACE**. These are research-use classifications, not legal permission grants.
REPLACE means a new preferred research series/role under a **new** ID, with the
existing futures ID and saved references retained. No current series is silently
retargeted, removed or disabled.

* Most core macro series are appropriate original government statistics. Their
  limitations concern concept, transformations, seasonal adjustment and vintages,
  rather than a need to abandon a reputable producer.
* Gold and WTI continuations are not good default **spot/physical-price** series.
  Unknown vendor roll mapping also limits investable-futures-return claims.
* Five flags: Yahoo S&P 500 and DXY delivery/lineage/rights; Michigan delivery lag,
  sparse early history and survey-method change; both ICE OAS feeds' rights and
  three-year history. FLAG does not mean the economic concept is worthless.
* FRED is a distributor, not the original producer or a blanket rights grant.
  Some FRED series are Bank-created calculations, not federal public-domain work.
  Current service terms specifically restrict API caching/archive and AI-related
  use. The app uses CSV/export URLs, so confirm service scope or choose a cleared
  producer-native route. Do not assume either automatic permission or a definitive
  legal violation. [Current terms](https://fred.stlouisfed.org/legal/).

## Deliverables

| Output | File |
|---|---|
| A. All 30 datasets: identity, original producer, concept, frequency/units/adjustment, coverage, revisions, rights, research fit and alternatives | [Readable matrix](PUBLIC_DATASET_MATRIX.md), [full structured matrix](PUBLIC_DATASET_MATRIX.json) |
| B. Research-value-ranked additions/replacements, exact comparison identifiers, coverage and existing-plan matches | [Recommendations](recommendations.json), summary below |
| C. Implementable cycle/gold event-study specification | [Event-study specification](FED_GOLD_EVENT_STUDY_SPEC.md) |
| D. Genuine blockers and nonblocking integration lanes | This report and [expansion standard](EXPANSION_QUALITY_STANDARD.md) |
| Same criteria applied to the expansion | [309-entry screen](EXPANSION_QUALITY_SCREEN.json) |
| Original evidence and limited live checks | [Source/rights ledger](sources.json), [26 FRED metadata checks](metadata_verification.json), [four Yahoo metadata checks](yahoo_metadata_check.json) |

The screen covers **309 manifest entries**, including the reviewed public 30,
three private World Bank pilots and 276 other planned entries. It retains all
298 planning references; panels/selections are not falsely expanded into invented
atomic feeds. The other **279** entries remain pending source-specific review.
Prior research is reused from `research/planning/batch0/originals/` and
`catalog/datasets.json`; neither is rewritten.

## Priority case study: what combination answers the question?

**Use official FOMC action timestamps and target states with a licensed,
explicitly timestamped gold benchmark.** Use real yields and broad USD as
complementary context. The present monthly-rate/futures pair is exploratory,
not a defensible event definition plus spot-return outcome.

| Choice | Appropriate role | Material limit |
|---|---|---|
| Current `gold` / GC=F | Explicitly qualified legacy futures-price proxy | Vendor-reported start 2000-08-30; no proven per-bar contract/roll/settlement map. Do not rename it spot or claim a specified rolled strategy return. |
| Licensed London gold PM, AM separately | Preferred daily spot benchmark panels | Loco London unallocated benchmark, not retail premiums or an executable global close; auction time is normally before the FOMC statement. |
| Licensed timestamped spot or a named futures contract | Narrow announcement-window research | Quote/contract identity, timing, rights and no within-window roll must be verified. No universally interchangeable XAU/USD feed. |
| Current `fed_funds` / FEDFUNDS | Monthly funding/policy-regime context | Calendar-month realized-rate average, not the policy target or announcement date. Mean-to-median daily methodology break in March 2016. |
| DFF / NY Fed EFFR | Daily implementation/funding context | Still not an action calendar; business/calendar-day conventions and next-publication timing differ. |
| FOMC documents + DFEDTAR / DFEDTARL/U | Decision calendar plus point/range policy state | Separate announcement and effective dates; do not infer target events or surprises from monthly means. |
| DFII10, optionally DFII5 | Real-yield opportunity-cost context | Checked history begins 2003-01-02; liquidity/term premia remain. A nominal yield or T5YIE is not a real yield. |
| DTWEXBGS | Broad nominal trade-weighted USD context | Checked history begins 2006-01-02; trade weights, revisions and publication clock matter. Not an interchangeable continuation of ICE DXY. |

London PM is normally before a typical 14:00 ET policy statement; documented
normal COMEX settlement is at 13:29–13:30 ET. A same-date price can therefore be
**pre-event**. The primary daily specification uses the last verified pre-event
fix and the next eligible post-event fix, explicitly labelled fix-to-fix. Narrow
reaction estimates require an intraday feed. Historical release times, emergency
events and US/UK daylight-saving weeks must be checked rather than assumed.
[IBA timing](https://www.ice.com/iba/lbma-precious-metals),
[CME rule](https://www.cmegroup.com/tools-information/lookups/advisories/market-regulation/SER-5147.html).

The modern London benchmark changed administration in March 2015. Legacy daily
IBA gold identifiers were removed from FRED in January 2022; World Gold Council
reports historical-data removal requested by IBA in March 2025. Neither is an
unrestricted daily-source workaround. Obtain rights for history, charts, API/
downloads and derived use independently. [FRED notice](https://fred.stlouisfed.org/news/2022/01/ice-benchmark-administration-ltd-iba-data-to-be-removed-from-fred),
[WGC availability](https://www.gold.org/goldhub/data/gold-prices).

For earlier cycles, do not invent real yields before 2003 or broad-dollar values
before 2006. A separately labelled GSW fitted TIPS curve from 1999 and older Fed
dollar indexes can be sensitivity panels, with different methods/coverage. Keep a
larger gold-only sample and smaller balanced-control samples. Contemporary real
yield/USD moves may be policy transmission channels; they are not innocuous
exogenous controls for a causal total effect.

## Ranked additions: proceed in parallel, not one global queue

| Rank | Addition / role | Immediate action and gating |
|---|---|---|
| 1 | Official timestamped FOMC calendar | Curate scheduled, no-change and emergency decisions; reconcile statements and implementation notes. |
| 2 | Licensed gold spot benchmark, PM/AM separate | Resolve benchmark history and actual rights; this lane may wait without blocking government sources. |
| 3 | Target state package: DFEDTAR, DFEDTARL, DFEDTARU | Three atomic series; retain the 2008 point/range transition and effective dates. |
| 4 | DFII10 / DFII5 real yields | Two maturities; source-native H.15/Treasury mapping and release-time checks. |
| 5 | DTWEXBGS broad USD | Verify H.10 route, weights and timestamps; older baskets stay separate. |
| 6 | DFF daily effective rate | Already ML-031 / `fred_f007c60ecacde1bf5fb2`; reuse its plan identity, not `fed_funds`. |
| 7 | DGS2 nominal two-year yield | Already ML-033 / `fred_fb83bc372b6c55d48647`; no duplicate catalog entry. |
| 8 | EIA Cushing WTI spot / DCOILWTICO comparison key | New spot ID; do not rewrite `wti`. Validate the producer API selector. |
| 9 | BLS ECI wages and compensation | Choose exact scope/atomic series; quarterly, not interpolated monthly. |
| 10 | Census construction put-in-place spending | Continue existing TTLCONS / ML-049 and public-works component plans. Dollars spent are not tonnes consumed. |

Real-time macro surprise studies additionally need original release vintages and
expectations. Existing latest-revised observations cannot supply that information
merely by shifting the date. Do not add a paid expectations source without approval.

## Genuine blockers

1. **Rights for the actual product/route.** ICE OAS is explicitly pre-approval
   required. No auditable onward grant for the four Yahoo feeds was found.
   London benchmark history needs permission. Freddie Mac has a limited automatic
   PMMS website permission, so do not incorrectly call all PMMS display prohibited;
   verify conditions and API/export/archive scope. Michigan's citation condition
   is not an unrestricted data-product licence. No permissions are changed here.
2. **Event timing and price lineage.** Unknown gold rolls/close times and missing
   historical announcement timestamps prevent a strong narrow-window result.
   Use reviewed documents and a suitable licensed price feed, not assumptions.
3. **Actual coverage and definitions.** ICE's current feed has only three years;
   early Michigan history is sparse; checked PCEC96 delivery begins in 2007. The
   app's 1990 request floor is not a full-history guarantee. Validate producer
   selectors, units and historical method changes for each selected new source.
4. **Source-specific acceptance before publication.** Non-atomic selections,
   undefined fiscal/calendar periods and physical-unit conversions need resolution.
   This is per-dataset work, not a reason to stop unrelated well-defined batches.

Source/service interpretation should be confirmed by the rights owner or qualified
review before public activation. No purchases, provider switches or production
depublication were performed by this audit.

## Safe development improvements and validation

The existing Source & methodology panel now has concise research-use disclosures
for the most easily misinterpreted series, including cached legacy records.
These are static explanatory text keyed by existing IDs. They do not touch
observations, sources, transformations, permissions, saved research or the UI
layout. Existing monthly-effective and continuous-futures labels are retained.

`scripts/build_suitability_audit.py` reproducibly builds the matrix and planning
screen from reviewed notes/metadata; `--check` is read-only and makes no network
requests. The identity baseline and tests protect all 30 original provider IDs,
units/frequencies/adjustments/transformations and all 309 planning entries.

This audit did not read production SQLite or exhaustively reconcile every price/
observation against an original release. Metadata ranges are not gap counts or
proof of price accuracy; no event-study return or causal estimate is claimed.
