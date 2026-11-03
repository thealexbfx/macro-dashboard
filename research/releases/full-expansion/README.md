# Working full-catalog expansion release units

Development branch: `feature/macrolens-full-dataset-expansion`, stacked on the
reviewed Batch 0 foundation and separate suitability audit. Nothing is merged or
deployed. No production database, flags, scheduling, AI, Render resources or DNS
were accessed or changed.

## Output A: actual working datasets

**30 existing public IDs preserved; 185 additional real datasets integrated and
tested in disposable SQLite.** The development public catalog contains 215 IDs.
The new histories contain **203,387 source-native rows, 194,180 non-null values**;
explicit source missing cells remain null. Three production World Bank pilots
and their reported 2,403 observations are untouched and remain private.

[Readable successful inventory](SUCCESSFUL_DATASETS.md) ·
[complete machine-readable inventory](../../../catalog/release_candidates.json) ·
[counts](summary.json) · [rights evidence](rights_evidence.json).

| Original source | Additional working datasets |
|---|---:|
| Eurostat: Germany, France, Italy and exact euro-area compositions | 78 |
| ONS: UK macro and Great Britain construction | 26 |
| Census construction spending, housing and manufacturing orders | 15 |
| BEA national accounts/income | 9 |
| ECB policy rates, FX, M3 and €STR | 8 |
| BLS including Missouri construction jobs, employment-population ratio and PPI | 9 |
| EIA physical prices, petroleum inventories/production and gas storage | 7 |
| Federal Reserve Board original bulk statistics | 10 |
| Bank of England rates and monetary/credit stocks | 7 |
| DESNZ physical energy balances/deliveries | 6 |
| USGS domestic aggregates and cement shipments | 5 |
| DBT-authored physical materials tables | 4 |
| DOL national seasonally adjusted continued claims | 1 |

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

[All 98 unresolved IDs](EXCEPTIONS.md) · [machine-readable exceptions](exceptions.json).
Each records the selector, exact blocker and next action. This includes remaining
adapter work, not just externally impossible datasets. It must not be described
as verified legal prohibitions or provider outages.

OECD returned 20 real histories but source-owner rights remain unresolved; later
requests encountered rate limiting. BOJ commercial copying requires permission.
World Bank/BCIS/MPA/LME/other third-party rights are not inferred from download
access. The BoE error was resolved: the original request started before its permitted 1963 start date. All seven BoE selections now work; e-Stat still returned 502. EIA's four
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
  selected series together. Source-window byte hashes remain in provenance.
  CPS people-based ratios remain distinct from CES payroll jobs; BLS's explicit
  dash missing marker remains null, while negative numbers remain negative.
  Board H41 assets retain Wednesday dates, distinct from Friday weekly series.
  DOL claims retain Saturday reference weeks; blank unpublished year-template
  rows outside actual coverage are excluded, while internal missing cells remain
  null. Census M3 uses original NAICS codes and monthly dollar flows, not SAAR
  or an undocumented SIC splice; housing uses the national one-unit SAAR column.
* Release candidates alone are invisible. A version-3 additive display grant,
  matching definition-bound scope review, complete source/hash/cursor receipt
  and per-observation proof are required. AI/Discovery remain independently denied.
* Existing private-only `norm_datasets` CHECK constraints are retained. Version-3
  `catalog_release_grants` is the separately reviewed authoritative display gate;
  the old registry fields remain denied/unreviewed for backward rollback. No
  World Bank grant or protected legacy identity can be registered by this path.
* Long histories use an explicit 50,000-row generation bound; the existing default
  remains 10,000. Release jobs default to a **384 MiB combined SQLite/WAL budget**, while
  existing workers retain 256 MiB. A separately reviewed explicit
  `--storage-budget-mib 512` ceiling is available; this is a software disk guard,
  not a RAM/hosting allocation change. Render's 1 GB disk is unchanged.
* Completed staging rows can move to compact SHA-256 receipts;
  every stage key/value/date/partition/artifact remains in those receipts. Full observation and
  revision payloads, page hashes, receipts and generations remain preserved.
  Compaction is explicit, atomic and off by default for existing workers.

## Validation and capacity

All 185 actual histories completed disposable ingestion, bounded reader queries,
first/middle/last snapshot-to-SQLite sample comparisons, private-scope checks and
SQLite backup/restore integrity. No source failure is silently substituted.
[Windows measurements](windows-validation.json) record the final stored counts.

