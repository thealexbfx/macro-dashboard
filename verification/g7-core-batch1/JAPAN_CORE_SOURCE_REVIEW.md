# Japan G7 core official-source review — November 2026

**All five Japan country mappings are UNCONFIGURED. No production approvals.** The BOJ published current guideline and its observed daily call rate are distinct concepts, requiring separate evidence streams.

## G7-JP-22 — BOJ announced policy target

**Current guideline source:** Bank of Japan official homepage (https://www.boj.or.jp/en/index.htm) states that it will encourage the uncollateralized overnight call rate to stay around **1.25 percent** (observed as of November 2026). **Original monetary policy decision source:** BOJ's *Change in the Guideline for Money Market Operations*, Monetary Policy Meeting of **September 18, 2026**, listed under https://www.boj.or.jp/en/mopo/mpmdeci/state_2026/ and included in the minutes at https://www.boj.or.jp/en/mopo/mpmsche_minu/minu_2026/g260918.pdf . The BOJ announcement is an event-style target decision; it is *not* a daily observed interest-rate time series.

New current-state probe: fetches only the original BOJ homepage over bounded read-only HTTPS, accepts exactly the formal guideline sentence and a rate in percent, and writes **boj_policy_target_snapshot.json** in the disposable audit artifact. This is **CURRENT_SOURCE_SNAPSHOT_ONLY**, with no verified effective date, history, release vintages, or production eligibility. Target mapping G7-JP-22 **remains unconfigured**, even if the probe succeeds. A historical event-series implementation will require a dedicated publisher statement archive parser, exact decision dates and effective dates, policy regime changes, and source-page receipts per event. It must never silently borrow the daily actual overnight rate.

Separate actual market rate: FM01 / STRDCLUCON, the **observed** uncollateralized overnight call rate average from BOJ getDataCode. Recent-sample verification previously passed on GitHub. This is related, but not equivalent to, the policy target.

## G7-JP-07 — headline CPI (Statistics Bureau of Japan)

Original: https://www.stat.go.jp/english/data/cpi/ and https://www.stat.go.jp/english/data/cpi/1588.htm .

**Critical change:** The Statistics Bureau transitioned monthly CPI to **2025-base** on **August 21, 2026**. The national all-items price index (2025=100) must be selected with its exact seasonality, geography and index-vs-12-month-change definition. Any downloaded 2020-base series is a different reference base, NOT an interchangeable current 2025-base series; documenting rebasing and historical linking is required. Official e-Stat and Statistics Dashboard have different code systems. Specific current 2025-base dashboard indicator ID/table value not yet established: **UNCONFIGURED**.

## G7-JP-11 — unemployment (Statistics Bureau Labour Force Survey)

Original e-Stat dataset: https://www.e-stat.go.jp/en/stat-search/files?stat_infid=000031831358 (Labour Force Survey, monthly **seasonally adjusted and original**, nationwide unemployment rate in historical table 1-a-1). Statistics code `00200531`. The table contains multiple populations, series and time spans; a table identifier alone does not establish a unique seasonally-adjusted unemployment rate API value. Exact API table/element identifier and baseline coverage remain **UNCONFIGURED**.

## G7-JP-01 — real GDP (Cabinet Office, Economic and Social Research Institute)

Original Cabinet Office releases: https://www.esri.cao.go.jp/en/sna/data/sokuhou/files/2026/toukei_2026.html and https://www.esri.cao.go.jp/en/sna/menu.html .
Official e-Stat table: https://www.e-stat.go.jp/en/stat-search/files?stat_infid=000040501955 (table: *Real Gross Domestic Product (seasonally adjusted series)*, **Amount**, second preliminary estimate, Apr–Jun 2026 release September 8 2026). It is different from the similarly named *Changes from previous term* table. E-Stat API requires an app ID; a CSV can be obtained publicly but needs a **strict column, unit and series definition audit** before parser registration. Cabinet Office real GDP reference year is **2020** in the 2026 release. Real expenditure-side GDP series ID/CSV schema not yet established: **UNCONFIGURED**. Revisions of seasonally adjusted history on each release must be tracked.

## G7-JP-23 — 10-year sovereign yield

Original issuer/publisher candidates include Japan Ministry of Finance reference-bond government securities yields and BOJ government-bond market yield statistics. Need exact yield definition (benchmark cash 10-year vs constant-maturity zero coupon), source type, series metadata and third-party quote/redistribution licenses. No unproven market proxy configured.

## Release controls

1. Exact original-publisher source and typed series identity
2. Live read-only retrieval with receipts, bounded data and tests
3. Full historical coverage / revisions / vintage methodology
4. Commercial rights, attribution, export and display including third-party quotes
5. Separate production approval

**No source page read grants commercial redistribution permission.** No scheduled, credentialed or production deployment actions.
