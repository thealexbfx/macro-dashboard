# Working full-catalog expansion release units

Development branch: `feature/macrolens-full-dataset-expansion`, stacked on the
reviewed Batch 0 foundation and separate suitability audit. Nothing is merged or
deployed. No production database, flags, scheduling, AI, Render resources or DNS
were accessed or changed.

## Output A: actual working datasets

**30 existing public IDs preserved; 168 additional real datasets integrated and
tested in disposable SQLite.** The development public catalog contains 198 IDs.
The new histories contain **171,576 source-native rows, 162,370 non-null values**;
explicit source missing cells remain null. Three production World Bank pilots
and their reported 2,403 observations are untouched and remain private.

[Readable successful inventory](SUCCESSFUL_DATASETS.md) ·
[complete machine-readable inventory](../../../catalog/release_candidates.json) ·
[counts](summary.json) · [rights evidence](rights_evidence.json).

| Original source | Additional working datasets |
|---|---:|
| Eurostat: Germany, France, Italy and exact euro-area compositions | 78 |
| ONS: UK macro and Great Britain construction | 26 |
| Census construction spending | 11 |
| BEA national accounts/income | 9 |
| ECB policy rates, FX, M3 and €STR | 8 |
| BLS including Missouri construction jobs and materials PPI | 7 |
| EIA physical prices, petroleum inventories/production and gas storage | 7 |
| Federal Reserve Board original bulk statistics | 7 |
| DESNZ physical energy balances/deliveries | 6 |
| USGS domestic aggregates and cement shipments | 5 |
| DBT-authored physical materials tables | 4 |

The original manifest remains **309 entries / 298 planning references**. Four
explicit suitability additions have new IDs: WTI spot, five-/ten-year real yields
and broad USD. No existing futures or monthly effective-rate ID is retargeted.
New values use original-producer routes, not an assumed blanket FRED licence.

Important corrections include actual SA labels for Missouri employment and DBT
brick/block/sand-gravel columns; explicit SAAR units for Census/BEA; ONS rolling
labour windows and 2024 reference-year notes; ECB effective-state semantics and
source missing observations; and the obsolete H10 XML unit code reconciled
against the Board's documented 2019 reindexing. Raw values are never rebased here.
Eurostat names identify their country/composition to disambiguate comparisons.

## Output B: exceptions, not a veto on successful units

[All 115 unresolved IDs](EXCEPTIONS.md) · [machine-readable exceptions](exceptions.json).
Each records the selector, exact blocker and next action. This includes remaining
adapter work, not just externally impossible datasets. It must not be described
as 115 verified legal prohibitions or provider outages.

OECD returned 20 real histories but source-owner rights remain unresolved; later
requests encountered rate limiting. BOJ commercial copying requires permission.
World Bank/BCIS/MPA/LME/other third-party rights are not inferred from download
access. BoE redirected to an official error page; e-Stat returned 502. EIA's four
electricity selections need a free credential or another documented original
download. Other unresolved panels, images, units and adapters are listed
individually. Do not wait on gold benchmark licensing to release cleared units.

## Implementation

* Reuses Batch 0 normalized calendars, durable partition jobs, cursors,
  generation snapshots, revisions, APIs, pagination and native Investigate charts.
* `official_snapshots.py` enforces official HTTPS hosts, redirects, verified TLS,
  byte/time budgets and immutable source snapshots before pagination. Standard
  certifi trust roots resolve the local ECB certificate-chain failure; TLS is
  never disabled. HTTP 401/403 are not bypassed. 429 stops that provider's run.
* Exact JSON-stat, ONS, SDMX, BLS, XLS/XLSX and streamed Board XML parsers validate
  source identity, dimensions/columns and units. Annual summaries/YTD totals are
  not invented monthly data. Zero, negative, null and source flags are preserved.
* BLS full backfills use at most twelve documented ten-year requests, batching
  the seven selections together. Source-window byte hashes remain in provenance.
