# Targeted readiness corrections (audit schema 1.1)

Code-only follow-up to PR #15. Detailed production findings and operator report
contents are not committed or published. No production writes, refresh setting
changes, observations, migrations, permissions, ingestion, merge or deployment.

## Methodology changes

- Existing Yahoo market definitions can have seasonal adjustment **not applicable**.
  This is separate from unknown economic-series adjustment and from dividend or
  futures-roll adjustments. Preserve the original null and add applicability; do
  not fabricate SA/NSA metadata or relax history thresholds/rights/integrity checks.
- Expose history sufficiency, publication validity, integrity validity and applicable
  metadata completeness separately. An unsupported metadata gate no longer creates
  an inaccurate insufficient-history warning. Numerical lookup and rolling
  relationship fields are additive; existing three capability keys/statuses remain.
- Keep raw nulls, but count analytical-grid missing periods separately. Nulls on
  excluded calendar dates do not automatically prove a gap. Record leading,
  trailing and internal missing periods and bounded gap examples. Calendar
  uncertainty remains explicit; no gap or extreme value is filled/deleted.
- Native coarse-lag review uses the validated end of the measured reference period,
  not its start. This is still a review threshold, not a verified publication date.
- Distinguish recorded success followed by failures from incomplete success
  telemetry. Do not label absent success timestamps as provider failures or infer
  recovery from an earlier successful check.

## Reusable descriptive metadata review

`backend.app.catalog.research_metadata` consumes existing canonical registry rows;
it does not register datasets or manage publication, AI or Discovery permission.
`catalog/research_metadata.json` starts with an empty review list. No automatic
prose generation, provider crawling, guessed seasonal adjustment or release dates.

`resolve(row)` returns canonical source identity, geography, units/scaling,
frequency, adjustment, native reference calendar, existing definition and evidence.
Unverified observation/publication/revision explanations remain null. Future
Explorer/Investigate/Discovery/Ask consumers must use their existing permission
boundary before calling it. No public API/UI changes are made in this phase.

A reviewed overlay must contain exactly these fields:

`id`, `identity_sha256`, `definition`, `observation_convention`,
`publication_behavior`, `revision_behavior`, `references`, `reviewed_at`, `reviewer`.

The identity digest binds the review to the canonical source selector, geography,
units, multiplier, frequency, adjustment and native definition hash. Changed
definitions reject outdated overlays. Named reviewer, timezone-aware review time
and HTTPS source references are mandatory. Unknown behaviors must remain null.
Unknown/permission fields and duplicate IDs are rejected. The workflow is a normal
reviewed PR, never an ingestion or grant action.

To build a prioritized review queue and provider breakdown from an operator-supplied
report in a local checkout, using existing dependencies:

```bash
python -m scripts.analyze_readiness_report \
  --audit /PATH/TO/SUPPLIED/audit.json \
  --output /NEW/LOCAL/REPORT/DIRECTORY
```

This reads reports and canonical metadata only. Outputs are `findings.json`,
`findings.md`, and `metadata-review-queue.json`. Keep operational report contents
outside git; the tool never publishes or uploads them. Origin remains explicitly
operator-declared; fixture input is labelled fixture, not production revalidation.
Prioritize missing definitions coupled with gap/lag interpretation, then remaining
definitions, batching reviews by provider/table family. Labels and selectors are
review evidence, not complete economic explanations. Reuse existing reviewed
definition notes and suitability evidence before researching missing prose.

## Safe focused Render diagnostics, without deployment

This stdlib-only script reads just the cached refresh evidence for the six named
legacy exceptions. It makes no provider requests and exports only allowlisted
timestamps/status/booleans. Raw provider warnings, errors, credentials and
observations are not exported. A recorded truncation guard is evidence of the
guard firing, not approval to disable it or trim history.

In the backend Render Shell:

```bash
set -eu
cd /opt/render/project/src
test "$(git rev-parse HEAD)" = 'cb7a03cded7113231fe1bac42beadff0e92a274a'
DIAG_WORK="$(mktemp -d /tmp/macrolens-refresh-diagnostics.XXXXXX)"
curl --fail --silent --show-error --location --max-time 60 \
  'https://raw.githubusercontent.com/thealexbfx/macro-dashboard/e7942d35018c5d28218768e2f3f0c3f413f40b98/scripts/readiness_refresh_diagnostics.py' \
  --output "$DIAG_WORK/diagnostics.py"
printf '%s  %s\n' \
  '19770a8f6e983c1bf7e48a17f68cf0e79eae62d3651508f2c388b626104dd509' \
  "$DIAG_WORK/diagnostics.py" | sha256sum --check -
PYTHONDONTWRITEBYTECODE=1 python -B "$DIAG_WORK/diagnostics.py" \
  --database /var/data/macrolens-v2.sqlite3 > "$DIAG_WORK/refresh.json"
printf 'Review/download diagnostic output: %s/refresh.json\n' "$DIAG_WORK"
```

Stop if revision or checksum differs. The only network call downloads the reviewed
program. SQLite uses `mode=ro`, `query_only`, a read-only authorizer, one transaction,
two-second lock timeout and ten-second SQL deadline; each cached payload is bounded
to 16 MiB. Normal read locks/WAL bookkeeping apply. No worker initialization,
checkpoint, migration, repair, deployment, settings change or source refresh.
Download the result before `/tmp` is cleared; the script does not upload it.

The original v1.0 full-audit runbook remains pinned and unchanged. Audit v1.1 adds
the descriptive helper and review file: **do not download only readiness.py and
execute it against old deployed libraries**. Run v1.1 from a complete reviewed
checkout using the existing Python dependencies, against an existing consistent
backup, or after separately reviewing an isolated temporary checkout for a live
read. No production migration or application deployment is needed for either read.

## Validation and scope boundary

Full backend: **500 passed**, including **12 new correction tests**. Final audit
and correction subset: **36 passed**. Ruff checks/formatting and whitespace checks
pass. Existing Starlette/NumPy warnings remain. Initial broader runs stalled at
Windows loopback event-loop initialization; they were interrupted and successfully
rerun after permitting the local test socket. No application workaround was added.

Tests cover not-applicable versus unknown adjustment, preserved publication and
integrity gates, no inaccurate history warning, calendar-excluded nulls, boundary
versus internal gaps, annual reference-end age, definition-bound overlays, forbidden
permission fields, noninvented queue facts, safe diagnostics, fixture labelling,
and the inherited read-only/full-public-release regressions.

Limitations remain visible: instrument definitions, rolling source windows,
calendar/release uncertainty, real shocks/revisions/method breaks, paired overlap,
transformation warm-up, compatible units/frequency, complete rolling windows,
effective samples, stability, latest-vintage data and lack of causal certification.
Capability fields never grant research permissions. Metadata review and additional
production diagnostics remain follow-up evidence, not a reason to change source
schedules or prolong an unrestricted cleaning project.
