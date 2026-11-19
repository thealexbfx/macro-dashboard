# Phase 3 publisher access and expansion handoff

Base `311c665d0a77823ed343223b3c18825e82495c17`. New completed datasets **0**. New historical observations **0**. The six existing development CPI histories remain at 4,278 values and 984 source nulls. [Authoritative coverage matrix](FOUNDATION.md).

## Direct transport result

The read-only probe attempted the Statistics Canada national CPI and core CPI table discovery URLs and the exact e-Stat Japan 2025-base historical listing. All returned `network_or_tls_failure` before discovery. Independent curl checks returned error 6, could not resolve `www150.statcan.gc.ca` and `www.e-stat.go.jp`. The Statistics Canada quarterly GDP browser navigation timed out and then showed a connection reset. No alternate host or proxy was used. The Phase 2 browser capture and mocked refresh tests remain separate from unattended evidence.

Run `python -m scripts.g7_cpi_probe` on an approved development host. It makes one bounded direct request per unique URL, exits nonzero on failures, and on success reports the exact resolved URL, release, artifact hash, validators and verified coverage. Then run the existing `scripts.g7_cpi_refresh` CLI against a dedicated development database. Check its normal next-due run and the next release. Compare the active generation and source receipt before and after an unchanged response, and confirm retained observations across a controlled transport failure. No scheduler or networking change is part of this phase.

## Expansion selection and acquisition gates

| Series | Official product and intended selection | Status and evidence still required |
|---|---|---|
| Canada real GDP | StatCan 36-10-0104-01, Canada, GDP at market prices, expenditure-based, quarterly SAAR, chained dollars | Browser bulk acquisition blocked. Confirm current chain reference year, vector and historical boundary from cube archive. |
| Canada nominal GDP | Same table and concept, current Canadian dollars, quarterly SAAR | Same blocker. Pin separate current-price vector and scale. |
| Canada unemployment rate | StatCan 14-10-0287-01, Canada, total gender, age 15+, seasonally adjusted unemployment rate, percent | Candidate. Confirm vector, periods and flags from full archive. |
| Canada employment level | Same table and population, employment count, seasonally adjusted | Candidate. Confirm vector and publisher scale in thousands of persons. |
| Japan real GDP | ESRI September 8 second preliminary release, expenditure GDP level, real seasonally adjusted, 2020 benchmark | Official landing metadata verified. Download and validate exact level CSV, units and Q1 1994–Q2 2026 claimed table range. |
| Japan nominal GDP | Same release, nominal seasonally adjusted GDP level | Official landing metadata verified. Acquire separate CSV and independently check latest level and scale. |
| Japan total cash earnings | MHLW Monthly Labour Survey, national all-industry total cash earnings per employee, select establishment-size and worker scope explicitly | Research candidate. Pin historical table and level units in yen, review benchmark and sample changes. |
| Japan household expenditure | Statistics Bureau Family Income and Expenditure Survey, monthly nominal consumption expenditure per two-or-more-person household | Research candidate. Verify exact historical file and survey discontinuities. Separate from ESRI private consumption and real expenditure changes. |

For each adapter, record a bounded source artifact and SHA-256, validate exact selectors, month or quarter continuity, explicit missingness, units and comparable publisher anchors, then stage via the existing native generation/revision infrastructure. Observe a second official vintage before marking automated refresh verified. Statistics Canada Open Licence applies to covered tables subject to attribution and other conditions. Exact Japanese product terms and exceptions remain a gate for expansion. There are zero new public grants.

[StatCan GDP](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3610010401) · [StatCan labour](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410028701) · [StatCan licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence) · [ESRI GDP](https://www.esri.cao.go.jp/en/sna/data/sokuhou/files/2026/qe262_2/gdemenuea.html) · [MHLW definitions](https://www.mhlw.go.jp/english/database/db-slms/dl/slms-01.pdf) · [Japan household survey](https://www.stat.go.jp/english/data/kakei/156time.html)