* Release candidates alone are invisible. A version-3 additive display grant,
  matching definition-bound scope review, complete source/hash/cursor receipt
  and per-observation proof are required. AI/Discovery remain independently denied.
* Existing private-only `norm_datasets` CHECK constraints are retained. Version-3
  `catalog_release_grants` is the separately reviewed authoritative display gate;
  the old registry fields remain denied/unreviewed for backward rollback. No
  World Bank grant or protected legacy identity can be registered by this path.
* Long histories use an explicit 50,000-row generation bound; the existing default
  remains 10,000. Release jobs use a **384 MiB combined SQLite/WAL budget**, while
  existing workers retain 256 MiB. Neither changes Render's 1 GB disk allocation.
* Completed staging payload duplicates can be represented by SHA-256 digests;
  every stage key/value/date/partition/artifact remains. Full observation and
  revision payloads, page hashes, receipts and generations remain preserved.
  Compaction is explicit, atomic and off by default for existing workers.

## Validation and capacity

All 168 actual histories completed disposable ingestion, bounded reader queries,
first/middle/last snapshot-to-SQLite sample comparisons, private-scope checks and
SQLite backup/restore integrity. No source failure is silently substituted.
[Windows measurements](windows-validation.json) record the final stored counts.

Fresh backfill of the initial 166,896 rows with the backend loaded took 53.0 s,
49.8 CPU s and peaked at **145.9 MiB Windows working set**. It served 216
concurrent catalog requests without errors; maximum latency was 161.5 ms. The
subsequent full BLS-history update completed the 171,576-row set in 11.9 s,
peaking at 133.8 MiB; 49 concurrent requests had no errors (maximum 67.0 ms).
Final SQLite was **347.8 MiB**, WAL **5.4 MiB**, SHM 32 KiB. These are development
measurements, not Linux/Render RSS claims, and exclude the production legacy DB.

The dedicated GitHub workflow measures representative actual official histories
with the backend and API traffic under 512 MiB, no swap and 0.5 CPU. It also
reuses the 309-entry synthetic catalog workload. Source download failures must
fail validation rather than produce synthetic replacements. Standard Linux
Next.js builds and synthetic/real-history browser checks are included in CI.
Local preview compilation passed; local frontend launch was rejected by automatic
approval review, which supplied no reason. Local browser success is not claimed.

## Safe release order and production blockers

Use [DEPLOYMENT.md](DEPLOYMENT.md). Suggested independent units:

1. Eurostat/ONS: 104 datasets, mostly compact histories.
2. BLS/BEA/Census plus Board H6: 29 datasets.
3. DESNZ/DBT/USGS physical materials: 15 datasets, with short USGS coverage explicit.
4. EIA/ECB/Board daily histories: 20 datasets, only after measured disk headroom.

**Do not activate all 168 blindly.** Existing production SQLite size, backup
retention and WAL headroom are unknown here. Combined production data may hit the
384 MiB software guard before the 1 GB disk limit. Release small units, measure
after each, and stop at the guard. A larger budget/deployment change needs an
explicit evidence-based review; no hosting upgrade was performed.

Date-stamped DESNZ/USGS/DBT issues are pinned releases. Advancing to a new issue
needs a reviewed official URL/definition and validation; generic automatic issue
discovery is not claimed. No native scheduler is enabled by this release. Board
DDP retirement is announced, so bulk-route continuity needs monitoring before
automated updates. Older USGS/UK workbook archive reconciliation remains separate
from the accurately disclosed histories already integrated.

CI conclusions, draft PR links and the commit SHA are reported with the review.
Production requires explicit merge/deploy/migration/ingestion/display approval.

The existing Investigate safety limit of 2,000 native records per series is
unchanged. Long daily MAX/10Y comparisons can require a shorter selected range;
they fail explicitly rather than silently truncate or resample. Full stored
histories remain accessible through paginated observation queries. Expanding
that comparison limit needs a separate measured workload change.
