# MacroLens data architecture and 264-series ingestion proposal

**Approval draft — researched 27 October 2026. No application changes, database writes, ingestion installation, deployment, branch changes or paid API calls.** Repository audited at `4d7045576b5d0354103e38d733b51805612ea95d` on `feature/macrolens-v2`. This is a proposed expansion, not a claim that 264 production feeds are already connected or commercially cleared.

## Recommendation

Retain the existing FastAPI service, SQLite database on its persistent disk, supervised scheduler, source leases, research engines and Next.js contracts. Add provider adapters and an additive, normalized observation store inside the same SQLite database. Turn the existing scheduler into a bounded dispatcher for due ingestion batches and changed-series research work. Serve research requests from persisted observations rather than triggering hundreds of remote fetches.

The accompanying catalog proposes **264 distinct provider series/document measures** across the requested eight economies. It does not count alternative mirrors as additional series. Native levels and separately published growth measures are separately identified; some aggregates overlap their components and must not be added together.

| Geography | Proposed series | Scope |
| --- | ---: | --- |
| US | 76 | National accounts, inflation, labour, rates/money, housing, construction spending, materials, minerals and physical energy |
| UK / GB | 56 | 38 UK measures plus 18 explicitly GB measures; output, infrastructure, prices, cement, aggregates and energy |
| Euro area | 28 | 20 fixed-composition EA21 Eurostat measures plus 8 explicitly identified ECB/changing-composition monetary/FX measures |
| Germany | 20 | Common Eurostat macro, industrial and construction measures |
| France | 20 | Common Eurostat macro, industrial and construction measures |
| Italy | 18 | Common Eurostat measures; the two requested detailed construction selections returned no observations and were excluded |
| Japan | 22 | OECD macro, BOJ native rates/transactions, official national CPI |
| China | 24 | 12 OECD-distributed monthly/quarterly macro measures and 12 exact NBS annual document/table measures |
| **Total** | **264** | Proposal, including explicitly gated entries |

The full inventory is in `MACROLENS_PROPOSED_SERIES_CATALOG.html` and `.json`. Every entry carries country, exact provider identifier or document selector, endpoint, metadata link, native frequency, coverage, units, seasonal adjustment, licensing reference, credential requirement, update plan and verification state. `ML-xxx` identifiers are research-catalog row numbers, not approved replacement production IDs.

## 1. What MacroLens already has

### V2 production-oriented path

- `backend/app/v2/definitions.py`: immutable `Spec`, explicit units, source definition, provider ID, region, representation, adjustments and allowed transformations. `expanded.py` expands the registry to **30 current series: 26 FRED and 4 Yahoo**. The supported registry frequencies currently exclude annual data.
- `backend/app/v2/main.py`: `V2PublicProvider` fetches FRED website CSV and Yahoo chart JSON; `DataService` validates observations/freshness/definitions and computes controlled transformations. FRED retrieval currently downloads full website CSV then filters history from **1990**. Comparison validation also has a 1990 floor. The proposal's earlier provider history cannot currently be queried through V2 unchanged.
- `backend/app/services/direct_answers.py`: reusable small provider boundary and request utilities without Streamlit dependency; the protocol currently exposes FRED and market methods, not a generic multi-provider catalog.
- `backend/app/v2/refresh.py`: persistent per-series source cache, in-process key locks, SQLite source leases, next-due timing, failure backoff and lease-held freshness assessment. Current daily/weekly/base economic checks are 6h/12h/24h, with selected release-date hints. These are useful mechanisms, not a comprehensive international release calendar. Some release hints in `expanded.py` are dated static entries.
- `backend/app/v2/state.py`: WAL SQLite; `source_cache` stores whole Dataset JSON; `leases`, `reports`, `stories`, `story_versions`, `library` and AI accounting tables persist research state. There is no normalized observation/vintage store, generic ingestion-job ledger or rights registry yet.
- `backend/app/v2/scheduler.py`: supervised 60-second background loop with heartbeat/attempt/success/failure diagnostics. `/ready` probes scheduler/database operation without querying providers. Reuse this supervision and preserve its provider-independent readiness.
- `backend/app/v2/runtime.py`: source/report fingerprints and a short cache prevent unchanged rescans; archives are bounded/on-demand. Cold/due source loading still maps across the whole V2 `SPECS` registry using five threads, and the catalogue returns complete history for every registered dataset.
- V2 research and comparison paths already preserve actual observations, missingness, horizon definitions, saved investigation snapshots and historical identities. Reuse these calculations; do not redesign them as part of ingestion.

