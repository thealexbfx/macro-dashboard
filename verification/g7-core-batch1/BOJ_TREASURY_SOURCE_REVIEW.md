# G7 Core — US Treasury implementation and Japan source discovery

All entries remain development candidates. Identity/short sample, historical continuity, release vintages, commercial rights, export and production are **separate** gates. HTTP success is not production approval.

## New implementation: US nominal ten-year benchmark yield

- Country mapping: `G7-US-23`
- Original publisher: US Department of the Treasury
- Publisher official identifier: Atom XML field `BC_10YEAR` in the `daily_treasury_yield_curve` dataset.
- Official data feed documentation: https://home.treasury.gov/treasury-daily-interest-rate-xml-feed
- Discovery/methodology: https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics
- Retrieval: `GET https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month=YYYYMM`. Only bounded current-month XML response, no historic coverage.
- Value: nominal par yield expressed in percent for a constant maturity of 10 years. It is NOT the actual traded yield of one specific benchmark note, a zero-coupon yield or a 10-year TIPS real yield.
- Published rates use market quotations; independent third-party rights/provenance assessment remains PENDING even though published by Treasury.
- Historical verification, holiday gaps, vintage snapshots, methodology and earliest observations remain PENDING.

The XML adapter validates the expected Treasury feed field and numeric dated observations. It must remain UNRESOLVED when XML is absent or does not contain the required ten-year field. A new hosted audit is required before counting the mapping as recent-sample VERIFIED.

## Japan discovery — important new official capability (February 2026)

The Bank of Japan announced a **public time-series API on February 18, 2026**. This changes the earlier assumption that Japanese official time-series retrieval necessarily requires an API registration key.

- BOJ primary publisher announcement: https://www.boj.or.jp/en/statistics/outline/notice_2026/not260218a.htm
- API documentation: https://www.stat-search.boj.or.jp/info/api_manual_en.pdf
- BOJ time-series API host: `www.stat-search.boj.or.jp`
- API forms: `/api/v1/getMetadata` (discover database-specific codes), `/api/v1/getDataCode` (retrieve a known code), `/api/v1/getDataLayer` (retrieve layer-specific data).

**None of the Japan core country mappings are configured yet.** Before adding a Japan policy mapping, establish the precise official monetary-policy measure (policy target vs uncollateralized overnight call-rate actual), a publisher database and exact code, frequency, units, cessation/transition history, and returned metadata. Do not substitute a market overnight quote for a policy target silently. Likewise CPI, unemployment, GDP and 10-year yields require exact original-publisher IDs and rights checks.

The Statistics Dashboard API is another publicly available no-registration source, but its 19-digit indicator identifiers must be found via official metadata discovery and the original survey/provenance recorded. Source: https://dashboard.e-stat.go.jp/en/static/api?language=en

## Remaining original-publisher US mappings

- US `G7-US-01` real GDP: BEA chained-dollar quarterly GDP definition and API access; verify API credentials/terms and current reference year before implementing.
- US `G7-US-22` policy rate: choose specific Federal Reserve policy-rate target or upper/lower bound. Do not substitute FRED effective federal funds or a vendor proxy for the announced target without documenting that choice.
- UK/Japan/continental GDP and 10-year yields: not yet implemented.

**Next publisher implementation priority**: search the BOJ `getMetadata` API and official national source tables for exact Japanese codes, implement independent original-publisher metadata checks, and add the vetted mappings to the JSON registry. Do not request secret credentials in a public Actions workflow.

All rights reviews PENDING; all production approvals NOT_APPROVED; no DB writes/deployments/schedules.

## Additional BOJ database evidence

The BOJ API User Manual's DB-name table identifies `FM01` as **Uncollateralized Overnight Call Rate (average), updated every business day** and `IR01` as **The Basic Discount Rates and Basic Loan Rates (formerly Official Discount Rates)**. These are *not automatically equivalent* to the current monetary-policy target. The next Japan discovery step is the public, read-only metadata endpoint `https://www.stat-search.boj.or.jp/api/v1/getMetadata?format=json&lang=en&db=FM01`, followed by a deliberate policy-target-vs-effective-market-rate decision. Do not use `FM01` for the policy mapping until this distinction is explicitly addressed. Source: BOJ API User Manual, section II, DB Names, February 18 2026.

## BOJ FM01 live metadata discovery — audit-ready, not series verification

The dev-only runner now sends a bounded, unauthenticated GET to the BOJ first-party metadata endpoint:
`https://www.stat-search.boj.or.jp/api/v1/getMetadata?format=json&lang=en&db=FM01`.
It produces a separate artifact file `boj_fm01_metadata_discovery.json` containing HTTP status, timestamp, JSON field names/types and array sizes, but **not metadata values or series codes**. Its 2 MiB maximum response, three-attempt bounded retry, 8-second request timeout and read-only request rule avoid blind bulk ingestion. An oversized or malformed response stays a diagnostic error, never a verified mapping.

`G7-JP-22` remains unconfigured. The rate target needs exact definition and code from official metadata and a cross-country concept decision; `FM01` covers the **observed** uncollateralized overnight call rate. Finding the BOJ API response schema does not establish a current policy-target series, historical vintages, commercial rights or any production approval.

Official API manual: https://www.stat-search.boj.or.jp/ssi/docs/info/nme_aphelp_en.html
Official Statistics Dashboard API (other Japanese core indicator discovery): https://dashboard.e-stat.go.jp/en/static/api?language=en

Do not add schedule, production writes or authentication tokens to the audit.
