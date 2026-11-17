# G7 fundamentals coverage

This checklist covers three headline concepts for each G7 economy. IDs are
existing release catalogue IDs or private development preview IDs. The
[194-ID and official capture rehearsal](https://github.com/thealexbfx/macro-dashboard/actions/runs/44001786044)
verified the existing release definition and staged private coverage in a
disposable environment. Legacy US CPI and unemployment observations in that
rehearsal were synthetic fixtures.

| Economy | Headline consumer prices | Real GDP level | Unemployment |
| --- | --- | --- | --- |
| Canada | Statistics Canada, `ca_cpi_all_items_nsa`, private, Jan 1914 to Oct 2026 in the separate CPI audit | Statistics Canada, `g7_ca_01`, private, quarterly endpoints of monthly GDP by industry | Statistics Canada, `g7_ca_11`, private, monthly |
| France | Eurostat harmonized HICP, `eurostat_2591546ccb87a306e904`. INSEE national CPI `g7_fr_07` added to private staging | Eurostat country series, `eurostat_eca8a799de8d6687fe33`. INSEE backfill pending | Eurostat monthly, `eurostat_61686fe8fdc9577e6d47`. INSEE quarterly, France excluding Mayotte, `g7_fr_11` added to private staging |
| Germany | Eurostat harmonized HICP, `eurostat_6545d7d4eb72cd90a2b8`. Destatis national CPI backfill pending | Eurostat country series, `eurostat_e4b0591cf148660f3349`. Destatis backfill pending | Eurostat monthly, `eurostat_37c229cd537e5fa533bb`. Original national history pending |
| Italy | Eurostat harmonized HICP, `eurostat_8f5e1320615623acdebb`. Istat national CPI backfill pending | Eurostat country series, `eurostat_6e1c74c102959c0ded7b`. Istat backfill pending | Eurostat monthly, `eurostat_c0fc01ed5efaf8a07abd`. Istat backfill pending |
| Japan | Statistics Bureau/e-Stat, `jp_cpi_all_items_2025_nsa`, private, Jan 1970 to Sep 2026 in the CPI audit | Cabinet Office/ESRI, `g7_jp_01`, private, quarterly chained 2020 yen at annual rates | Statistics Bureau/e-Stat, `g7_jp_11`, private, monthly |
| United Kingdom | ONS D7BT, `ons_24c4972dca3a5b1bbe32`, monthly | ONS ABMI, `ons_a007e11b21ed0f67ccf1`, quarterly chained volume | ONS MGSX, `ons_24df6f5df34ca52bac40`, monthly publication of rolling three-month estimates |
| United States | BLS series via FRED, `cpi_nsa`; direct BLS history audit pending | BEA original workbook T10106-Q/A191RX, `fred_8d3240bb6b5eae523737` | BLS U-3 via FRED, `unemployment`; direct BLS history audit pending |

After the French captures there are 12 of 21 concepts with original-publisher
history evidence, seven with Eurostat harmonized histories, and two with legacy
mirror routes that still need direct-source history verification. The Canadian
GDP route uses the observed last month of each quarter. A publisher-produced
quarterly expenditure GDP replacement remains a separate scope decision.

## French national backfills

| Mapping | Publisher series | Coverage in captured file | Valid | Explicit nulls | Publisher update |
| --- | --- | --- | ---: | ---: | --- |
| G7-FR-07 | [INSEE 011814630](https://www.insee.fr/fr/statistiques/serie/011814630) | Jan 1996 to Oct 2026 | 370 | 0 | 2026-11-13 |
| G7-FR-11 | [INSEE 001688527](https://www.insee.fr/fr/statistiques/serie/001688527) | 1975 Q1 to 2026 Q3 | 207 | 0 | 2026-11-10 |

The capture records the current SDMX vintage and preserves its observation
status and revision markers. It does not infer past release timestamps or
combine the national series with HICP or Eurostat monthly unemployment. Refresh
currently runs on demand through the isolated capture workflow. No catalogue
release grant was added. Both rights entries remain pending for paid display,
export and external AI use. [INSEE terms](https://www.insee.fr/fr/information/1302169)
provide starting evidence for an exact-series review.

The next backfill targets are Destatis and Istat headline CPI, followed by
remaining original GDP and labour sources and direct BLS verification.