### Additional existing legacy adapters — useful code, not drop-in V2 dependencies

The repository is broader than the V2 catalog. `data/fred.py` already implements authenticated FRED JSON, response validation and bounded retries; `data/ons.py` implements CDID/dataset retrieval and date parsing; `data/eurostat.py` contains JSON-stat retrieval; `data/ecb.py` has SDMX CSV loaders; `data/boe.py` parses Bank Rate HTML; `data/boj.py` and `data/japan.py` contain BOJ files/new API, e-Stat, Dashboard, customs and national-file loaders. `data/bls.py` and `data/bea.py` are potential primary-US access paths. Existing configuration references FRED and e-Stat credentials; no values were inspected or used in this research.

**Reuse pure parsing/validation logic after tests, not entire imports.** These modules commonly import Streamlit, decorators and shared `config`, while legacy refresh/storage uses Streamlit caches and Redis/Valkey or pickle files. V2 should not acquire a runtime dependence on those services. No usable V2 adapter for OECD, EIA, USGS or China was found.

Specific porting hazards found in the source:

1. Legacy `eurostat_json_to_df` indexes observations solely by the time position. This is valid only if every other dimension has exactly one selected category. A generic adapter must decode the complete JSON-stat cube or reject unpinned dimensions; the catalog verification enforced the latter.
2. Legacy ONS loading silently chooses months before quarters before years. New registry entries must explicitly select native frequency and keep quarterly/monthly aggregates separate. `get_uk_gdp_mom_data` returns ECY2, which the live ONS metadata identifies as a **monthly volume index**, not an already calculated month-on-month growth rate. Do not propagate the function name as a data definition.
3. Legacy Japan code includes a basic-discount-rate-to-policy-rate approximation in `get_japan_policy_rate_proxy_data`. It must not be imported as an official policy target. Use BOJ's explicitly named target, discount or observed call-rate series with their real definitions.
4. Some legacy Japan loaders hard-code workbook positions, filter legitimate zero trade balances or discard missing rows. Do not copy those behaviours into a generalized ingestion layer. The proposed versioned parser must retain nulls, zeroes and source flags.
5. `data/http.py` describes bounded downloads but buffers `response.content` without a byte-size ceiling. Add an actual streaming size limit before reusing it for SDMX/bulk files on 512 MB instances.
6. US market-session assumptions in V2 movements are not valid calendars for BOJ, TARGET/ECB, UK or Chinese daily releases. Economic reference periods also differ from trading dates.
7. `render.yaml` still describes the legacy Streamlit service on `main`; it is not an authoritative description of the separately configured V2 Render services. No hosting configuration was changed or audited through Render in this task.

## 2. Official access methods and access gates

