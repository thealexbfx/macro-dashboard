# Public dataset suitability matrix

Checked 30 October 2026. All 30 current public IDs; no source/permission changes.

Classification concerns research use, not permission. REPLACE means a new source/role under a new ID while preserving the legacy ID and saved references.

History is source metadata, not application coverage: the legacy app requests history from 1990, and a source can begin later. First/last dates do not establish continuity. Yahoo dates are vendor metadata, not validated contract histories.

Full machine-readable fields: [PUBLIC_DATASET_MATRIX.json](PUBLIC_DATASET_MATRIX.json). Rights codes and evidence: [sources.json](sources.json). Current FRED-route restrictions are evaluated separately from original-government-data rights; all flags stay unchanged.

| ID / selected identifier | Original producer; frequency / units / adjustment | Source history checked | Classification | Suitable / unsuitable research | Main continuity risk; better or complementary data | Rights code |
|---|---|---|---|---|---|---|
| `cpi` / `CPIAUCSL` | BLS CPI program; monthly; Index 1982–1984=100; Seasonally adjusted | 1947-01-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Seasonally adjusted short-run consumer-price momentum and inflation-cycle comparisons. Avoid: Official NSA annual headline, individual household cost of living, policy announcement timing or point-in-time trading backtests using revised history. | Urban-consumer coverage and basket weights evolve; an index level is not an inflation rate. Annual SA changes differ from the official NSA headline. Compare: Existing cpi_nsa for official annual CPI; PCEPI for broader consumption prices; BLS release vintages for announcement studies. | L_BLS + T_FRED |
| `core_cpi` / `CPILFESL` | BLS CPI program; monthly; Index 1982–1984=100; Seasonally adjusted | 1957-01-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Short-run consumer inflation excluding food and energy. Avoid: A complete household inflation burden, pure monetary-policy shock or the NSA core headline without choosing that separate series. | Excluding food/energy does not remove every transitory price movement; shelter lags and changing weights matter. Compare: Existing core_cpi_nsa and core_pce; Cleveland Fed median/trimmed-mean CPI under their own definitions and terms. | L_BLS + T_FRED |
| `pce` / `PCEPI` | BEA NIPA / Personal Income and Outlays; monthly; Index 2017=100; Seasonally adjusted | 1959-01-01 to 2026-09-01 | KEEP | Use: Broad consumption-price inflation and the price concept relevant to the Fed's longer-run inflation objective. Avoid: A substitute for CPI contract escalation, a fixed basket or a release-time policy information set without vintages. | Scope, third-party-paid consumption and chain weights differ from CPI; indexes cannot be spliced merely because both measure prices. Compare: Existing core_pce for food/energy exclusion and cpi_nsa for a different consumer-price scope; no wholesale replacement needed. | L_BEA + T_FRED |
| `core_pce` / `PCEPILFE` | BEA NIPA / Personal Income and Outlays; monthly; Index 2017=100; Seasonally adjusted | 1959-01-01 to 2026-09-01 | KEEP | Use: Underlying consumption-price trends excluding food and energy, using the stated transformation. Avoid: An exact representation of all inflation faced by households or an unrevised policy-surprise series. | Chain weights and comprehensive revisions matter; core PCE and core CPI have different scopes and formulas. Compare: Dallas Fed trimmed-mean PCE as a separate robust-trend measure, with source-specific permission review. | L_BEA + T_FRED |
| `unemployment` / `UNRATE` | BLS Current Population Survey; monthly; Percent; Seasonally adjusted | 1948-01-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: U-3 labour-market slack among the civilian labour force aged 16 and over. Avoid: The share of the entire population without a job, unique payroll job creation, or all underemployment. | Labour-force exits can reduce the rate without employment gains. Annual population controls and redesigns need review. Compare: U-6 (U6RATE), prime-age employment/population (LNS12300060), and existing participation/payrolls; each is a distinct concept. | L_BLS + T_FRED |
| `payrolls` / `PAYEMS` | BLS Current Employment Statistics; monthly; Thousands of persons; Seasonally adjusted | 1939-01-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Establishment nonfarm payroll job levels and correctly scaled adjacent-month job changes. Avoid: Unique employed people, self-employment, a fixed unrevised jobs-announcement surprise or direct wage purchasing power. | Multiple jobholders may be counted more than once; employment benchmarks and business births/deaths affect revisions. Compare: CPS employment for people, QCEW for benchmarking, and original BLS release archives for announcement-time values. | L_BLS + T_FRED |
| `real_gdp_growth` / `A191RL1Q225SBEA` | BEA NIPA GDP; quarterly; Percent change, quarterly annualized; Seasonally adjusted annual rate | 1947-04-01 to 2026-07-01 | KEEP + SUPPLEMENT | Use: Quarter-on-quarter annualized real US output growth. Avoid: A GDP level, ordinary quarterly percent change, year-on-year growth or a monthly activity observation. | Already annualized: do not apply another percentage-change transform or sum rates as though they were dollars. Compare: GDPC1 real GDP level for consistent YoY/level questions; final sales and GDI for complementary output evidence. | L_BEA + T_FRED |
| `fed_funds` / `FEDFUNDS` | Federal Reserve Board; underlying daily effective rates administered by New York Fed; monthly; Percent; Not seasonally adjusted | 1954-07-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Monthly overnight funding conditions and slow-moving policy-regime context. Avoid: Identifying first hike/cut announcement dates, target rates, daily event returns or monetary-policy surprises. | Averages mix before/after a decision and calendar-day weights. The 2016 calculation break is distinct from target-regime changes. Compare: Official FOMC statements/events; DFEDTAR and DFEDTARL/U for target states; DFF or NY Fed EFFR for daily implementation. | L_BOARD + T_FRED |
| `sp500` / `^GSPC` | S&P Dow Jones Indices; Yahoo redistributor; daily; index points; No SA convention / market price | 1927-12-30 to unverified | FLAG | Use: Qualified US large-cap price-index context after feed validation and permission clearance. Avoid: Dividend-inclusive investor performance, a tradable security or an unqualified pre-launch/live-constituent history. | Modern 500-stock index launched in 1957; earlier vendor history is a predecessor/backcast question. Yahoo firstTradeDate does not prove uniform construction. Compare: Licensed original S&P price and total-return series; a separately identified SPY total-return proxy only with dividends, fees, tracking and its 1993 inception disclosed. | L_MARKET + T_YAHOO |
| `gold` / `GC=F` | COMEX/CME contract market; vendor continuation construction not verified; daily; USD / troy oz; No SA convention / market price | 2000-08-30 to unverified | REPLACE | Use: Clearly qualified futures-price exploration, pending contract-map, close-time and rights validation. Avoid: Primary spot-gold benchmark, documented rolled futures strategy returns or announcement-window inference from the date label alone. | Basis/carry and contract switches can contaminate chained-close returns. Vendor metadata starts 2000-08-30; it cannot cover 1994/1999 cycle windows. COMEX settlement is not a post-14:00 ET quote. Compare: New licensed London gold AM/PM benchmark IDs for spot research; licensed timestamped XAU/USD or explicit single-contract futures for narrow FOMC windows. Retain gold unchanged as the legacy futures ID. | L_MARKET + T_YAHOO |
| `us10y` / `DGS10` | Federal Reserve Board / US Treasury yield-curve inputs; daily; Percent; Not seasonally adjusted | 1962-01-02 to 2026-10-29 | KEEP + SUPPLEMENT | Use: Nominal long-term yield conditions and basis-point changes. Avoid: A real yield, a bond price/total return or a timestamp-synchronous intraday control. | Constant maturity is fitted, not a held bond. Curve/input methods and holiday gaps matter. Compare: DFII10 real TIPS yield, DGS2 short-end expectations, and separate 10-year breakevens for decomposition. | L_BOARD + T_FRED |
| `dxy` / `DX-Y.NYB` | ICE index methodology; Yahoo redistributor; daily; index points; No SA convention / market price | 1971-01-04 to unverified | FLAG | Use: A fixed developed-currency-basket dollar measure with clear ICE attribution and cleared rights. Avoid: The broad trade-weighted dollar, an FX pair, index futures returns or all US trading-partner exposure. | Six-currency basket, euro weight 57.6%; 1999 euro transition. Vendor firstTradeDate precedes the 1973 base/launch convention, so backcasts require proof. Compare: DTWEXBGS nominal broad trade-weighted dollar (2006 onward); separate historical DTWEXM/DTWEXB panels, never a silent splice. | L_MARKET + T_YAHOO |
| `wti` / `CL=F` | NYMEX/CME contract market; vendor continuation construction not verified; daily; USD / barrel; No SA convention / market price | 2000-08-23 to unverified | REPLACE | Use: Qualified signed futures-price context, with explicit roll and delivery caveats. Avoid: Default physical spot-oil benchmark, physical production/consumption quantities or chained strategy returns without a roll specification. | Vendor metadata starts 2000-08-23; April 2020 expiry/storage effects and legitimate negative prices defeat generic log/percentage-return assumptions. Compare: EIA Cushing WTI spot, FRED comparison identifier DCOILWTICO, under a new ID; add inventories/production/consumption separately. Preserve wti as futures. | L_MARKET + T_YAHOO |
| `cpi_nsa` / `CPIAUCNS` | BLS CPI program; monthly; Index 1982–1984=100; Not seasonally adjusted | 1913-01-01 to 2026-09-01 | KEEP | Use: Official all-items 12-month CPI inflation, purchasing-power comparisons with caveats, and the specified NSA escalation concept. Avoid: Seasonally adjusted monthly momentum or an individual household's exact inflation experience. | Seasonality affects short-horizon changes; annual weight/method changes do not make the index a fixed historical basket. Compare: Existing cpi for SA month-on-month analysis and pce for a broader consumption-price concept; no replacement needed. | L_BLS + T_FRED |
| `core_cpi_nsa` / `CPILFENS` | BLS CPI program; monthly; Index 1982–1984=100; Not seasonally adjusted | 1957-01-01 to 2026-09-01 | KEEP | Use: Official 12-month CPI excluding food and energy. Avoid: All household price pressure, SA monthly core momentum or a real-time surprise without the actual release vintage. | Core composition/weights change; short NSA month-to-month moves retain seasonality. Compare: Existing core_cpi for SA monthly momentum and core_pce for a different scope; no silent blending. | L_BLS + T_FRED |
| `initial_claims` / `ICSA` | US Department of Labor Employment and Training Administration; weekly; Number of claims; Seasonally adjusted | 1967-01-07 to 2026-10-24 | KEEP + SUPPLEMENT | Use: Timely weekly signals of insured layoffs and labour-market deterioration. Avoid: The total unemployed population, all layoffs, or a complete monthly labour-market count. | Week ending Saturday is a reference period, not Thursday publication. Seasonality, holidays, backlog and state reporting can distort individual weeks. Compare: Initial NSA claims (ICNSA), continuing claims (CCSA) and a clearly labelled four-week average, not fabricated daily interpolation. | L_DOL + T_FRED |
| `job_openings` / `JTSJOL` | BLS Job Openings and Labor Turnover Survey; monthly; Thousands of job openings; Seasonally adjusted | 2000-12-01 to 2026-08-01 | KEEP + SUPPLEMENT | Use: Surveyed unfilled positions at the last business day of the month and vacancy demand. Avoid: Payroll jobs created, monthly hires, exact online vacancy advertisements or a real-time count of all available jobs. | Stock at a reference date, not an average flow. Vacancy levels and rates answer different questions as the employment base changes. Compare: JTSJOR vacancy rate, JTSHIR hires and JTSQUR quits rate; preserve stock/flow definitions separately. | L_BLS + T_FRED |
| `participation` / `CIVPART` | BLS Current Population Survey; monthly; Percent; Seasonally adjusted | 1948-01-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Civilian labour-force participation among the noninstitutional population aged 16+. Avoid: Unemployment, employment/population or a pure cyclical slack measure unaffected by ageing. | Demographic composition and population controls matter; denominator scope differs from payroll employment. Compare: Prime-age participation (LNS11300060), prime-age employment/population and existing unemployment. | L_BLS + T_FRED |
| `hourly_earnings` / `CES0500000003` | BLS Current Employment Statistics; monthly; Dollars per hour; Seasonally adjusted | 2006-03-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Average nominal gross hourly earnings of all private payroll employees. Avoid: Fixed-composition wage inflation, benefits-inclusive compensation, median earnings or real purchasing power without an explicit deflator. | Job-composition shocks can raise the average while low-paid workers lose jobs. All-employee scope differs from longer production/nonsupervisory series. Compare: Employment Cost Index wage/compensation measures; separately deflated real earnings and the older nonsupervisory series with its narrower scope. | L_BLS + T_FRED |
| `breakeven_5y` / `T5YIE` | Federal Reserve Bank of St. Louis calculation, Treasury yield inputs; daily; Percent; Not seasonally adjusted | 2003-01-02 to 2026-10-30 | KEEP + SUPPLEMENT | Use: Market-based five-year inflation compensation and comparison with nominal/real yields. Avoid: A pure survey expectation, realized future inflation, or the real-yield variable itself. | Inflation risk and TIPS liquidity premia matter, especially under stress. Maturity and quote times must match; no pre-2003 backfill from future CPI. Compare: DFII5, DGS5 and a separately permissioned SPF inflation forecast at its own horizon/frequency. | L_STL + T_FRED |
| `retail_sales` / `RSAFS` | US Census Bureau MARTS/MRTS; monthly; Millions of dollars; Seasonally adjusted | 1992-01-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Nominal retail/food-service spending and near-term goods-oriented demand. Avoid: Real sales volume, all household services consumption, material tonnage or a standalone real-consumption measure. | Seasonal/trading-day adjustment is not inflation adjustment. Industry definitions and annual benchmarks can revise history. Compare: Real PCE and explicit goods/services components; a correctly matched retail deflator only under a new documented derived series. | L_GOV + T_FRED |
| `real_consumption` / `PCEC96` | BEA NIPA / Personal Income and Outlays; monthly; Billions of chained 2017 dollars; Seasonally adjusted annual rate | 2007-01-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Broad inflation-adjusted household-consumption activity, including services. Avoid: Nominal retail sales, physical tonnes of consumption, or an additive sum of all chained-dollar components. | Verified current FRED table begins in 2007; do not advertise 1959 coverage without a separately validated source response. SAAR levels do not make monthly growth annualized. Compare: BEA direct account/history and real goods/services components; validate the exact monthly table/endpoint mapping before extending history. | L_BEA + T_FRED |
| `consumer_sentiment` / `UMCSENT` | University of Michigan Surveys of Consumers; monthly; Index 1966:Q1=100; Not seasonally adjusted | 1952-11-01 to 2026-09-01 | FLAG | Use: Qualified household attitudes and sentiment, using source-release and delivery-lag information. Avoid: Actual spending/output, a live same-month FRED reading, or a homogeneous monthly sample back to the first 1952 observation. | Do not fill sparse early observations or interpret the April-July 2024 survey-mode change as wholly economic. Follow the specified source attribution. Compare: Separate expectations/current-conditions components if rights-cleared; NY Fed consumer expectations as a different concept, not a drop-in replacement. | L_MICH + T_FRED |
| `housing_starts` / `HOUST` | US Census Bureau / HUD; monthly; Thousands of units; Seasonally adjusted annual rate | 1959-01-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Residential construction starts and forward demand for housing-related inputs. Avoid: All construction/infrastructure activity, completed dwellings, material consumption tonnage or the raw number started during the month. | Thousands at SAAR; weather, sampling error and multifamily volatility matter. Use an NSA series for literal monthly counts. Compare: Existing permits, single/multifamily components, completions (COMPUTSA) and construction put-in-place spending. | L_GOV + T_FRED |
| `building_permits` / `PERMIT` | US Census Bureau / HUD; monthly; Thousands of units; Seasonally adjusted annual rate | 1960-01-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Authorized residential pipeline in permit-issuing places. Avoid: Starts/completions, all US building work, nonresidential infrastructure or tonnes of aggregate demand. | SAAR units and permit-issuing geography must be retained. An authorization does not guarantee subsequent construction. Compare: Existing starts; completions, nonresidential/public construction spending and Missouri/local BPS under separate regional selectors. | L_GOV + T_FRED |
| `mortgage_30y` / `MORTGAGE30US` | Freddie Mac; weekly; Percent; Not seasonally adjusted | 1971-04-02 to 2026-10-29 | KEEP + SUPPLEMENT | Use: Broad weekly mortgage financing conditions for the defined borrower/product sample. Avoid: Every borrower's available rate, daily policy-event response, APR or a homogeneous unchanged survey methodology across November 2022. | Rates/points/sample selection and the 2022 method break matter. Follow actual release/reference weekdays rather than manufacturing a weekly grid. Compare: 15-year PMMS and rate/points distributions where permitted; mortgage credit availability and lending standards as different explanatory variables. | L_PMMS + T_FRED |
| `industrial_production` / `INDPRO` | Federal Reserve Board; monthly; Index 2017=100 (industrial output); Seasonally adjusted | 1919-01-01 to 2026-09-01 | KEEP + SUPPLEMENT | Use: Real manufacturing/mining/utilities output-cycle context. Avoid: Economy-wide GDP, construction output or physical tonnes of one commodity. | Industry weights, energy/weather effects and annual benchmarks matter; an index with a 2017 base is not the same economic object as a price index. Compare: Manufacturing/mining/utilities components, capacity utilization (TCU) and genuinely physical commodity production/stock datasets. | L_BOARD + T_FRED |
| `yield_curve` / `T10Y2Y` | Federal Reserve Bank of St. Louis calculation, Treasury yield inputs; daily; Percent; Not seasonally adjusted | 1976-06-01 to 2026-10-30 | KEEP + SUPPLEMENT | Use: Nominal Treasury curve slope and inversion regimes. Avoid: A causal recession forecast, term premium alone, a bond return or a pure expected policy path. | Level is a percentage-point yield difference although source units say Percent: 1.00 equals 100 bp. Negative values are valid; missing legs cannot be filled silently. Compare: DGS10 and DGS2 inputs; a separately defined 10-year/3-month slope and reviewed term-premium estimates. | L_STL + T_FRED |
| `high_yield_spread` / `BAMLH0A0HYM2` | ICE Data Indices LLC; daily; Percent; Not seasonally adjusted | 2023-10-31 to 2026-10-29 | FLAG | Use: Licensed recent speculative-grade credit-risk/financial-conditions context. Avoid: Default probability, corporate financing cost for every issuer, a bond total return or a free full-history 2008-cycle study. | Current three-year FRED window, model/constituent changes and stale/illiquid bond marks limit interpretation. Levels are quoted percent spreads; changes should be bp/pp. Compare: Licensed original ICE history; a distinct reviewed corporate-minus-Treasury spread or published financial-conditions index, never falsely called the same OAS. | L_ICE + T_FRED |
| `investment_grade_spread` / `BAMLC0A0CM` | ICE Data Indices LLC; daily; Percent; Not seasonally adjusted | 2023-10-31 to 2026-10-29 | FLAG | Use: Licensed recent investment-grade credit conditions, distinguished from high yield. Avoid: A default probability, total return, exact funding rate or unrestricted long-history cycle comparator. | Rolling three-year FRED access and changing index constituents/models; Treasury-curve-relative option adjustment is not the same as a simple yield spread. Compare: Licensed original ICE history; distinct matched-maturity corporate/Treasury measures with their own IDs and permissions. | L_ICE + T_FRED |

