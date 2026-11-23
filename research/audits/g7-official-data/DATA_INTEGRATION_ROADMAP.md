# MacroLens data integration roadmap

## Decision

A substantial official-source G7 macro catalog is feasible. The first commercial release should concentrate on producer-owned statistics with documented reuse and useful history. The strongest starting evidence covers exact owned BLS, EIA, Federal Reserve Board, ONS, DESNZ, Statistics Canada, Eurostat, Destatis, eligible ECB and e-Stat data. Existing exact BEA, Census and BoE monetary selections have prior scoped reviews worth retaining. Daily sovereign sources are feasible as a separate workstream because long-end history, definitions and rights vary by market. The Yahoo-delivered market instruments and third-party credit spreads, sentiment, mortgage and proprietary index histories need individual rights decisions.

## Minimum viable scope

Target about 40–55 series after validating exact selectors and rights. This is a scope estimate, not an approved or live count.

| Group | Initial selection |
|---|---|
| G7 macro base | Headline prices, a clearly labelled core or exclusion measure where available, real GDP, unemployment, employment and industrial activity. Keep market-specific conventions visible |
| Policy | US, UK, Canada and Japan policy-setting concepts, plus one common ECB policy series. Overnight transaction or effective rates remain distinct |
| Market context | Fed broad dollar, a small set of approved official reference FX pairs, EIA WTI/Brent spot and optional US Treasury curve points once file rights are checked |
| Sovereigns | 2Y and 10Y within-market pairs after daily history, definition and rights checks. Start with the cleanest official curves. Add comparable monthly European convergence rates if daily cross-country spreads remain unresolved |

Agency downloads identified as public have no observed access charge on the proposed route. API registration and quotas are separate from commercial permissions. Infrastructure, source monitoring and review time are additional costs. Proprietary external-display pricing, exchange charges, backfill and derived-data rights remain quote-dependent, so a verified all-in monthly figure is unavailable. The core can be designed without a paid market-data dependency.

## Sequence

1. **Reconcile operations.** Save the live public ID set, compare to the 194-plan set and obtain the Render backend deployment commit and a read-only audit report. Verify each relevant source receipt and history, limits and last successful provider check. Reconcile exact ID and source definition before new registration.
2. **Preserve useful official connectors.** Retain existing native validation and refresh mechanisms for exact eligible BEA, Census, ONS, BoE, DESNZ, ECB, Eurostat, EIA and Federal Reserve selections. For US legacy BLS/BEA/Fed series via FRED, test direct producer parity for units, adjustments, release versions, boundaries and full overlap. Keep the ID for a proven equivalent. Record both source routes, immutable receipts and effective dates. Retain verified revised histories separately from point-in-time vintages.
3. **Fill Canada and Japan first.** Reuse native adapters, benchmark WDS and e-Stat files in isolation, then resolve Canada and Japan GDP, labour, production and policy concepts. Check period conventions and headline definitions. Use one table selector per exact series. Test download limits and schedule without burdening production.
4. **Close national and sovereign gaps.** Retain harmonised Eurostat IDs. Add national CPI/production and other country definitions only when they provide distinct research value. Follow the sovereign source matrix with reproducible per-tenor checks. Keep narrower initial spans where structural breaks or source rights limit history.
5. **Stage display and analytics separately.** Use additive grants for rows that pass rights, definition, completeness, freshness and capacity gates. Rehearse rollback and verify old evidence objects. Track export, display, research automation and external AI independently. Paid feeds come after the exact symbol and entitlement review.

## Catalog structure and stable identity

Use a canonical concept, immutable series ID and explicit variant. Store geography/coverage, definition version, native frequency, adjustment, unit/base, price basis and observation calendar at the series layer. Record producer, retrieval provider, selectors, endpoint version, licence and attribution separately. Keep presentation labels concise with metadata available on demand.

For US CPI, `cpi` is the SA index and `cpi_nsa` the NSA index. Headline YoY based on the NSA index is a labelled transformation of that series. MoM from the SA index is a different transformation. Preserve both stable IDs and store transform parameters with saved evidence. HICP and national CPI receive their own definitions. A successor base or source with materially different history needs an explicit provenance transition or separate series. Existing market IDs retain their meaning and can resolve to historical evidence or an unavailable state if rights require a display restriction.

## Discovery Radar suitability and guardrails

| Method | Suitable inputs and tests |
|---|---|
| Unusual moves, streaks and momentum | Calendar-aware daily yields and FX, or monthly SA changes. Use percentage points/basis points for rates. Count consecutive scheduled observations, flag unexpected gaps. Test valid negative commodity prices and rates |
| Percentile/range and analogues | Long homogeneous segments with matching units, basis, horizon and frequency. Reject rolling windows that cross discontinuities or missing periods. Mark revised data and use real-time vintages for historical claims where possible |
| Divergence and rolling correlation | Predefine economically meaningful comparable pairs, align reference and publication times, compare changes rather than trending levels and test overlap, sample size, influence and stability |
| Potential lead-lag | Require real-time availability dates, multiple-testing controls, aligned horizons, holdout samples and adequate history. Describe associations without implying causality |
| Quarterly, annual, irregular or revised | Quarterly GDP supports longer trends and analogues under vintage checks. Annual population is context. Policy event data should use decision dates and documented unchanged intervals. Flash and final releases carry their own identities |

Record separate observation, reference-period end, source publication, verified retrieval and calculation timestamps. Monitor revisions, missingness, sudden definition changes, holiday coverage, drift, backfills and ongoing source failures. Historical detection must not infer that a data point was available at its reference date.