Fresh backfill of all 203,387 rows with the backend loaded took **61.0 s**,
56.9 CPU s and peaked at **147.2 MiB Windows working set**. It served 247
concurrent catalog requests without errors; maximum latency was 150.4 ms.
Bounded preview queries had a 4.14 ms median and 8.42 ms maximum. Final SQLite
was **268.0 MiB**, WAL **29.3 MiB**, SHM 64 KiB, within the default 384 MiB
software guard. Before moving completed working rows to compact receipts, the
smaller 175-set used 397.2 MiB SQLite; the new path preserves all lineage while
releasing duplicate staging pages for reuse. No VACUUM or production rewrite ran.
A second run kept exactly 203,387 observations and passed in 9.8 s with 40 API
requests and zero errors ([idempotency evidence](idempotency-validation.json)).
These are development Windows measurements, not Linux/Render RSS claims, and
exclude the production legacy DB and backup retention.

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
2. BLS/BEA/Census/DOL plus Board H6/G17/H41: 39 datasets.
3. DESNZ/DBT/USGS physical materials: 15 datasets, with short USGS coverage explicit.
4. EIA/ECB/Board daily histories: 20 datasets, only after measured disk headroom.
5. Bank of England: 7 datasets; include the SONIA attribution and stock/flow labels.

**Do not activate all 185 blindly.** Existing production SQLite size, backup
retention and WAL headroom are unknown here. Combined production data may hit the
384 MiB software guard before the 1 GB disk limit. Release small units, measure
after each, and stop at the guard. Compact receipts bring the full development
set below the default 384 MiB guard; combined production-size/headroom still needs review. No hosting
upgrade was performed. The legacy WB worker retains its 256 MiB guard and will
stop safely above that size; keep it disabled pending a separate capacity review.

Date-stamped DESNZ/USGS/DBT issues are pinned releases. Advancing to a new issue
needs a reviewed official URL/definition and validation; generic automatic issue
discovery is not claimed. No native scheduler is enabled by this release. Board
DDP retirement is announced, so bulk-route continuity needs monitoring before
automated updates. Older USGS/UK workbook archive reconciliation remains separate
from the accurately disclosed histories already integrated.
DOL's reviewed query ends in 2026; extend its explicit year bound only after
checking the official calendar. Reusing the same immutable snapshot is idempotent.
A fresh capture has a new validation timestamp and snapshot identity even when
raw source bytes are unchanged; repeated captures can retain additional generation
receipts. Disk/vintage growth and unchanged-source short-circuiting need a
separate review before scheduling unattended whole-catalog refreshes.

The constrained Linux workload includes eight actual histories, including the
large H41/G17 archives and BoE daily rates. Capture/parsing and loaded-backend
ingestion are measured separately; the full 185 actual histories are not all
downloaded in CI. Final results and this limitation are reported with the review.
CI conclusions, draft PR links and the commit SHA are reported with the review.
Production requires explicit merge/deploy/migration/ingestion/display approval.

The existing Investigate safety limit of 2,000 native records per series is
unchanged. Long daily MAX/10Y comparisons can require a shorter selected range;
they fail explicitly rather than silently truncate or resample. Full stored
histories remain accessible through paginated observation queries. Expanding
that comparison limit needs a separate measured workload change.

## Local review

The completed disposable database is outside git. With backend dependencies
installed, from the repository root:

```powershell
python -m scripts.serve_expansion_preview --workspace C:/Users/algba/Documents/Codex/expansion-development --database-name disposable-release-v11.sqlite3
```

In a second terminal, from `frontend-v2`, build/start with
`MACROLENS_V2_API_URL=http://127.0.0.1:8140` and port 3040. On PowerShell:

```powershell
$env:MACROLENS_V2_API_URL='http://127.0.0.1:8140'
npm run build:preview
node node_modules/next/dist/bin/next start -H 127.0.0.1 -p 3040
```

Open `http://127.0.0.1:3040`. This is an operator-run development preview, not a
claim that a local frontend process is currently running. Production data is not
copied into it; legacy IDs remain listed but their histories are intentionally
unavailable in this isolated preview. CI exercises existing behaviour separately
with local fixtures, plus real-source desktop/mobile charts and saved research.
