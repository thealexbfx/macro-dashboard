# G7 Core — UK implementation and Japan/US publisher discovery

Status: DEVELOPMENT CANDIDATES ONLY. No new hosted checks performed as of this document. Production approval remains NOT_APPROVED; commercial rights PENDING.

## Implemented UK candidate checks

| Mapping | Original publisher | Candidate | Semantic safeguards |
|---|---|---|---|
| G7-GB-07 | ONS | D7BT, MM23, `CPI INDEX 00: ALL ITEMS 2015=100` | Index level, not 12-month inflation rate; do not substitute CPIH |
| G7-GB-11 | ONS | MGSX, LMS, 16+ seasonally adjusted unemployment | Labour Force Survey rate; published monthly but estimate covers rolling three-month periods |
| G7-GB-22 | Bank of England | IUDBEDR official Bank Rate | Daily rate level; distinguish from SONIA / market rates |

Official ONS series pages:
- https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/d7bt/mm23
- https://www.ons.gov.uk/employmentandlabourmarket/peoplenotinwork/unemployment/timeseries/mgsx/lms
- ONS time-series `/data` JSON format on these original publisher routes.
Bank of England:
- https://www.bankofengland.co.uk/boeapps/database/Bank-Rate.asp
- https://www.bankofengland.co.uk/boeapps/database/help.asp (CSV layout and historical-data caveats)

Before acceptance: execute read-only GitHub-hosted audit, confirm exact series identity/units/periods from receipts and check metadata consistency. Not all fields are independently represented in the ONS /data and BoE CSV responses; any missing body-level ID or title remains a scoped identity caveat.

## Japan — researched; do not activate without exact official indicators

Japan's e-Stat REST API at `https://api.e-stat.go.jp/rest/2.1/app/json/getStatsData` requires an application ID. It must not be simulated or shipped as a production secret. The separately published Statistics Dashboard no-registration REST API at `https://dashboard.e-stat.go.jp/api/1.0/Json/getData` can retrieve official indicator/time/region datasets but requires **exact 19-digit indicator code and appropriate region/time codes**. None of the five Japanese core mapping candidates has yet been confirmed sufficiently to configure. The Cabinet Office GDP release tables are accessible via the official National Accounts/e-Stat listings, but a current exact real chained GDP series, seasonal adjustment, reference year and response schema must be verified before mapping.

Official sources:
- https://dashboard.e-stat.go.jp/en/static/api?language=en
- https://www.e-stat.go.jp/api/
- https://www.esri.cao.go.jp/en/sna/menu.html
- https://www.stat.go.jp/english/data/roudou/index.html
- https://www.boj.or.jp/en/statistics/index.htm

## Remaining US original-publisher connections

US CPI and unemployment are already configured via BLS. GDP (BEA NIPA), monetary policy (Federal Reserve Board), and government 10-year yield (Treasury/FRB) still need publisher IDs, method confirmation and strict terms provenance. Do not quietly use Yahoo Finance, FRED republishing, or unlicensed vendor markets as substitutes for an original-publisher requirement. Some official API channels require registered keys: verify permissions before any credentials are introduced.

## Separate release gates

- **Identity:** exact series ID and publisher definition, unit, adjustments, reference base, geography
- **Access:** bounded live official publisher response with clean immutable evidence
- **History:** earliest observations, gaps, method changes, revisions and continuity
- **Vintages:** actual original release snapshots, not inferred from latest downloaded value
- **Rights:** original publisher license and any underlying third-party market-data restrictions, commercial web display, exports, redistribution and attribution, all independently approved by explicit evidence
- **Production:** NOT_APPROVED until all required checks independently pass

No rights status should change simply because a response is HTTP 200.
