# Batch 0 Part 3 — catalog integration review

Base: `5ae4836086d4358bb380b636e4a90f5b3a1374fc`. Development only,
`feature/macrolens-batch0-foundation`, draft PR #9. No production operations.

## Read boundary and compatibility

* `PublicCatalog` loads the existing 309-entry planning manifest, retaining all
  30 legacy public IDs. Public counts/facets/search contain authorized records
  only; the 279 real nonpublic manifest IDs cannot be discovered or read by ID.
* `GET /api/v2/catalog`, `POST /api/v2/catalog/search`: metadata pages, maximum
  100 entries (Explorer uses 12), filters for text/category/region/provider/native
  frequency. Favourites filter accepts at most 400 IDs. No provider/history fetch
  during metadata listing. Retired/private favourites remain in local storage.
* `GET /api/v2/catalog/{id}` resolves selected/saved metadata independently of
  the visible page. Unknown and private IDs use the same 404 response.
* `GET /api/v2/observations/{id}`: explicit start/end dates, limit <=1,000,
  offset <=100,000, `next_offset`/`has_more`; tail previews <=40 points.
  Selection uses native reference-period **start** dates, UTC instants for events.
  Previews never fill missing periods. Legacy source-cache JSON is sliced inside
  SQLite; a cold/expired request refreshes only its requested legacy source.
* Existing `/datasets` and legacy-only `/compare` routes and calculations remain
  intact. Native comparisons authorize all IDs before fetching, cap at 2,000
  source rows per series, retain null/zero/negative values and source labels,
  and never silently decimate or resample. Oversized ranges require a shorter
  range; paginated observation retrieval remains available separately.
* Native correlations require identical reviewed frequency/calendar and exact
  reference dates. Mixed-frequency charts remain native, with no correlation
  asserted across incompatible calendars. Events render as discrete points and
  simultaneous distinct event identities survive. Changes require exact prior
  periods (including gaps and zero-base handling); yearly daily/weekly changes
  require the exact date a calendar year earlier, not guessed trading sessions.
* Legacy lead-lag, session/calendar analyses and explicit period-end alignment
  are preserved. Native catalog comparisons explicitly reject these conversions
  until source-specific semantics are reviewed. API errors explain this limit.
* Explorer fetches visible previews with at most three requests in flight.
  Short metadata/range reads have a separate two-reader bound, so they cannot
  queue behind a complete Discovery calculation. Heavy analysis retains its
  existing one-worker limit and the global HTTP admission bounds are unchanged.
  Saved references/settings are hydrated on reopening; missing/private IDs are
  identified without deleting or remapping saved research.

## Publication, source integrity and migration safety

`NATIVE_PUBLICATIONS` is **empty**. The World Bank stored presentation registry
remains empty. Native reads require a code-reviewed presentation definition,
matching definition/provider hash, explicit `public_display` approval and evidence,
permitted row rights, a complete active generation, and complete source-hashed
receipts. Every returned row is checked against its **own** completed generation,
staged source evidence, source URL, units/calendar, and revision lineage. A small
incremental update does not certify unrelated older rows.

Display, AI and Discovery are independent. AI/Discovery continue to use the
existing curated legacy allowlist; native public display never grants either.
No source adapters, schedulers, rights or data records are activated by this work.
The three World Bank pilots remain private, AI denied and Discovery excluded.

There is **no Part 3 migration**, schema destruction, automatic startup migration,
or production data write. Parts 1/2 additive migrations stay explicitly gated.
The existing hard-deny native schema intentionally cannot publish any real new
series: future publication requires separately reviewed rights evidence,
source/benchmark/unit validation, a reviewed activation/schema plan, explicit
operator approval and presentation registration. The test fixture relaxes only
the public/rights constraints of a newly created **disposable synthetic** table;
it cannot be imported into production application startup.

## Validation and capacity evidence

Local full Python suite and frontend lint/type-check/unit tests pass. A real
Chrome test exercises pagination/filters, saved comparisons, missing/private
references, frontend proxy denial, failed catalog requests/recovery and desktop/
mobile rendering, including native event markers. An empty economic-headline object discovered by this test now
renders Unavailable rather than crashing.

The full-catalog fixture contains 30 legacy definitions plus 279 fake reviewed
native datasets (daily, weekly, monthly, quarterly, fiscal, annual, event and
irregular), 120 observations each plus simultaneous events. No actual provider
requests or real approvals. Tests separately exercise every real manifest ID,
revision provenance, backup/restore, pagination and independent privacy gates.

Linux validation runs this fixture over HTTP with the real Discovery scheduler,
bounded reads/comparisons and burst overload, inside Docker with **512 MiB,
no swap, 0.5 CPU**, network disabled. It reports backend RSS/HWM, cgroup peak,
database/WAL/SHM, response sizes/latency, controlled 503s and graceful shutdown.
It distinguishes paced interactive reads from unpaced concurrent mixed-analysis
and 24-client overload bursts; sampled peak database/WAL/SHM sizes are recorded
at 100 ms intervals. Such sampled peaks are lower bounds on instantaneous file size.
The existing ingestion-enabled/disabled combined scheduler harness also remains
required. CI retains measurement JSON and browser screenshots for seven days.
Exact final results are recorded in the PR review report after CI concludes.

## Review, future rollout and rollback

1. Review Part 3 diff and final Linux CI results; keep PR #9 draft. No merge or
   deployment is authorized by this report.
2. Before any subsequent rights-cleared batch: clear source-specific redistribution
   rights separately from AI rights, finalize atomic selectors/calendar/unit
   benchmarks, confirm completeness window and freshness expectations, and review
   the explicit publication activation plan. Iron-ore benchmark/unit history
   and World Bank underlying third-party rights remain unresolved.
3. Ingest only approved bounded batches after an independent backup/restore and
   production disk-headroom check. No such ingestion occurs here. Re-measure
   resource use against actual per-source histories/provider payloads: hundreds
   of long daily histories and live provider latency are not proved by fixtures.
4. Roll back application code to the pre-Part-3 revision if needed; do not drop
   additive tables, replace SQLite, clear caches/history or reverse permissions.
   Existing public endpoints and legacy data remain readable by the old code.
5. No deployment upgrade is assumed. Saturation should produce retryable 503s,
   not unbounded jobs. Capacity/release approval depends on measured CI results
   and later real-source batch profiling, not just a passing small fixture.
