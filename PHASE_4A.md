# Phase 4A — internal ingestion foundation

Implemented on `feature/macrolens-v2`. No deployment, merge, production database operation, Render/environment change, paid service or AI enablement. Existing public V2 registry remains exactly 30 datasets. This phase adds **only three internal World Bank monthly series**; it does not ingest the remaining research catalog or gap selections.

## Structure and compatibility

- `backend/app/ingestion/contracts.py`: adapter protocol, immutable series/point/batch contracts and safe provider errors. Future monthly OECD/Eurostat/ONS/JODI/EIA adapters can implement this interface; none is implemented or registered here. Other native frequencies need explicit period/window validation before activation.
- `schema.py`: five additive `ingest_*` tables: dataset definitions/rights, current normalized observations, prior observation revisions, durable jobs/cursors and run diagnostics. Existing source-cache, Discovery, research, AI and lease tables are unchanged. Schema initialization is idempotent through the existing Store.
- `world_bank.py`: one fixed official monthly Pink Sheet XLSX, only `Crude oil, Brent`, `Copper`, `Iron ore, cfr spot`. Sheet relationship, headers and units are validated; columns are found by label rather than hard-coded letters. Standard-library ZIP/XML parsing; no Excel engine or dependency additions.
- `runner.py`: one provider job per invocation, one background thread per process, existing SQLite source leases plus commit fencing. Network/parsing occurs outside write transactions. Each commit is atomic and capped at 120 months / 360 pilot observations. Durable exponential backoff, capped Retry-After and expired-worker recovery retain last good data.
- `cli.py`: explicit database path required; status, bounded local backfill and one-shot update. There is no public ingestion/permission-changing API.
- `backend/app/v2/state.py`: additive schema creation only. `main.py`: the existing supervised refresh dispatches an optional, non-blocking ingestion worker even if Discovery raises; worker stops on lifespan shutdown. Authenticated existing diagnostics include ingestion status. Provider failures do not determine `/ready` and do not stop Discovery.

**Disabled by default:** scheduler ingestion requires the new optional `MACROLENS_INGESTION_ENABLED=1`. It is not set anywhere in this change. The CLI is an explicit operator action and does not depend on this flag. No new configuration is necessary to run the existing application unchanged.

All three definitions have `public_display=0`, `ai_allowed=0`, `rights_state=unreviewed`. SQLite CHECK constraints prohibit enabling those flags in this phase. They are absent from public `SPECS`, comparisons, Dataset Explorer, Discovery and AI inputs. An approved later code/rights change is required for exposure, not a simple accidental registry append. Existing AI behavior/configuration is unchanged and AI was not enabled.

## Correctness and resource bounds

Native periods are `YYYY-MM`. Values retain source precision. Missing cells/ellipsis markers become SQL NULL with `missing` quality; there is no interpolation, forward fill or zero substitution. Invalid/nonfinite/nonpositive prices, duplicate/unordered/future periods, formulas/errors, changed units, incomplete headers, missing period rows and truncated histories are rejected. Observations with a stale source period retain explicit stale metadata; successful retrieval is not a claim of fresh economic data.

Primary key `(dataset_id,period)` prevents duplicates. Changed values or quality preserve the old value/quality with its revision number and capture time, then update current state atomically. These are **captured revisions**, not fabricated historical publication vintages. Metadata-only changes do not create observation revisions. Last success is distinct from attempts/errors. Abandoned jobs are marked after lease expiry, then resume their committed cursor; workers with lost leases cannot commit.

Initial and monthly full reconciliations use resumable 120-month slices. Changed normal updates examine the latest 24 months; older revisions can therefore wait until the next monthly reconciliation. Unchanged daily files skip observation writes, without postponing monthly reconciliation. Normal completed checks are daily; backfill continuation is due in 60 seconds. The adapter caches one parsed batch for five minutes during backfill; source-check timestamp remains the actual fetch time, not every cached invocation.

Bounds: 4 MiB HTTP body, 16 MiB expanded archive, 8 MiB per member, 100 archive members, 20,000 shared strings, 150,000 selected-sheet cells, 1,200 monthly periods, 5,000 batch observations. Reject DTD/entities, encrypted archives, external sheet targets and redirects. HTTP connect/read timeouts are 5/10 seconds with a 25-second streaming deadline checked between chunks. Slow/blocked reads may consume one extra read timeout. A single worker prevents concurrent parser copies; use the existing single backend worker configuration, not extra ingestion services.

No raw workbook is retained by the running service. It stores source URL/hash, downloaded size, actual check time and parser version, rather than a copy on every run. Ingestion stops safely at a combined DB/WAL-family size of 256 MiB or less than 64 MiB free disk. This is a conservative admission guard, not a quota on unrelated existing research writes. It deletes no observations or research. Revision/run rows accumulate; monitor growth before expanding scope on the 1 GB disk.

## Actual pilot demonstration (28 October 2026)

Official source: `https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx`

Source SHA256: `ea1c350827878ea3bbe30e3cda16a13fd3bd5b409b8458940dc94a36b5a33154`; download 586,099 bytes. Demonstration used a separate `work/phase4a-demo.sqlite3` outside the repository, never the configured application/production database. Every stored period/value/quality was compared with a fresh parsed response.