| Source | Official method / exact address pattern | Credentials, cost and restrictions | Recommended refresh |
| --- | --- | --- | --- |
| FRED / ALFRED | `https://api.stlouisfed.org/fred/series`, `/series/observations`, `/series/vintagedates`; v2 release-bulk API also exists | Free registered API key. Existing V2 website CSV is not a substitute for authenticated metadata/vintages. Application/user-key terms and commercial display rights need approval. Third-party series can require permission. | Metadata/release-aware due jobs; overlap for revisions; ALFRED where available |
| OECD | `https://sdmx.oecd.org/public/rest/v1/data/{agency},{flow},{version}/{dimension.key}`; dataflow/DSD/codelists/content constraints | No key, free API; rate limiting; data terms and third-party exceptions. Catalog uses current `OECD.SDD.STES,DSD_KEI@DF_KEI,4.0` keys, not legacy OECD.Stat guesses. | Cache DSDs; narrow, batched country/frequency queries; back off on 429 |
| Eurostat | Statistics JSON-stat `https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}`; official SDMX 2.1/3.0 and catalogue alternatives | No key/fee. Source acknowledgement required. Latest database is revised; do not infer historical vintages from today's download. | Metadata + release-aware daily checks; Eurostat refresh windows are normally twice daily |
| ONS | Published time-series `/.../timeseries/{cdid}/{dataset}/data` and linked CSV/XLS; CMD `https://api.beta.ons.gov.uk/v1/datasets` for datasets exposed there | No key for public downloads. OGL with exceptions. Not all legacy CDIDs are CMD datasets; do not synthesize an API route from a CDID alone. | Use release/next-release/version metadata and official attachment manifests |
| Bank of England | Documented `_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=...&Dateto=now&SeriesCodes=...&UsingCodes=Y&CSVF=CT` | No subscription/key required for IADB download; up to 300 series codes per documented query. This research host received **403**; no bypass attempted. Database OGL has selected FX exclusions; SONIA requires specific attribution. | Small CSV batches, separate notes/metadata, daily or monetary-release timing |
| ECB | `https://data-api.ecb.europa.eu/service/data/{flow}/{key}?format=csvdata`; dataflow/structure services | No key/fee. Free reuse of public ESCB statistics subject to notices. `updatedAfter` can return changed observations/304. | Deltas plus overlap/full reconciliation; policy-effective dates and reference FX schedules remain distinct |
| EIA | `https://api.eia.gov/v2/.../data/` or `/v2/seriesid/{legacy-id}`; keyless official bulk files | Free registered key for API. API v1 is retired; a legacy ID through the v2 compatibility route is supported. JSON pagination maximum is 5,000 observations. Bulk files need no key but may be too large for this server without streaming. | Native weekly/monthly release schedule; preserve units/facets and revision windows |
| USGS NMIC | Official commodity release pages, linked monthly cement and quarterly aggregates XLSX/PDF/ZIP; ScienceBase manifests as releases migrate | No paid key for public files. No verified unified economic-series API. The USGS water API is irrelevant to these mineral indicators. Public-domain federal data with source/third-party checks. | Poll release manifests weekly; parse new/revised files; reconcile overlapping releases |
| Japan | BOJ `https://www.stat-search.boj.or.jp/api/v1/getDataCode`, `/getMetadata`, `/getDataLayer`; e-Stat `/rest/3.0/app/json/getStatsData`; Statistics Dashboard `/api/1.0/Json/getData` | BOJ API launched 18 Feb 2026, no registration; full e-Stat needs a free registered appId; Dashboard needs no key and requires API credit. Published statistics and source-specific rights apply. | BOJ daily metadata/business-day checks; e-Stat native release calendar; explicit rebasing/version mapping |
| China | NBS official releases, National Data portal and yearbook at `https://www.stats.gov.cn/english/Statisticaldata/`; exact edition/table URLs in catalog | A supported, documented unauthenticated general NBS series API was **not established**. Do not rely on old undocumented `easyquery.htm` recipes or bypass access controls. Rights/automated commercial extraction require confirmation. | OECD-distributed macro core first; NBS authorized exports or human-verified annual files second |