## Revision methodology and exact source evidence

### `cpi`

Original selection: BLS CUSR0000SA0; FRED CPIAUCSL. [Producer](https://www.bls.gov/cpi/); [current selected source](https://fred.stlouisfed.org/series/CPIAUCSL); [history metadata](https://fred.stlouisfed.org/data/CPIAUCSL).

Annual seasonal-factor recalculation can revise the preceding five years. Weights, sampling and methods evolve; preserve release vintages for historical information-set studies.

Evidence: [BLS_CPI_SA](https://www.bls.gov/cpi/seasonal-adjustment/using-seasonally-adjusted-data.htm), [BLS_RIGHTS](https://www.bls.gov/bls/linksite.htm).

### `core_cpi`

Original selection: BLS CUSR0000SA0L1E; FRED CPILFESL. [Producer](https://www.bls.gov/cpi/); [current selected source](https://fred.stlouisfed.org/series/CPILFESL); [history metadata](https://fred.stlouisfed.org/data/CPILFESL).

Annual seasonal-factor recalculation can revise the preceding five years. Weights, sampling and methods evolve; preserve release vintages for historical information-set studies.

Evidence: [BLS_CPI_SA](https://www.bls.gov/cpi/seasonal-adjustment/using-seasonally-adjusted-data.htm), [BLS_RIGHTS](https://www.bls.gov/bls/linksite.htm).

### `pce`

Original selection: BEA DPCERG; FRED PCEPI. [Producer](https://www.bea.gov/data/personal-consumption-expenditures-price-index); [current selected source](https://fred.stlouisfed.org/series/PCEPI); [history metadata](https://fred.stlouisfed.org/data/PCEPI).

Monthly estimates are revised with new inputs and annual/comprehensive NIPA updates. Chain weights, methods and reference years change; current history is not a release-time vintage.

Evidence: [BEA_NIPA](https://www.bea.gov/resources/methodologies/nipa-handbook), [BEA_RIGHTS](https://www.bea.gov/help/faq/147).

### `core_pce`

Original selection: BEA DPCCRG; FRED PCEPILFE. [Producer](https://www.bea.gov/data/personal-consumption-expenditures-price-index); [current selected source](https://fred.stlouisfed.org/series/PCEPILFE); [history metadata](https://fred.stlouisfed.org/data/PCEPILFE).

Monthly estimates are revised with new inputs and annual/comprehensive NIPA updates. Chain weights, methods and reference years change; current history is not a release-time vintage.

Evidence: [BEA_NIPA](https://www.bea.gov/resources/methodologies/nipa-handbook), [BEA_RIGHTS](https://www.bea.gov/help/faq/147).

### `unemployment`

Original selection: BLS LNS14000000; FRED UNRATE. [Producer](https://www.bls.gov/cps/); [current selected source](https://fred.stlouisfed.org/series/UNRATE); [history metadata](https://fred.stlouisfed.org/data/UNRATE).

Seasonal revisions and population-control updates can change estimates or create breaks; historical treatment differs across levels and rates. Survey redesigns require source notes and vintages.

Evidence: [BLS_CPS](https://www.bls.gov/cps/documentation.htm), [BLS_RIGHTS](https://www.bls.gov/bls/linksite.htm).

### `payrolls`

Original selection: BLS CES0000000001; FRED PAYEMS. [Producer](https://www.bls.gov/ces/); [current selected source](https://fred.stlouisfed.org/series/PAYEMS); [history metadata](https://fred.stlouisfed.org/data/PAYEMS).

Initial estimates normally receive two monthly revisions; annual employment benchmarking, seasonal factors and methodological updates revise history. Changes in job mix matter for average earnings.

Evidence: [BLS_CES](https://www.bls.gov/web/empsit/cesfaq.htm), [BLS_RIGHTS](https://www.bls.gov/bls/linksite.htm).

### `real_gdp_growth`

Original selection: BEA A191RL; FRED A191RL1Q225SBEA. [Producer](https://www.bea.gov/data/gdp/gross-domestic-product); [current selected source](https://fred.stlouisfed.org/series/A191RL1Q225SBEA); [history metadata](https://fred.stlouisfed.org/data/A191RL1Q225SBEA).

Advance, second and third quarterly estimates, followed by annual/comprehensive revisions. Annualized growth is already transformed; inspect vintage and reference-year changes.

Evidence: [BEA_REVISIONS](https://www.bea.gov/help/faq/130), [BEA_NIPA](https://www.bea.gov/resources/methodologies/nipa-handbook), [BEA_RIGHTS](https://www.bea.gov/help/faq/147).

### `fed_funds`

Original selection: Board H.15 effective funds monthly; FRED FEDFUNDS. [Producer](https://www.federalreserve.gov/releases/h15/); [current selected source](https://fred.stlouisfed.org/series/FEDFUNDS); [history metadata](https://fred.stlouisfed.org/data/FEDFUNDS).

Official monthly aggregation of daily effective rates. Daily methodology changed from brokered volume-weighted mean to FR 2420 transaction-based volume-weighted median on 2016-03-01; monthly figures include calendar days.

Evidence: [H15](https://www.federalreserve.gov/releases/h15/), [NY_EFFR](https://www.newyorkfed.org/markets/reference-rates/effr), [FOMC](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm), [BOARD_RIGHTS](https://www.federalreserve.gov/disclaimer.htm).

### `sp500`

Original selection: S&P DJI S&P 500 price index; secondary Yahoo ^GSPC. [Producer](https://www.spglobal.com/spdji/en/indices/equity/sp-500/); [current selected source](https://finance.yahoo.com/quote/^GSPC/history/); [history metadata](https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?range=5d&interval=1d).

Secondary-vendor corrections and backcasts are not a versioned original index archive. Price indexes exclude dividends; historical constituent/basket changes require original methodology.

Evidence: [SP500](https://www.spglobal.com/spdji/en/indices/equity/sp-500/), [YAHOO_RIGHTS](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html).

### `gold`

Original selection: COMEX GC underlying contract; vendor Yahoo GC=F continuation. [Producer](https://www.cmegroup.com/markets/metals/precious/gold.contractSpecs.html); [current selected source](https://finance.yahoo.com/quote/GC=F/history/); [history metadata](https://query1.finance.yahoo.com/v8/finance/chart/GC%3DF?range=5d&interval=1d).

Per-bar contract selection, roll date, adjustment method and close/settlement identity are not established by the current adapter. Current history is not a frozen contract-level audit trail.

Evidence: [IBA_GOLD](https://www.ice.com/iba/lbma-precious-metals), [CME_SETTLEMENT](https://www.cmegroup.com/tools-information/lookups/advisories/market-regulation/SER-5147.html), [CME_RIGHTS](https://www.cmegroup.com/market-data/distributor/files/cme-group-data-licensing-policy-guidelines-historical-information-distribution.pdf), [LBMA_HISTORY](https://www.lbma.org.uk/centenary-of-the-lbma-gold-price), [GOLD_FRED_REMOVAL](https://fred.stlouisfed.org/news/2022/01/ice-benchmark-administration-ltd-iba-data-to-be-removed-from-fred), [WGC_GOLD](https://www.gold.org/goldhub/data/gold-prices), [YAHOO_RIGHTS](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html).

### `us10y`

Original selection: Board H.15 / Treasury 10-year constant maturity; FRED DGS10. [Producer](https://www.federalreserve.gov/releases/h15/); [current selected source](https://fred.stlouisfed.org/series/DGS10); [history metadata](https://fred.stlouisfed.org/data/DGS10).

Correction-prone financial observations rather than macro survey vintages. Missing business-day quotes must remain missing; yields are fitted constant-maturity estimates, not tradable bond returns.

Evidence: [H15](https://www.federalreserve.gov/releases/h15/), [DFII10](https://fred.stlouisfed.org/data/DFII10), [BOARD_RIGHTS](https://www.federalreserve.gov/disclaimer.htm).

### `dxy`

Original selection: ICE USDX cash index; secondary Yahoo DX-Y.NYB. [Producer](https://www.ice.com/publicdocs/futures_us/ICE_Dollar_Index_FAQ.pdf); [current selected source](https://finance.yahoo.com/quote/DX-Y.NYB/history/); [history metadata](https://query1.finance.yahoo.com/v8/finance/chart/DX-Y.NYB?range=5d&interval=1d).

Secondary-vendor corrections and backcasts are not a versioned original index archive. Price indexes exclude dividends; historical constituent/basket changes require original methodology.

Evidence: [ICE_DXY](https://www.ice.com/publicdocs/futures_us/ICE_Dollar_Index_FAQ.pdf), [FED_DOLLAR](https://www.federalreserve.gov/releases/h10/weights/default.htm), [YAHOO_RIGHTS](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html).

### `wti`

Original selection: NYMEX CL underlying contract; vendor Yahoo CL=F continuation. [Producer](https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.html); [current selected source](https://finance.yahoo.com/quote/CL=F/history/); [history metadata](https://query1.finance.yahoo.com/v8/finance/chart/CL%3DF?range=5d&interval=1d).

Per-bar contract selection, roll date, adjustment method and close/settlement identity are not established by the current adapter. Current history is not a frozen contract-level audit trail.

Evidence: [EIA_WTI](https://fred.stlouisfed.org/data/DCOILWTICO), [EIA_RIGHTS](https://www.eia.gov/about/copyrights_reuse.php), [CME_RIGHTS](https://www.cmegroup.com/market-data/distributor/files/cme-group-data-licensing-policy-guidelines-historical-information-distribution.pdf), [YAHOO_RIGHTS](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html).

### `cpi_nsa`

Original selection: BLS CUUR0000SA0; FRED CPIAUCNS. [Producer](https://www.bls.gov/cpi/); [current selected source](https://fred.stlouisfed.org/series/CPIAUCNS); [history metadata](https://fred.stlouisfed.org/data/CPIAUCNS).

No routine seasonal-factor revision; corrections and methodological/coverage changes remain possible. Do not describe the series as immutable.

Evidence: [BLS_CPI_SA](https://www.bls.gov/cpi/seasonal-adjustment/using-seasonally-adjusted-data.htm), [BLS_RIGHTS](https://www.bls.gov/bls/linksite.htm).

### `core_cpi_nsa`

Original selection: BLS CUUR0000SA0L1E; FRED CPILFENS. [Producer](https://www.bls.gov/cpi/); [current selected source](https://fred.stlouisfed.org/series/CPILFENS); [history metadata](https://fred.stlouisfed.org/data/CPILFENS).

No routine seasonal-factor revision; corrections and methodological/coverage changes remain possible. Do not describe the series as immutable.

Evidence: [BLS_CPI_SA](https://www.bls.gov/cpi/seasonal-adjustment/using-seasonally-adjusted-data.htm), [BLS_RIGHTS](https://www.bls.gov/bls/linksite.htm).

### `initial_claims`

Original selection: DOL ETA UI Weekly Claims / initial SA; FRED ICSA. [Producer](https://www.dol.gov/ui/data.pdf); [current selected source](https://fred.stlouisfed.org/series/ICSA); [history metadata](https://fred.stlouisfed.org/data/ICSA).

Recent weeks can be revised; seasonal factors and estimation methods are updated. Pandemic distortions and reporting backlogs make a single weekly change noisy.

Evidence: [DOL_CLAIMS](https://www.dol.gov/ui/data.pdf), [DOL_RIGHTS](https://www.dol.gov/general/aboutdol/copyright).

### `job_openings`

Original selection: BLS JOLTS total nonfarm openings; FRED JTSJOL. [Producer](https://www.bls.gov/jlt/); [current selected source](https://fred.stlouisfed.org/series/JTSJOL); [history metadata](https://fred.stlouisfed.org/data/JTSJOL).

Preliminary estimates receive revisions and annual benchmarking/seasonal updates. Scope is surveyed vacancies, not all internet advertisements.

Evidence: [BLS_JOLTS](https://www.bls.gov/jlt/), [BLS_RIGHTS](https://www.bls.gov/bls/linksite.htm).

### `participation`

Original selection: BLS LNS11300000; FRED CIVPART. [Producer](https://www.bls.gov/cps/); [current selected source](https://fred.stlouisfed.org/series/CIVPART); [history metadata](https://fred.stlouisfed.org/data/CIVPART).

Seasonal revisions and population-control updates can change estimates or create breaks; historical treatment differs across levels and rates. Survey redesigns require source notes and vintages.

Evidence: [BLS_CPS](https://www.bls.gov/cps/documentation.htm), [BLS_RIGHTS](https://www.bls.gov/bls/linksite.htm).

### `hourly_earnings`

Original selection: BLS CES0500000003; same FRED identifier. [Producer](https://www.bls.gov/ces/); [current selected source](https://fred.stlouisfed.org/series/CES0500000003); [history metadata](https://fred.stlouisfed.org/data/CES0500000003).

Initial estimates normally receive two monthly revisions; annual employment benchmarking, seasonal factors and methodological updates revise history. Changes in job mix matter for average earnings.

Evidence: [BLS_CES](https://www.bls.gov/web/empsit/cesfaq.htm), [BLS_RIGHTS](https://www.bls.gov/bls/linksite.htm).

### `breakeven_5y`

Original selection: St. Louis Fed DGS5 minus DFII5; FRED T5YIE. [Producer](https://fred.stlouisfed.org/series/T5YIE); [current selected source](https://fred.stlouisfed.org/series/T5YIE); [history metadata](https://fred.stlouisfed.org/data/T5YIE).

Derived from Treasury yield inputs; corrections and input-method/source changes propagate. FRED notes a Treasury input-source change in June 2019 for breakevens. Negative spreads/real yields are legitimate.

Evidence: [T5YIE](https://fred.stlouisfed.org/series/T5YIE), [FED_TIPS](https://www.federalreserve.gov/data/yield-curve-models.htm), [FRED_TERMS](https://fred.stlouisfed.org/legal/).

### `retail_sales`

Original selection: Census Advance Monthly Retail Trade / total retail and food services; FRED RSAFS. [Producer](https://www.census.gov/retail/); [current selected source](https://fred.stlouisfed.org/series/RSAFS); [history metadata](https://fred.stlouisfed.org/data/RSAFS).

Advance estimates are revised as fuller monthly information and annual benchmark inputs arrive; historical corrections and seasonal/trading-day factors can change the full path.

Evidence: [CENSUS_RETAIL](https://www.census.gov/retail/index.html), [GOV_RIGHTS](https://www.copyright.gov/help/faq/faq-protect.html).

### `real_consumption`

Original selection: BEA DPCERX; FRED PCEC96. [Producer](https://www.bea.gov/data/income-saving/personal-income); [current selected source](https://fred.stlouisfed.org/series/PCEC96); [history metadata](https://fred.stlouisfed.org/data/PCEC96).

Monthly estimates and annual/comprehensive revisions; chain-linking and rebasing affect reported levels. Chained-dollar components are generally not additive outside the reference period.

Evidence: [PCEC96_RANGE](https://fred.stlouisfed.org/data/PCEC96), [BEA_NIPA](https://www.bea.gov/resources/methodologies/nipa-handbook), [BEA_RIGHTS](https://www.bea.gov/help/faq/147).

### `consumer_sentiment`

Original selection: University of Michigan Index of Consumer Sentiment; FRED UMCSENT. [Producer](https://data.sca.isr.umich.edu/); [current selected source](https://fred.stlouisfed.org/series/UMCSENT); [history metadata](https://fred.stlouisfed.org/data/UMCSENT).

Preliminary/final survey readings differ; FRED delivery is delayed one month. Early pre-1978 history is sparse. Telephone-to-web transition April-July 2024 introduces method effects.

Evidence: [MICHIGAN](https://fred.stlouisfed.org/series/UMCSENT), [MICHIGAN_METHOD](https://www.sca.isr.umich.edu/files/methodtransitionannouncement2024.pdf), [FRED_TERMS](https://fred.stlouisfed.org/legal/).

### `housing_starts`

Original selection: Census/HUD New Residential Construction, total privately owned starts; FRED HOUST. [Producer](https://www.census.gov/construction/nrc/); [current selected source](https://fred.stlouisfed.org/series/HOUST); [history metadata](https://fred.stlouisfed.org/data/HOUST).

Survey/administrative estimates receive monthly and annual seasonal revisions. Geographic coverage, authorizations, starts and completions are different populations/stages.

Evidence: [CENSUS_NRC](https://www.census.gov/construction/nrc/), [GOV_RIGHTS](https://www.copyright.gov/help/faq/faq-protect.html).

### `building_permits`

Original selection: Census/HUD Building Permits Survey, total privately owned authorizations; FRED PERMIT. [Producer](https://www.census.gov/construction/bps/); [current selected source](https://fred.stlouisfed.org/series/PERMIT); [history metadata](https://fred.stlouisfed.org/data/PERMIT).

Survey/administrative estimates receive monthly and annual seasonal revisions. Geographic coverage, authorizations, starts and completions are different populations/stages.

Evidence: [CENSUS_NRC](https://www.census.gov/construction/nrc/), [GOV_RIGHTS](https://www.copyright.gov/help/faq/faq-protect.html).

### `mortgage_30y`

Original selection: Freddie Mac PMMS 30-year fixed-rate national average; FRED MORTGAGE30US. [Producer](https://www.freddiemac.com/pmms); [current selected source](https://fred.stlouisfed.org/series/MORTGAGE30US); [history metadata](https://fred.stlouisfed.org/data/MORTGAGE30US).

Weekly estimates and corrections; major shift from the prior survey to application-based data on 2022-11-17. Historical publication weekdays differ; do not force Thursday labels backward.

Evidence: [PMMS](https://fred.stlouisfed.org/series/MORTGAGE30US), [PMMS_RIGHTS](https://www.freddiemac.com/terms/linking).

### `industrial_production`

Original selection: Board G.17 total industrial production; FRED INDPRO. [Producer](https://www.federalreserve.gov/releases/g17/); [current selected source](https://fred.stlouisfed.org/series/INDPRO); [history metadata](https://fred.stlouisfed.org/data/INDPRO).

Recent monthly estimates, annual benchmarks, seasonal factors, industry weights and methods are revised. Rebased index levels are not tonnes or construction output.

Evidence: [G17](https://www.federalreserve.gov/releases/g17/revisions/current/default_rev.htm), [BOARD_RIGHTS](https://www.federalreserve.gov/disclaimer.htm).

### `yield_curve`

Original selection: St. Louis Fed DGS10 minus DGS2; FRED T10Y2Y. [Producer](https://fred.stlouisfed.org/series/T10Y2Y); [current selected source](https://fred.stlouisfed.org/series/T10Y2Y); [history metadata](https://fred.stlouisfed.org/data/T10Y2Y).

Derived from Treasury yield inputs; corrections and input-method/source changes propagate. FRED notes a Treasury input-source change in June 2019 for breakevens. Negative spreads/real yields are legitimate.

Evidence: [T10Y2Y](https://fred.stlouisfed.org/series/T10Y2Y), [H15](https://www.federalreserve.gov/releases/h15/), [FRED_TERMS](https://fred.stlouisfed.org/legal/).

### `high_yield_spread`

Original selection: ICE BofA US High Yield Index OAS; FRED BAMLH0A0HYM2. [Producer](https://www.ice.com/fixed-income-data-services/index-solutions/fixed-income-indices); [current selected source](https://fred.stlouisfed.org/series/BAMLH0A0HYM2); [history metadata](https://fred.stlouisfed.org/data/BAMLH0A0HYM2).

Constituents rebalance and pricing/OAS models can change; historical corrections are possible. Current FRED access is a rolling three-year window from April 2026, not the index's full economic history.

Evidence: [ICE_HY](https://fred.stlouisfed.org/series/BAMLH0A0HYM2), [ICE_IG](https://fred.stlouisfed.org/series/BAMLC0A0CM), [FRED_TERMS](https://fred.stlouisfed.org/legal/).

### `investment_grade_spread`

Original selection: ICE BofA US Corporate Index OAS; FRED BAMLC0A0CM. [Producer](https://www.ice.com/fixed-income-data-services/index-solutions/fixed-income-indices); [current selected source](https://fred.stlouisfed.org/series/BAMLC0A0CM); [history metadata](https://fred.stlouisfed.org/data/BAMLC0A0CM).

Constituents rebalance and pricing/OAS models can change; historical corrections are possible. Current FRED access is a rolling three-year window from April 2026, not the index's full economic history.

Evidence: [ICE_IG](https://fred.stlouisfed.org/series/BAMLC0A0CM), [ICE_HY](https://fred.stlouisfed.org/series/BAMLH0A0HYM2), [FRED_TERMS](https://fred.stlouisfed.org/legal/).

