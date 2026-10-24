# Rebuild validation and handover

MacroLens is now a daily market check and personal economic-question notebook. Navigation is Today, Investigate and My Research. It remains Streamlit.

## Decisions and removals

See PRODUCT_SIMPLIFICATION.md for every previous destination and retained metric. REMOVED_PRODUCT_SURFACES.md lists deleted files and five intentionally retired UI tests. The production entry no longer imports model dashboards, regime displays, placeholder pages or duplicate economic/market page renderers. Approximately 25,000 lines of presentation code were removed. The legacy menu dependency was removed. Data catalogue, pure statistical safeguards and version-1 saved investigations remain. Non-UI model engines and the separate backend/frontend remain for active consumers; refresh loaders were moved to macro_engine/refresh/loaders.py and their imports updated. A static import scan found no retained imports of deleted modules.

PR #2 is merged as 82e14d0d72f59e23c48f9e5fe79c69d54481ba78. This branch begins there, so its alignment, units, exact calendar-month horizons and persistence corrections are inherited, not duplicated or overwritten.

## Retained journeys

Today displays four observed market moves with exact previous/latest observation dates and source, flags observations older than three calendar days, and links to an investigation. It neither invents catalysts nor claims access to a verified economic release calendar. A 10-minute result cache does not suppress displayed observation dates. Provider failures show unavailable rather than fabricated changes. Yahoo close retrieval now uses a bounded verified chart request, avoiding the local database failure seen with the previous loader. Missing rows are preserved. FRED's public CSV supplies the small Treasury overview without requiring a credential.

Investigate starts with a question and two series. One options panel contains sample, hypothesis, transformation and frequency. The first result is a comparison chart, one descriptive finding and coverage. Historical splits, rolling diagnostics and lag scans are optional. Notes remain distinct from calculated evidence. The first finding is not a causal or forecasting claim. Definitions and limitations remain available.

My Research reopens records in the same tab, displays notes and exports durable copies. Local records are server-scoped and can disappear on restart. JSON restore creates a new copy and validates supported fields. Imported snapshots are explicitly unverified until recalculated. Existing version-1 records default to native alignment. Old page links map to a retained workflow with a migration notice; removed model pages do not silently execute in the background. Asset-specific legacy model context is not reproduced.

## Analytical regression examples

Recalculated with retained engines from actual source observations, not hardcoded expected outputs:

| Pair | Valid changes | Full sample | First half | Second half |
|---|---:|---:|---:|---:|
| Gold / US 10Y | 6,435 | -0.159656 | -0.077858 | -0.272153 |
| Gold / S&P 500 | 6,531 | +0.010618 | -0.011836 | +0.042015 |

Gold and US yields use the real exported production source snapshot from the preceding audit; S&P closes were freshly retrieved from Yahoo and paired with that Gold snapshot. Coverage ends October 22, 2026 for yields and October 23 for S&P. Both examples reproduce the reference observations. Gold is a futures closing-price series, not spot or total return. Latest-vintage data can change. Correlation does not establish causation; lag scanning is not predictive validation.

The strict 60-period yield comparison still has 59 warm-up periods, 3,012 incomplete later windows and 3,517 valid estimates. Latest valid is October 9 at -0.305517. No gaps were filled. Existing tests retain unit conversion, missingness, frequency, lag sign, sample size, snapshot reopen/update and export safeguards.

## Tests and browser verification

Local full suite: 324 passed, five explicit opt-in live checks skipped. Five UI tests were intentionally retired with their deleted pages/wrapper; six new product tests cover three-route migration, dated changes and stale data, failure/empty states, restore validation and verified Yahoo transport. One dependency deprecation warning remains. Fatal Python lint, compilation and whitespace checks are release gates. Remote CI status is reported on the PR.

Browser verification rendered Today with real Yahoo/FRED observations, opened My Research, followed its same-tab continuation link and reopened the real production evidence snapshot in the simplified notebook. Screenshots show the default form, overview, library and saved evidence. The available browser surfaces in this turn were desktop; explicit mobile viewport control was unavailable. Responsive CSS wraps navigation on small screens, but a new mobile rendering/screen-reader certification is not claimed. No synthetic values were presented as live observations.

## Limits and deployment

Provider outages, rate limits and revisions remain possible. Missing values are never made into fictitious observations. Market dates are observation dates, not verified publication times. This app is not a point-in-time backtest or calibrated prediction system. Local storage has no account isolation or durable cloud guarantee. No news feed is fabricated. Uploaded snapshots can be user-edited and remain labelled unverified. Exhaustive provider permutations and mobile testing remain follow-ups.

No secrets or production infrastructure were modified. The previously documented Render branch discrepancy is unchanged. This task opens a PR against redesign-ui; it does not merge or deploy.
