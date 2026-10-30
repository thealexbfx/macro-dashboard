# MacroLens: incremental commodity and real-resource gaps

28 October 2026 · Proposal only · **34 missing dataset selections, with a first-10 priority list.**

Compared with the existing 264-entry JSON catalog and architecture proposal. Existing entries were not re-researched or revalidated. Three read-only research agents covered energy, metals and construction. Country panels and paired trade flows count as one dataset selection, not one series per country. No application, database or hosting changes.

The main gap is **commodity benchmarks connected to physical supply, demand, stocks and trade**. Existing macro, US crude production/stocks/gas storage, national construction spending and GB materials/output measures remain reusable. Missouri has no entries. These additions complement that coverage; they do not recreate the catalog.

Validation: **D** = official documentation/publication or identifier checked, selected observation/parser not validated; **T** = official data table inspected, automation pending; **C** = source identified, exact selection/access unresolved. No row implies commercial clearance or a production-ready feed. Full historical coverage was intentionally not audited.

## Energy: 12 additions

**WB:** [World Bank Commodity Markets](https://www.worldbank.org/en/research/commodity-markets), [monthly Pink Sheet workbook](https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx), sheet `Monthly Prices`.

**JO/JG:** [JODI API manual v1.2](https://www.jodidata.org/_resources/files/downloads/jodi-rest-api-v1.2.pdf); `https://www.jodidata.org/api/oildata` and `/api/gasdata`, country/product/flow/unit filters. Free account/JWT; free [oil CSV](https://www.jodidata.org/oil/database/data-downloads.aspx) and [gas CSV](https://www.jodidata.org/gas/database/data-downloads.aspx) alternatives. Selectors below are documented codes, not exercised API queries.

| ID | Missing dataset | Official source / identifier or selector | Validation / main caveat |
|---|---|---|---|
| G01 | Brent price, monthly | WB `Crude oil, Brent`, USD/barrel | D; workbook extraction and benchmark reuse rights pending |
| G02 | European gas benchmark price, monthly | WB `Natural gas, Europe`, USD/MMBtu | D; confirm changing benchmark definition; not TTF futures |
| G03 | Australian thermal-coal price, monthly | WB `Coal, Australia`, USD/tonne | D; specification and benchmark rights |
| G04 | International crude-production panel | JO `CRUDEOIL / INDPROD / KBD`; start Saudi Arabia, Russia, Iraq, UAE, Brazil, Canada | D; coverage pending; extends existing national geography |
| G05 | Refinery crude intake by country | JO `CRUDEOIL / REFINOBS / KBD` | D; distinct from production and final demand |
| G06 | Petroleum-products demand by country | JO `TOTPRODS / TOTDEMO / KBD` | D; demand is not necessarily final consumption |
| G07 | Non-US crude inventories | JO `CRUDEOIL / CLOSTLV / KBBL` | D; end-month levels, reporting gaps retained |
| G08 | Crude imports and exports by country | JO `CRUDEOIL / TOTIMPSB,TOTEXPSB / KBD` | D; separate gross flows, not synthetic net imports |
| G09 | International gas production/demand | JG `NATGAS / INDPROD,TOTDEMO / M3` | D; retain native units and extend country coverage |
| G10 | LNG imports and exports by country | JG `NATGAS / IMPLNG,EXPLNG / M3` | D; gas-volume basis, not tonnes of LNG |
| G11 | US gasoline inventories, weekly | EIA `PET.WGTSTUS1.W`; [official table](https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WGTSTUS1&f=W) | T; free-key API check pending |
| G12 | US distillate inventories, weekly | EIA `PET.WDISTUS1.W`; [official table](https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WDISTUS1&f=W) | T; free-key API check pending |

EIA pattern: `https://api.eia.gov/v2/seriesid/{identifier}?api_key={EIA_API_KEY}`. JODI is monthly national reporting: retain confidence/participation flags and revisions. Available-country sums are not a complete world balance. [JODI definitions/update guidance](https://www.jodidata.org/about-jodi/faqs.aspx).

## Industrial metals: 12 additions

WB uses the shared workbook above. Publication labels/specifications were checked, not complete workbook history. **CT:** [UN Comtrade API documentation](https://uncomtrade.org/docs/un-comtrade-api/). Association sources below are not government agencies.

| ID | Missing dataset | Official source / identifier or selector | Validation / main caveat |
|---|---|---|---|
| G13 | Copper price, monthly | WB `Copper`, USD/metric tonne | D; underlying benchmark rights |
| G14 | Aluminium price, monthly | WB `Aluminum`, USD/metric tonne | D; same workbook/rights gate |
| G15 | Iron-ore price, monthly | WB `Iron ore`, USD/dry metric tonne, 62% Fe CFR China specification | D; retain grade/delivery basis |
| G16 | Nickel price, monthly | WB `Nickel`, USD/metric tonne | D; specification/rights |
| G17 | Zinc price, monthly | WB `Zinc`, USD/metric tonne | D; specification/rights |
| G18 | US copper mine production, monthly | [USGS Copper MIS](https://www.usgs.gov/centers/national-minerals-information-center/copper-statistics-and-information), Table 2, US mine production | T; [sample report](https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/media/files/mis-20250709-coppe.pdf) checked; current-file parser pending |
| G19 | US refined-copper stock components, monthly | Same MIS, Table 10 `Stocks`; producer/fabricator/exchange components | T; estimates and third-party components need flags/rights |
| G20 | LME copper/aluminium warehouse stocks | LME [Stocks breakdown report](https://www.lme.com/en/Market-data/Reports-and-data/Warehouse-and-stocks-reports): levels, live/cancelled warrants, arrivals/departures | D; exact files/history and commercial licence unresolved; defer |
| G21 | China iron-ore import weight, monthly | CT `C/M/HS`; reporter `156`, partner `0`, commodity `2601`, flow `M`, field `netWgt` | D; response, classification and weight completeness pending |
| G22 | China refined-copper cathode import weight, monthly | Same CT selection, commodity `740311` | D; not all copper/alloy imports; response pending |
| G23 | World copper mine/refinery production by country, annual | [USGS MCS 2026](https://pubs.usgs.gov/publication/mcs2026), Copper: `World Mine and Refinery Production and Reserves` | C; indexed official table identified; direct download returned 403 here; data file/parser unresolved |
| G24 | Crude-steel production by country, monthly | worldsteel [data publications](https://worldsteel.org/data/), country/month/crude steel | D; public snapshots versus licensed full history need access decision |

CT candidate example: `https://comtradeapi.un.org/public/v1/preview/C/M/HS?reporterCode=156&period=202501&partnerCode=0&cmdCode=2601&flowCode=M`. Selected response not validated. Use physical weight, not dollar value; keep quantity flags and avoid aggregate/component double counting. USGS mine production, refinery production and reserves are different measures.

## Missouri and UK construction: 10 additions

| ID | Missing dataset | Official source / identifier or endpoint | Validation / main caveat |
|---|---|---|---|
| G25 | Missouri residential permits by structure type, monthly | Census BPS [state-monthly files](https://www.census.gov/construction/bps/statemonthly.html), FIPS `29`; linked `https://www.census.gov/construction/bps/xls/statemonthly_202609.xls` | D; manifest checked, state row not parsed; authorizations, not starts |
| G26 | Missouri construction jobs, monthly SA | BLS CES `SMS29000002000000001`, thousands; `https://api.bls.gov/publicAPI/v2/timeseries/data/`; [official state list](https://www.bls.gov/sae/additional-resources/list-of-published-state-and-metropolitan-area-series/missouri.htm) | D; exact identifier checked, observations pending |
| G27 | Missouri crushed-stone quantity, annual | [USGS Missouri mineral industry](https://www.usgs.gov/centers/national-minerals-information-center/mineral-industry-missouri), state commodity quantity tables | C; exact file/year/row unresolved; lag/suppression |
| G28 | Missouri construction sand/gravel quantity, annual | Same USGS state source, construction sand-and-gravel quantity | C; exact file/row unresolved; distinct commodity |
| G29 | Missouri awarded highway-contract value | MoDOT final awards; project/letting ID + value; [official award process](https://epg.modot.org/index.php/Category:102_Bidding_Requirements_and_Conditions) | C; stable document manifest/parser pending; low bid is not final award |
| G30 | Missouri awarded asphalt/concrete/aggregate quantities and unit bid prices | MoDOT final bid tabs, project + bid-item code + quantity/unit/price | C; item mapping unresolved; later phase, mixed specifications and bidder duplicates |
| G31 | GB total construction new orders, quarterly | ONS [new-orders dataset](https://www.ons.gov.uk/businessindustryandtrade/constructionindustry/datasets/newordersintheconstructionindustry/current); `https://www.ons.gov.uk/file?uri=/businessindustryandtrade/constructionindustry/datasets/newordersintheconstructionindustry/current/bulletindataset7.xlsx`; total CVM SA | D; exact sheet/CDID/base year pending; forward pipeline |
| G32 | GB infrastructure new orders, quarterly | Same ONS workbook, infrastructure type-of-work selector | D; exact sheet/CDID and adjustment pending; do not inherit headline SA |
| G33 | UK cement/clinker import-export quantities, monthly | HMRC `https://api.uktradeinfo.com/OTS`, `/Commodity`; HS `2523` and subheadings; [API docs](https://www.uktradeinfo.com/api-documentation) | D; net-mass query/rollup pending; retain GB/NI and EU reporting breaks |
| G34 | UK aggregate import-export quantities, monthly | Same HMRC API; HS `251710`; [official definition](https://www.uktradeinfo.com/commodities/251710) | D; query/weights pending; all HS2517 would also include tarred macadam/decorative stone |

State minerals and highway awards are supply/demand proxies, not current measured material consumption. UK infrastructure orders add a leading indicator alongside existing output. Cement/aggregate imports complement existing domestic production/deliveries.

## First 10 after ingestion infrastructure is ready

Subject to validation and rights gates; start with selected countries, not every panel member.

| Rank | Dataset | Why first |
|---|---|---|
| 1 | G01 Brent price | Global energy anchor; shared WB download |
| 2 | G13 Copper price | Industrial-cycle benchmark, same parser |
| 3 | G15 Iron-ore price | China/steel/construction exposure, same parser |
| 4 | G04 JODI crude production | International physical supply |
| 5 | G06 JODI products demand | Connect prices with reported demand |
| 6 | G07 JODI non-US crude inventories | Distinguish stock accumulation from flows |
| 7 | G10 JODI LNG trade | Cross-region gas-market fundamentals |
| 8 | G21 China iron-ore import weight | Physical bridge from China to global mining |
| 9 | G25 Missouri housing permits | Accessible local leading-demand indicator |
| 10 | G32 GB infrastructure new orders | Forward materials-demand pipeline |

If rights/access delay WB or JODI, advance G26 Missouri jobs, G11/G12 EIA inventories and G18 USGS copper production after their checks. Do not substitute futures for benchmarks silently. G14 aluminium is the next shared-workbook price addition.

## Access/cost decisions and implementation boundary

- **WB:** public workbook access; check underlying benchmark exceptions before commercial display or AI use. Public availability is not blanket redistribution permission.
- **JODI:** free account/JWT or bulk CSV; targeted commercial/derived redistribution terms remain open. Keep missing reporters, confidence flags and revision history.
- **EIA/BLS/Census/USGS/ONS/HMRC:** public/free methods first. EIA needs a free key; BLS higher-volume registration is optional. OGL/federal-data reuse remains subject to source exceptions. HMRC supports unauthenticated access with pagination/rate limits.
- **Comtrade:** verify small-scope public/free registered access before considering premium bulk/history. Redistribution conditions remain a gate.
- **LME/worldsteel:** defer licence-gated automation. worldsteel advertises an optional **EUR1,590/year** full monthly-data subscription; not recommended expenditure now. [Official subscription information](https://worldsteel.org/data/about-our-data/).
- **MoDOT:** public document extraction and item-standardization QA, not a paid tender service. Confirm bulk reuse; never treat unawarded bids as expenditure or consumption.

Reuse the existing ingestion proposal's registry, SQLite observation/revision store and bounded scheduler. Share provider downloads; retain native quantities, geography and quality flags. Require one accepted sample, exact definition/units, parser fixture and permission decision per addition before backfill. No new architecture or paid service is proposed.

**Saved scope:** this incremental report and its short priority list only. The original 264-series catalog is unchanged. No implementation, production data access, purchases, merges or deployments.
