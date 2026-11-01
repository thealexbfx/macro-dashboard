# Suitability gates for the expansion

Apply these to each **atomic** series. Existing source research and its provenance
are reused; a manifest entry is not independent verification or a rights grant.
`EXPANSION_QUALITY_SCREEN.json` covers all 309 entries with source-family prompts,
the 30 reviewed classifications and explicit pending review for the other 279.
It does not invent 279 final KEEP/REPLACE decisions from provider names.

## Required review record

1. **Question and concept:** define the estimand and population/instrument. State
   at least one appropriate use and one attractive but invalid interpretation.
2. **Identity:** original producer, distributor, exact atomic selector including
   SDMX dimensions, geography, unit multiplier, adjustment, currency, index base,
   valuation, benchmark grade/location and stock/flow/rate/price distinction.
3. **Time:** daily/business/weekly/monthly/quarterly/annual/event frequency, native
   fiscal/calendar labels, source timezone, observation/release/effective times
   and reference-period start/end. Treat publication and retrieval independently.
4. **History:** check first/last returned nonmissing observations, interior gaps,
   known closures, changing definitions and availability limits. Preserve missing
   versus zero/negative observations. Metadata endpoints alone do not prove a
   continuous comparable history.
5. **Revisions:** identify first-release/final/vintage/correction conventions,
   historical benchmark changes and deletion/truncation behaviour. An incremental
   tail refresh cannot discover an old revision without scheduled bounded checks.
6. **Research presentation:** native levels versus growth/annualized rates, bp
   versus percent returns, totals versus per-capita and nominal versus real.
   Resampling or transformations require an explicit reviewed derived definition.
7. **Permissions:** original owner, transport/service, display, export/API,
   storage/archive and derived/model/AI uses each need evidence and attribution.
   Do not infer approval from public availability, a free API key or an upstream
   catalog licence. Current FRED-route review is separate from government-data
   rights; see the source/transport profiles in `sources.json`.
8. **Implementation:** fixture and producer sample agree on units/dates/signs,
   duplicates and revisions; prove bounded backfills, source hashes/cursors,
   dataset-specific completeness, retries, restart/restore and resource headroom.
9. **Decision:** KEEP, KEEP + SUPPLEMENT, REPLACE or FLAG, with the reason tied to
   the research question and separate rights status. Reassess when definitions,
   source terms or methodology change; do not silently amend source history.
10. **Publication:** use independent display/AI/Discovery gates. Availability or
    an ingestion success is not sufficient. New entries remain private/denied/
    excluded until their specific approvals and activation plan are reviewed.

## Source-family checks

* **International macro:** harmonized versus national concepts; fixed versus
  changing euro-area composition; PPP versus market-exchange-rate values; GDP
  growth annualized versus ordinary q/q; current versus constant prices. German,
  French and Italian totals are not automatically additive to changing EA totals.
* **OECD/Eurostat:** lock the entire selection/dimension/adjustment/unit key and
  structure version. Revised structures or similar labels do not prove identity.
* **UK/ONS:** chain-volume versus current prices; monthly proxy versus quarterly
  aggregate; UK versus GB/England geography and publication vintages.
* **Japan:** fiscal year label/start and calendar year are different. Retain
  source-defined quarterly and annual periods rather than relabelling January.
* **China:** cumulative/YTD versus single-month values; January-February combined
  publications; nominal/real growth, published rates and definition breaks. Do
  not split a combined publication into fictitious January/February observations.
* **Energy/metals/agriculture:** benchmark grade/location, spot versus futures,
  contract/roll rules, inventory snapshot dates, production/consumption flows,
  gross/net trade, calendar months and unit/heating-value/density conversions.
  Prices cannot stand in for physical supply-demand quantities.
* **Construction/materials:** starts/authorizations/completions versus spending,
  cost/bid/price indexes versus output volumes; SAAR dollars versus physical
  tonnes; cement versus clinker, aggregates versus sand/gravel, asphalt binder
  versus mixture. National series do not measure Missouri/St. Louis or UK-local
  conditions without the correct geography and scope.
* **Local/regional:** state/metro/county/city definitions, independent St. Louis
  city versus county, suppression, experimental status and changing geographic
  classifications. MoDOT bid prices are not a census of materials consumed.
* **Financial feeds:** price versus total return, quote/settlement time, calendar,
  historical backcasts, constituents, methodology, rights and provider corrections.

## Changes without breaking saved research

Keep every existing public ID. Pure explanatory disclosures may improve clarity
without changing the selected series. A switch of economic object—spot/futures,
target/effective, daily/monthly, SA/NSA, new basket or material benchmark—requires
a new canonical ID and an explicit relationship/migration note. A transport-only
change still requires reviewed equivalence, source version/provenance and update
disclosure; it is not an invitation to overwrite source hashes or past captures.

Retired or unavailable IDs retain metadata and saved references. No automatic
alias may silently select a different surviving source. Historical versions and
source revisions remain auditable and missing cells remain missing.

## Parallel work lanes

* **Proceed with ordinary source-specific checks:** original government macro,
  target-rate, yield, physical-energy and construction series with exact selectors
  and cleared producer routes. Continue private fixture/integration work under the
  existing approvals; this audit does not authorize new ingestion itself.
* **Resolve definitions first:** selection panels, combined periods, unclear units,
  index/benchmark changes and ambiguous regional scope. Other datasets proceed.
* **Rights-dependent lane:** proprietary benchmarks, exchange/vendor history,
  surveys and underlying third-party inputs. Source-specific approvals, not a
  global catalogue halt. Do not purchase, scrape around restrictions or activate
  public/AI use to overcome an unanswered rights question.

No manifest, dataset rights, ingestion schedule, migration or production resource
is changed by this quality screen. Real-history/partition-depth and disk-growth
profiling remains part of each later bounded batch's acceptance criteria.
