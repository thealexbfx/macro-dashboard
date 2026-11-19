# G7 fundamentals coverage

This checklist covers three headline concepts for each G7 economy. IDs are
existing release catalogue IDs or private development preview IDs. The
[194-ID and official capture rehearsal](https://github.com/thealexbfx/macro-dashboard/actions/runs/44001786044)
verified the existing release definition and staged private coverage in a
disposable environment. Legacy US CPI and unemployment observations in that
rehearsal were synthetic fixtures. Ranges below use the first and latest
non-null reference periods from the captured sources. These dates describe
observations. The French table separately lists the publisher update dates.

| Economy | Headline consumer prices | Real GDP level | Unemployment |
| --- | --- | --- | --- |
| Canada | Statistics Canada, `ca_cpi_all_items_nsa`, private, Jan 1914 to Oct 2026 in the separate CPI audit | Statistics Canada, `g7_ca_01`, private, quarterly expenditure GDP at market prices in chained 2017 dollars at annual rates, 1961 Q1 to 2026 Q2 | Statistics Canada, `g7_ca_11`, private, Jan 1976 to Oct 2026 |
| France | Eurostat harmonized HICP, `eurostat_2591546ccb87a306e904` (Jan 1996 to Oct 2026). INSEE national CPI `g7_fr_07` added to private staging | Eurostat country series, `eurostat_eca8a799de8d6687fe33` (1980 Q1 to 2026 Q3). INSEE backfill pending | Eurostat monthly, `eurostat_61686fe8fdc9577e6d47` (Jan 1983 to Sep 2026). INSEE quarterly, France excluding Mayotte, `g7_fr_11` added to private staging |
| Germany | Eurostat harmonized HICP, `eurostat_6545d7d4eb72cd90a2b8` (Jan 1996 to Oct 2026). Destatis national CPI backfill pending | Eurostat country series, `eurostat_e4b0591cf148660f3349` (1991 Q1 to 2026 Q3). Destatis backfill pending | Eurostat monthly, `eurostat_37c229cd537e5fa533bb` (Jan 1991 to Sep 2026). Original national history pending |
| Italy | Eurostat harmonized HICP, `eurostat_8f5e1320615623acdebb` (Jan 1996 to Oct 2026). Istat national CPI backfill pending | Eurostat country series, `eurostat_6e1c74c102959c0ded7b` (1996 Q1 to 2026 Q3). Istat backfill pending | Eurostat monthly, `eurostat_c0fc01ed5efaf8a07abd` (Jan 1983 to Sep 2026). Istat backfill pending |
| Japan | Statistics Bureau/e-Stat, `jp_cpi_all_items_2025_nsa`, private, Jan 1970 to Sep 2026 in the CPI audit | Cabinet Office/ESRI, `g7_jp_01`, private, quarterly chained 2020 yen at annual rates, 1994 Q1 to 2026 Q2 | Statistics Bureau/e-Stat, `g7_jp_11`, private, Jan 1953 to Sep 2026 |
| United Kingdom | ONS D7BT, `ons_24c4972dca3a5b1bbe32` (Jan 1988 to Sep 2026), monthly | ONS ABMI, `ons_a007e11b21ed0f67ccf1` (1955 Q1 to 2026 Q2), quarterly chained volume | ONS MGSX, `ons_24df6f5df34ca52bac40` (Feb 1971 to Jul 2026), monthly publication of rolling three-month estimates |
| United States | BLS series via FRED, `cpi_nsa` (Jan 1913 to Oct 2026); direct BLS history audit pending | BEA original workbook T10106-Q/A191RX, `fred_8d3240bb6b5eae523737` (1947 Q1 to 2026 Q3) | BLS U-3 via FRED, `unemployment` (Jan 1948 to Oct 2026); direct BLS history audit pending |

After the French captures, 12 of 21 concepts have original-publisher history
evidence, seven have harmonized Eurostat histories as the current coverage,
and two use legacy mirrors pending a direct BLS history audit. The original
Canadian quarterly GDP table stores quarter labels as the quarter-start month.

The ONS, BEA and Eurostat entries above are approved in the repository’s
opt-in refresh policy. The Canadian and Japanese CPI pilot has its own
development refresh path. Other private entries currently refresh by explicit
publisher capture.

## French national backfills

| Mapping | Publisher series | Coverage in captured file | Valid | Explicit nulls | Publisher update |
| --- | --- | --- | ---: | ---: | --- |
| G7-FR-07 | [INSEE 011814630](https://www.insee.fr/fr/statistiques/serie/011814630) | Jan 1996 to Oct 2026 | 370 | 0 | 2026-11-13 |
| G7-FR-11 | [INSEE 001688527](https://www.insee.fr/fr/statistiques/serie/001688527) | 1975 Q1 to 2026 Q3 | 207 | 0 | 2026-11-10 |

The capture records the current SDMX vintage and preserves its observation
status and revision markers. Historical release timestamps require separate
verification. National CPI, HICP, quarterly INSEE unemployment and monthly
Eurostat unemployment keep distinct identities. Refresh
currently runs on demand through the isolated capture workflow. No catalogue
release grant was added. Both rights entries remain pending for paid display,
export and external AI use. [INSEE’s legal notice](https://www.insee.fr/en/information/2409130)
lists conditions for eligible data, including source credit, the last update
date when known, and preserving the meaning of the information.

The next backfill targets are Destatis and Istat headline CPI, followed by
remaining original GDP and labour sources and direct BLS verification.

## Validation

- [Hosted browser walkthrough](https://github.com/thealexbfx/macro-dashboard/actions/runs/44011412204)
  verified the France–Canada CPI comparison, save and reopen, and Ask evidence
  with a direct source link. Discovery eligibility for the private histories
  remains withheld.
- The refresh validator now hashes ordered rows incrementally. With 50,000
  synthetic observations, peak Python allocations measured by `tracemalloc`
  fell from 30,876,248 bytes to 2,886,546 bytes. The old and new input and
  stored-data hashes matched. This measurement covers the validator's Python
  allocations. The full application and SQLite file cache are covered by the
  separate [hosted capacity run](https://github.com/thealexbfx/macro-dashboard/actions/runs/44011412227).

For the matched 164-series, 768 MiB synthetic benchmark, the
[baseline](https://github.com/thealexbfx/macro-dashboard/actions/runs/44001786031/job/133767384874)
and [updated run](https://github.com/thealexbfx/macro-dashboard/actions/runs/44011412227/job/133799043429)
both reached the container memory limit with zero out-of-memory kills.
The baseline recorded 16 HTTP 503s in 3,864 requests. The updated run recorded
22 in 3,792 requests. At the final sample, the updated container reported
563 MiB of file-backed memory and 187 MiB of anonymous memory. The isolated
validator improvement alone has not verified application headroom.

The [213-dataset hosted rehearsal](https://github.com/thealexbfx/macro-dashboard/actions/runs/44453307354)
passed at commit `4e5a96d`. It preserved all 194 public IDs, read 19
private histories containing 41,820 observation records, checked 78 denied
public requests before and after the preview, and verified backup/restore
and the saved-research sentinel. The legacy cache used synthetic load fixtures.
The G7 preview imported the retained six-series CPI audit. It does not establish
that all series are current to the latest publisher release.

The next refresh change restricts proof-compaction lookups to their dataset,
using the existing observation index. A 164-dataset synthetic query benchmark
returned the same 11 obsolete generations with approximately 72,500 SQLite
execution steps versus 7,872,400 before. Full application measurements remain
necessary to establish the effect on resource use and API availability.

The first matched hosted trial with the dataset-scoped query completed the
164-series, 512 MiB refresh workload in 371.7 seconds, compared with 764.9
seconds in the prior trial. API p95 moved from 609.5 ms to 401.5 ms. Temporary
HTTP 503 responses were 31 of 2,922 requests in the updated trial versus
24 of 3,852 before. Both trials reached the container memory limit with zero
out-of-memory kills. This synthetic workload result supports the query
optimization while leaving availability and capacity acceptance open.
[Updated trial](https://github.com/thealexbfx/macro-dashboard/actions/runs/44453764941/job/135323729286)
and [prior trial](https://github.com/thealexbfx/macro-dashboard/actions/runs/44011412227/job/133799043140).