| Dataset ID | Stored periods | Source unit label | Missing cells | Latest source value (2026-09) |
|---|---|---|---:|---:|
| `wb_brent_monthly` | 801, 1960-01 through 2026-09 | `($/bbl)` | 0 | 116.8 |
| `wb_copper_monthly` | 801, 1960-01 through 2026-09 | `($/mt)` | 0 | 14474 |
| `wb_iron_ore_monthly` | 801, 1960-01 through 2026-09 | `($/dmtu)` — disputed | 0 | 97.7 |

Seven commits stored 2,403 observations. Rechecking unchanged data inserted/revised zero rows. SQLite including its empty legacy schema occupies 602,112 bytes (588 KiB); this is total demonstration size, not an exact production migration delta. Instrumented download/parse took 1.344 s, Python allocation peak 9,890,775 bytes, standalone Windows process peak working set 47,857,664 bytes. Separate unchanged check took 0.479 s. These are local single-run measurements, not Linux/Render/full FastAPI load guarantees.

### Licensing and technical blockers

1. **Public display and AI remain blocked for all three.** The workbook names third-party suppliers (including financial-market vendors); public download access alone does not establish redistribution or AI permissions. This phase performs no new rights research or purchases.
2. **Iron-ore unit conflict:** actual selected column `Iron ore, cfr spot` is labelled `($/dmtu)`, while Description defines recent spot prices as USD/dry ton. Store raw values with `unit_review` quality, both source-label/description warning, and no conversion. No assertion that historical prices share a constant benchmark specification. This corrects an assumption in the proposal without silently changing the catalog or underlying numbers.
3. The URL is pinned to the verified official attachment. If World Bank rotates its attachment or changes units/labels, fail visibly and retain history; review a replacement rather than scraping arbitrary links.
4. Pre-1990 native history is internal only; public V2's existing range/frequency contracts are unchanged. Additional providers/frequencies, public observation routes and broader ingestion remain out of scope.
5. Validate combined FastAPI/Discovery/ingestion RSS on a staging-equivalent 512 MB Linux instance and actual disk headroom before opting in. No claim that this Windows standalone measurement certifies production capacity.

## Reproduce locally

From repository root with existing backend dependencies installed (no new dependencies):

```powershell
# Explicit disposable database; never omit --database or point at production.
python -m backend.app.ingestion.cli --database ../phase4a-demo.sqlite3 --backfill
python -m backend.app.ingestion.cli --database ../phase4a-demo.sqlite3 --update
python -m backend.app.ingestion.cli --database ../phase4a-demo.sqlite3
python -m pytest backend/tests/test_phase4a_ingestion.py backend/tests/test_v32_readiness.py -q
```

`--backfill` performs at most 12 slices and stops immediately on failure. `--update` is an explicit check overriding due time; normal background jobs respect backoff. For a **local** scheduled demonstration, point `MACROLENS_V2_STATE_DB` at another disposable local database, set `MACROLENS_INGESTION_ENABLED=1` only in that local shell, keep AI disabled, and start the existing `backend.app.v2.main:app`. Nothing in this change edits environment files or starts a production server.

## Validation

- Full Python suite: **552 passed, 5 live checks skipped**. Includes **34 new ingestion tests** plus existing scheduler, integrity, Discovery and saved-research coverage.
- Initial Windows runs hit denied OS temporary/cache paths; redirecting TEMP/TMP and pytest basetemp into the workspace resolved those infrastructure errors, with no product-code workaround.
- Focused ingestion + existing production-readiness regressions: **57 passed**.
- New tests cover revisions/withdrawals, unchanged hashes, old-revision monthly reconciliation, duplicates, restart cursors, source outages, Retry-After, expired lease fencing, atomic rollback, storage admission, unsafe/malformed XLSX, unit changes, nulls, stale/future periods, default-off/public/AI gates and worker recovery.
- Ruff: repository CI fatal-error rules and full rules for the new package/tests pass. Python compilation passes. Frontend V2 unit tests: **46 passed**; no frontend files changed. Real fetching was an explicit local demonstration; offline automated tests use synthetic XLSX files and disposable databases.

## Safe release and rollback — instructions only, not executed

1. Review/approve code and CI. Keep AI disabled and ingestion opt-in unset for the first compatibility release. Do not merge or deploy automatically.
2. Before an approved release, create a **consistent SQLite backup using the SQLite backup API**, not a plain copy of the live main DB while WAL is active. Store the backup off the 1 GB disk if necessary; verify integrity and restore on a disposable location. Record space/row counts for existing library/stories/source cache. No backup or production DB operation was performed here.
3. On startup the additive schema creates only new `ingest_*` tables/indexes. There are no DROP/DELETE/ALTER operations on existing state. The new tables can remain with ingestion disabled. Check `/ready`, existing 30 datasets, Discovery and saved research against the pre-release counts.
4. Only after separate approval, enable the internal pilot on the existing service. This is an optional new environment setting requiring operator approval; no setting was changed here. Run a small bounded job, inspect authenticated diagnostics/CLI, space, RSS and captured metadata, then allow the rest of the pilot backfill. Public/AI CHECK constraints remain denied regardless of worker opt-in.
5. To pause ingestion, disable the opt-in and restart gracefully; an active bounded job may finish atomically. To roll back code, use the prior approved revision; it ignores the additional tables. **Leave the tables and their observations in place. Do not drop, reset, delete, or replace the production SQLite database.** Old research remains available. Restore a backup only for an actual recovery incident with separate approval and reconciliation of research created since the backup.