Official method references: [FRED key policy](https://fred.stlouisfed.org/docs/api/api_key.html), [OECD API](https://www.oecd.org/en/data/insights/data-explainers/2024/09/api.html), [Eurostat API](https://ec.europa.eu/eurostat/en/web/user-guides/data-browser/api-data-access/api-introduction), [ONS developer hub](https://developer.ons.gov.uk/), [BoE download help](https://www.bankofengland.co.uk/boeapps/database/help.asp), [ECB API](https://data.ecb.europa.eu/help/api/data), [EIA documentation](https://www.eia.gov/opendata/documentation.php), [BOJ API manual](https://www.stat-search.boj.or.jp/info/api_manual_en.pdf), [e-Stat API](https://www.e-stat.go.jp/api/), [Dashboard API](https://dashboard.e-stat.go.jp/en/static/api).

## 3. Inventory evidence and limitations

This proposal distinguishes **a valid mapping**, **observed coverage**, **an operational feed**, and **redistribution permission**. None implies the others.

- 202 entries were checked against non-missing official observations: 63 FRED, 78 Eurostat, 21 ONS, 30 OECD, 8 ECB and 2 Japan Dashboard series.
- 31 entries were checked against official workbook headers and data/printed coverage: 9 ONS construction, 11 UK building materials, 6 DESNZ energy, 5 USGS minerals.
- 12 NBS annual entries were visually checked against official table images. Their exact identifiers are edition/table/column selectors because no supported stable API series IDs were established. These require human verification before ingestion, rather than invented API codes.
- 2 BOJ entries have official live metadata verification; their data URLs follow the published API manual.
- 2 MPA entries use a visible recent published quarterly table; historical bulk access and commercial reuse remain permission-gated.
- 7 BoE and 8 EIA entries are explicitly access/credential-gated. Exact first/last observation coverage is marked **unverified**, not guessed. They are proposal slots, not implementation-ready feeds. Authenticated FRED API calls were also not exercised; the observations were checked through the official website's download and metadata pages.

The catalog intentionally excludes two invalid FRED candidates (`WPUFD4`, `PBSEWCONS`), four unresolved ONS path candidates and the two Italian detailed construction filters that returned no values. A zero-size or empty API cube is not success.

Important definition findings:

- Bulgaria joined the euro in January 2026. The catalog pins **EA21** and separately labels the ECB's changing-composition monetary aggregate; no automatic EA20/EA21 splice is proposed. [ECB changeover reference](https://www.ecb.europa.eu/euro/changeover/bulgaria/html/index.en.html)
- Current HICP is `prc_hicp_minr`, `coicop18=TOTAL`, with the requested unit; old `prc_hicp_midx`/`manr` ECOICOP1 mappings are archived. Index base 2025 and classification changes must be explicit. [Eurostat 2026 HICP information](https://ec.europa.eu/eurostat/web/hicp/information-data)
- UK construction output is **GB**, whereas some materials/energy series cover **UK**. Current inspected ONS construction indices use **2024=100**. Concrete block deliveries are in **thousand**, not million, square metres.
- UK cement production is annual in the inspected release; sand/gravel and ready-mix are quarterly. A monthly publication date does not make all its tables monthly. GB cement/geographic and recycled-material scope changes require series-definition versions.
- UK bitumen deliveries and US asphalt/road-oil product supplied are physical demand proxies, not asphalt-mixture production. The direct MPA asphalt measure is a sample sales-volume growth series, not tonnage and not an official-government series.
- China annual energy table 9-17 in the inspected edition contains only 2023/2024; longer coverage needs earlier-edition extraction and revision reconciliation. Floor-space tables contain selected earlier years. No missing observations have been invented.
- Provider-reported quarterly GDP growth is not interchangeable with US annualized quarterly GDP growth. Currency, constant/current-price basis, unit multipliers, fiscal/calendar years and overlapping rolling labour estimates must remain explicit.

## 4. Proposed unified ingestion design

### Data flow

`approved registry + rights -> existing scheduler -> SQLite due-job lease -> provider adapter -> raw artifact/hash -> validation/staging -> short SQLite commit -> changed-series marker -> existing research engines -> existing V2 Dataset/Comparison contracts`

This is a design only; no tables or jobs were created.

### Additive SQLite entities

| Proposed entity | Purpose / important key |
| --- | --- |
| `series_catalog` | Stable internal ID, provider/flow/version/all dimensions, native frequency, unit/scale/base, adjustment, geography definition, source and release policy, parser version, rights state |
| `series_aliases` | Preserve all existing V2 IDs and saved investigations; explicitly map equivalent source definitions only after review |
| `observations` | `(series_id, native_period)` primary key; source label, start/end period, value/null, source flags, source update time, first/last seen, validated ingestion run |
| `observation_revisions` | Append changes with observed-at time and old/new values/flags; genuine provider vintage/publication timestamps only when supplied |
| `ingestion_runs` | Provider batch, request fingerprint, mapping/parser version, started/finished, bytes, row/revision counts, status, redacted error, checksum and artifact path |
| `ingestion_jobs` | Unique due job/batch, next due, priority, attempts/backoff, lease owner/expiry and last success |
| `source_artifacts` | Bounded on-disk response manifests/hashes, rights/provenance, schema hash; avoid retaining duplicate full files indefinitely |
| `dirty_series` | Persist changed IDs/revisions so analytics only recompute actual dependent research |

Retain `source_cache`, `reports`, `stories`, `story_versions`, `library` and all AI/history/accounting tables. Initially dual-read verified observations into the existing Dataset contract and retain existing source JSON for rollback. Do not rewrite discovery IDs or saved research; do not silently replace Yahoo futures with EIA spot/physical series. Schema changes require a consistent SQLite backup, a reversible additive migration and count/hash reconciliation before approval to switch reads. The database remains at its existing configured persistent path.

### Provider adapters and scheduling

Factor existing tested parsers away from Streamlit wrappers into adapters exposing metadata/discovery, fetch, parse and release-policy operations. Keep original legacy wrappers working. Add SDMX adapters for OECD/ECB, a proper JSON-stat decoder for Eurostat, explicit ONS frequency/CDID selection, EIA v2 and deterministic workbook adapters. Separate raw observations from transformations; reuse V2 transformations later.

The existing 60-second supervisor should dispatch a small number of due jobs rather than refresh all 264 sources on every tick. Reuse SQLite leases and extend them only if a genuinely long bounded operation needs renewal. Fetch and parse outside write transactions, then commit idempotent chunks via a single writer. Provider failures pause that provider with backoff; they do not kill the supervisor or erase cached observations. Keep liveness/readiness independent of remote providers and expose provider freshness separately.

Start with two network requests globally, one per provider, one parser/writer batch, small SDMX country/time requests and a measured byte ceiling. Honour Retry-After, ETag/Last-Modified and provider deltas where actually supported; never assume every source implements them. Backfill jobs run at lower priority and yield between chunks. Do not make user chart requests wait on backfills. Preserve current analytical admission controls; do not hold the expensive-analysis lock during slow downloads.

Use daily metadata checks for monthly/quarterly releases, modest release-window checks and less frequent checks away from releases. Check daily monetary data after its actual local publishing window, not continuously. Periodically reconcile full histories because old observations can change. Store scheduling times in UTC and retain release timezone/period semantics. Poll one publication file once and extract its multiple measures; do not download the same workbook per catalog row.

### Research correctness, security and rights

Pin full dimension keys and metadata hashes; reject silent unit/base-year/seasonal/geographic changes. Preserve suppressed/provisional/estimated/break flags and actual missing cells. Handle revisions, dates and native currencies without generic interpolation or forced daily grids. Annual support, provider-specific calendars and pre-1990 history require deliberate extensions to current validators and display contracts.

Never infer historical publication dates or first-release vintages from today's revised observations. ALFRED/provider history is used only where available; locally captured revisions begin when ingestion starts. Chinese YTD or combined January–February measures need their own contracts; do not manufacture monthly levels by differencing unless a separately approved valid derivation exists.

Store credentials server-side only. Redact key-bearing URLs, response echoes and errors: EIA's response can echo the request API key. Apply provider host allowlists, actual streaming size limits, bounded ZIP expansion and deterministic parsers; never execute downloaded spreadsheet macros. Human review is mandatory for scanned/OCR tables and parser/schema changes.

Rights should be a registry control: `research_allowed`, `commercial_display_allowed`, `redistribution_allowed`, `ai_use_allowed`, attribution and evidence/expiry. Unknown permissions remain denied. Keep AI disabled. FRED's current terms explicitly restrict AI-related uses; blanket treatment as unrestricted public-domain data is not justified. Source primary-government data independently if that is the approved rights path, without using provenance changes to disguise restricted redistribution. [FRED terms](https://fred.stlouisfed.org/legal/terms/)

## 5. Capacity and cost implications

**No new paid data API or hosting service is inherently required for the open-statistics core.** FRED, EIA and full e-Stat registrations are free; OECD, Eurostat, ONS, BoE, ECB, BOJ and Dashboard public methods have no API subscription charge in the researched documentation. Access being free does not establish commercial redistribution rights. No registrations or purchases were made.

| Cost / risk | Proposal |
| --- | --- |
| Incremental API fees for approved open core | Expected $0; free credentials and provider terms still apply |
| Hosting | Reuse current services/disk initially; no promised plan increase or new database service. Actual headroom must be measured before accepting production volume |
| Storage | Engineering estimate: 0.3–1 million normalized observations at roughly 100–250 bytes each means about 30–250 MB before some indexes, artifacts and revision history. Raw-file retention can dominate; set an approved quota and measure real size |
| Memory | Do not load all 264 complete histories into duplicated Pydantic/JSON/DataFrame objects. Stream/chunk, lazy-read selected datasets, bound source cache and reuse unchanged transforms. Profile RSS/CPU under a 512 MB limit before release |
| Operations | Budget time for source schema changes, attribution, revisions and release calendars; manual China/file QA continues until authorized reliable exports are established |
| Optional licensed sources | MPA historical/asphalt/aggregates rights and bulk delivery may require permission or a quote; no published price was verified. BCIS commercial products are not included as a licensed feed. Existing ICE/Michigan/Yahoo redistribution rights also need their own review |
| Engineering | Rough planning allowance: 4–8 engineer-weeks for registry/rights, adapter refactoring, migrations, QA and staged acceptance, plus external permission waiting; estimate only, not a quotation |

Merely adding 264 registry entries is not safe. At five threads and the current eight-second provider timeout, one timeout per source would take roughly `ceil(264/5) * 8 = 424 seconds`, before parsing/retries. This is an illustrative upper-bound calculation, not a Render benchmark; it exceeds the current scheduler's heartbeat tolerance. Bounded scheduled jobs and selected-series reads avoid that design problem.

A reasonable initial operating estimate is tens to a few hundred HTTP requests per day after backfill when publications are batched and changes checked conditionally, not 264 multiplied by every browser visit. This must be measured against the eventual approved native release list and provider limits.

## 6. Phased implementation for approval

1. **Registry and rights gate.** Approve the 264-row scope; resolve 15 access/credential-gated entries, MPA permission, NBS reuse and ambiguous metadata (including ONS internet-share seasonal treatment). Confirm FRED commercial/API/AI policy and BOJ commercial reproduction/alteration permissions. Agree which document selectors are acceptable manual feeds. Establish stable IDs, geography/native-period/unit contracts and test fixtures. No production table migration yet.
2. **Open core and compatibility.** Extract pure existing FRED/ONS/ECB/Eurostat parsers; add provider metadata/rights mapping, additive SQLite migration and a bounded due-job dispatcher under the existing supervisor. Start a limited US/UK/EA/DE/FR/IT core. Preserve the existing 30 V2 IDs and all research/history. Verify request latency and memory before expanding.
3. **Japan/China macro and international completion.** Add current OECD SDMX, BOJ API and Dashboard/e-Stat adapters. Complete an approved automatically retrievable core of roughly 200 measures, only where exact definitions and rights pass. Add annual frequency and pre-1990 coverage without altering earlier saved investigations. Resolve BoE access through supported methods or provider contact, never access-control bypass.
4. **Construction, materials and physical energy.** Add EIA v2, ONS construction/DBT/DESNZ file manifests and USGS release/archive parsing. Prefer current, machine-readable official spreadsheets. Reconcile SA/NSA, annual cement, quarterly aggregates, 2024/2025 index bases, suppressed cells and revisions. Add only approved MPA access; retain bitumen/asphalt distinction.
5. **Manual/gated history and production acceptance.** Human-verify NBS yearbook extraction, reconcile prior editions, and introduce licensed history only if separately approved. Exercise cold/warm reads, provider timeouts/403/429, restarts/leases, revision reprocessing, duplicate suppression, SQLite backup/restore, schema-change quarantine and a sustained 512 MB load test. Add discovery dependencies gradually, not an all-pairs scan.

Each phase ends with a diff, per-series acceptance report, tests and explicit release approval. No automatic merge or deployment is included. The 264 proposals are a backlog with quality/access gates; not every candidate should enter production on the first release.

## 7. Deliverables and validation

- `MACROLENS_PROPOSED_SERIES_CATALOG.html`: standalone searchable, geography-filterable catalog; expand any row for all metadata/rights/access details.
- `MACROLENS_PROPOSED_SERIES_CATALOG.json`: 264 structured records, 22 fields each, suitable for later approved registry work; no credentials.
- `MACROLENS_PROPOSED_SERIES_INDEX.md`: compact human-readable index of all 264 entries.
- Supporting official metadata, workbook headers and sampled files are retained in this research output directory. They were not copied into application state or installed in the feed.

Validation performed: exact record count, unique catalog row IDs, required fields, eight-economy coverage, checked source dimension cardinality, non-missing observed ranges, source workbook units/headers, explicit unresolved/access states, and no real API keys in catalog URLs. Source response verification is not a complete production integration or rights certification. No application tests/build were necessary because application code was not changed.

Rights clarification: [BOJ Time-Series Data Search terms](https://www.stat-search.boj.or.jp/info/notice.html) require prior consultation for commercial reproduction and restrict alteration. The two BOJ candidates remain rights-gated despite free technical API access.
