# Targeted legacy refresh reconciliation

This change is prepared for review in PR #16 above the read-only audit PR #15.
It does not deploy, merge, migrate, edit production data/permissions/schedules,
run a production ingestion, add datasets or activate AI. Detailed operator
production findings remain outside the repository.

## Exact failure path and source evidence

`scheduled_service_class` loads the last-good persistent history into the
DataService cache for a due check. `V2PublicProvider.fred_series` requests the full
graph CSV for the registered `id`; there is no requested short `cosd`/`coed` slice.
DataService then checks whether every previously valid observation inside its
requested history still exists and is nonmissing. A failure rejects the entire
candidate and preserves last-good data, retrieval time and previous success.

The two exact source IDs BAMLH0A0HYM2 and BAMLC0A0CM have a documented three-year
availability limit. A moving left boundary can therefore remove formerly available
source dates without an outage. Treating the response as an all-history replacement
blocks otherwise valid updates/revisions. Sources:

- https://fred.stlouisfed.org/series/BAMLH0A0HYM2
- https://fred.stlouisfed.org/series/BAMLC0A0CM

`legacy_history.reconcile_rolling_prefix` handles only these provider/selector
contracts. When the returned start lies within seven calendar days of the
three-year calendar anniversary, earlier cached rows are retained unchanged. This
small boundary envelope accommodates source date rollover/weekends/holidays; it
does not accept a materially shorter feed. Source nulls at its returned boundary
are not hidden by an archive merge.

The combined candidate is validated again and the **existing completeness guard
runs unchanged**. Interior omissions, valid-to-null changes, tail loss and
unexpectedly shortened windows still fail. Other series get no prefix reconciliation.
New source rows and valid overlapping revisions update their exact dates; no
observations are deleted, fabricated, substituted, duplicated or interpolated.

Release metadata reports actual source coverage and retained-prefix count. Existing
quality warnings explicitly disclose that preserved older observations cannot be
reverified for revisions outside current provider availability. Successful source
checks do not certify an inaccessible historical prefix or a historical vintage.

## Legacy successful-check telemetry

The release preceding cb7a03c did not record the new explicit source-success fields.
An old `ok` cache with `retrieved_at` can consequently lack a source-success timestamp.
A cache read before its existing next-due time correctly makes no provider request.
It must not backfill or fabricate success.

Old cache responses now carry `source_check_telemetry=legacy_unverified` in memory;
the read does not rewrite the stored payload. A due source attempt must explicitly
report validation success before a new success timestamp is persisted. Missing
persistent rows cannot relabel an in-memory hit as a fresh check. Failure preserves
the earlier real timestamp, or null if no such evidence exists. Data Health no longer
uses an unqualified old retrieval timestamp as proof of successful source checking.
Intervals, backoff constants, leases and existing next-due decisions are unchanged.

## Optional bounded production difference check

This is optional evidence to distinguish leading source rollover from any additional
internal/tail loss. It cannot install responses or repair anything. The new flag
explicitly enables at most two public FRED CSV GETs after the read-only SQLite
transaction has closed. Without the flag, the diagnostic remains entirely offline.
No app imports, authentication tokens, source substitutions or observation exports.

In the **backend Render Shell**:

```bash
set -eu
cd /opt/render/project/src
test "$(git rev-parse HEAD)" = 'cb7a03cded7113231fe1bac42beadff0e92a274a'
DIAG_WORK="$(mktemp -d /tmp/macrolens-credit-coverage.XXXXXX)"
curl --fail --silent --show-error --location --max-time 60 \
  'https://raw.githubusercontent.com/thealexbfx/macro-dashboard/6ecbd91e6654ed45a3e9522c7ea533ffdb0c16ec/scripts/readiness_refresh_diagnostics.py' \
  --output "$DIAG_WORK/diagnostics.py"
printf '%s  %s\n' \
  'd58782e18dfc46c1f8e81cf18d6d057c61a82127d8fc4734c4cad5e1f33ea0ae' \
  "$DIAG_WORK/diagnostics.py" | sha256sum --check -
PYTHONDONTWRITEBYTECODE=1 python -B "$DIAG_WORK/diagnostics.py" \
  --database /var/data/macrolens-v2.sqlite3 \
  --compare-public-csv > "$DIAG_WORK/coverage.json"
printf 'Review/download: %s/coverage.json\n' "$DIAG_WORK"
```

Stop if the deployed revision or script hash differs. Download the small JSON before
`/tmp` is cleared. It contains counts, dates, allowlisted flags and at most five
missing-date examples per category; no actual observation values or raw errors.
It is not automatically uploaded or committed.

SQLite: `mode=ro`, `query_only`, read-only authorizer, ten-second SQL progress
deadline, two-second lock timeout, six bounded cache records (16 MiB each). Public
comparisons: exact two IDs/HTTPS endpoint only, no redirects or credentials,
eight-second socket timeout per response, 128 KiB response bound. Network/DNS
conditions can affect elapsed time; Ctrl-C stops the diagnostic without DB changes.
No source request is sent while a SQLite read snapshot remains open.

Read `coverage_comparison` for each credit series:

- `missing_before_source_start` counts previously valid dates outside the returned
  left boundary; those are the candidate retained prefix.
- `missing_within_or_after_source_range` must be zero to rule out additional
  interior/null/tail losses. Nonzero values remain guarded failures, not exemptions.
- `overlap_revision_count` distinguishes changed overlapping values from missingness.
- `legacy_telemetry_fields_absent` identifies old cache records without success
  telemetry; status/retrieval alone is not converted into historical success.

An unavailable/invalid response yields an explicit diagnostic failure, never a
successful comparison. This command does not trigger the application refresh path,
write a new successful-check timestamp, reset failure counters or change next_due.

## Validation and handoff

Full backend: **522 passed**, including **22 new synthetic regression cases**.
Final targeted refresh/readiness subset: **34 passed**. Ruff checks/formatting and
whitespace checks pass; existing Starlette and degenerate-correlation warnings remain.
Tests cover both exact series, lossless prefix retention, real overlap revision
semantics, restart persistence, internal/null/tail/left-boundary losses, shortened
feeds, transport failure, unchanged backoff, nonapproved series, leap-day boundary,
legacy cache reads with no writes, failure without invented success, subsequent
actual success, Data Health, optional bounded comparisons and identity/size limits.

No catalog-wide data issue established by this work blocks the Research Journey MVP.
Do not call stale credit data fresh before an approved rollout and normal scheduled
check confirm recovery. Inaccessible-prefix revisions, source calendars, provenance
and actual comparison overlap remain explicit limitations. They can be handled as
dataset-level restrictions while the complete research workflow proceeds with
already-permitted, dependable data. No unrelated cleaning or expansion is required.
