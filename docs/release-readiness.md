# Discovery Radar integration and release gate

The later [deployment checklist](deployment-checklist.md) supersedes the runtime
blocker below with the proposed exact Python 3.12.15 configuration and records
clean-environment verification, credential requirements and manual rollout steps.

## Dependency and merge order

Checked 2026-10-24: PR #5 is open against main at
`144da038a0dd1c14ea1f59800862e46f9af8ef2d`; PR #6 targets
`feature/discovery-engine-phase1`. Git ancestry confirms Phase 1 is an ancestor
of Phase 2. This pass modifies PR #6 only. Neither is deployed or merged.

1. Review/approve PR #5 and the Phase 1 limitations. Merge #5 into main first,
   preferably with a merge commit to preserve the stacked ancestry.
2. Retarget PR #6 to main and verify its diff contains only Phase 2/integration
   changes. If #5 is squash/rebase merged, rebase only the Phase 2 commits onto
   main (`git rebase --onto origin/main origin/feature/discovery-engine-phase1
   feature/discovery-radar-phase2`) before retargeting; review any conflicts.
3. Require green CI for #6 against the resulting main and review this checklist.
   Merge #6 only after explicit approval. Do not delete the Phase 1 branch until
   retargeting/rebasing is complete.
4. Review Render auto-deploy settings before either merge if merges must not
   trigger deployment. No live hosting settings were accessed or changed here.

## Ranking and definitions

Latest discoveries (default) sorts by reference/observation date, then research
priority. Most unusual discoveries sorts by absolute-change historical percentile
for sudden anomalies and same-duration cumulative-change percentile for trends.
Both apply category/type/date filters first, then select at most one discovery
per dataset, up to five. Missing percentiles sort last. This is empirical
historical unusualness, not a predictive probability. Economic reference dates
are not release dates; a newly published reference period may predate a market
observation. Exact release-time ranking remains deferred until metadata exists.

| Indicator | Primary | Compatible fallback | Raw unit / adjustment | Transformation |
|---|---|---|---|---|
| Unemployment | BLS LNS14000000 | FRED UNRATE | Percent of civilian labor force, age 16+, U-3, seasonally adjusted | Level; signal changes are percentage points |
| Inflation | BLS CUUR0000SA0 | FRED CPIAUCNS | CPI-U, all items, US city average, index 1982–84=100, **not seasonally adjusted** | 100 × (index / index 12 calendar months earlier − 1); changes are percentage points of YoY inflation |

Do not substitute CPIAUCSL (seasonally adjusted) or CPILFESL (core CPI). YoY
inflation uses month-key matching, including leap years; absent months stay
missing. It is not a seasonally adjusted MoM price-inflation measure. FRED
reference dates are normalized to month end before the same transformation.
Providers can carry different revision/update timing despite identical concepts.

Definition references:
- https://www.bls.gov/cpi/factsheets/cpi-series-ids.htm
- https://fred.stlouisfed.org/series/UNRATE (explicit BLS source code LNS14000000)
- https://fred.stlouisfed.org/series/CPIAUCNS

## BLS investigation, retry, cache and fallback

Live reproduction: both a small POST (LNS14000000, 2025–2026) and documented
single-series GET returned HTTP 503, HTML content, and no Retry-After header.
The response does not establish whether the cause is BLS, an intermediary, or
this host's outbound path. It is not evidence that the series definition or API
key is invalid. Credentialed/provider-success checks are still needed elsewhere.
API request form follows https://www.bls.gov/developers/api_signature_v2.htm .

BLS now retries HTTP 429/500/502/503/504 and connection/timeouts at most three
times, waiting 1 then 2 seconds, with 5-second connect / 10-second read timeouts.
Other HTTP failures, invalid JSON and application-level query failures do not
blindly retry. At worst each chunk consumes three bounded network attempts.
There is no continuous polling or new background service.

Fresh BLS disk snapshots are reused for one day and the existing BLS memory cache
for one hour. Atomic file replacement avoids partially written snapshots. If a
request fails, an existing snapshot may be returned with explicit stale/error
metadata; it is never labelled live. Numeric missing observations remain NaN.
Radar caches scan results (including unavailable states) for five minutes, giving
failed providers a cooldown. Refresh clears Radar and provider memory caches;
fresh disk snapshots are intentionally retained. Disk cache is best effort on
Render's ephemeral filesystem, not a persistence guarantee. Related comparison
results retain their existing 30-minute cache.

If BLS fails/returns no data or falls back to stale disk data **and a FRED key is
configured**, Radar tries only the compatible mapping in the table. Fallback
provider/series and original BLS failure are recorded in diagnostics and source
labels. If FRED also fails, explicit stale BLS data can be shown; otherwise the
indicator stays unavailable. Cache age and last observation are separate fields.
Freshness heuristics flag >4-day markets / >60-day monthly observations; these
are not release-calendar guarantees. No values are invented. API key values and
FRED query URLs are excluded from displayed provider errors. Configure the FRED
key via FRED_API_KEY or `[fred].api_key` in existing Streamlit secrets.

Data-source status and definitions on Radar shows credential-presence booleans
only, cache/retry policy, expected economic definitions, latest observation,
staleness, actual provider/fallback, and failure/action text. Observation dates
and unknown release timestamps remain distinct.

## Render compatibility

The repository's render.yaml has a free Python web service tracking main and
`streamlit run app.py`. This pass supplies the missing build command
`pip install -r requirements.txt`; no hosting infrastructure or paid resources
are added. Existing package requirements now explicitly require pandas >=2.2
and Streamlit >=1.40 for used period aliases/testing/UI APIs.

**Deployment blocker:** PYTHON_VERSION is still the existing partial `3.10`.
Render requires a fully qualified environment version; Python 3.10 reached end
of life on 2026-10-01. Select/review a supported full runtime version (3.12 is
the locally tested family), then rerun CI and a staging build with that exact
runtime. This pass does not silently change the production runtime or inspect
Render Dashboard overrides. References:
- https://render.com/docs/python-version
- https://render.com/docs/troubleshooting-python-deploys
- https://www.python.org/downloads/release/python-31022/

Local checks use Python 3.12 and the existing installed requirements; pip check
passes. Requirements remain ranges/unpinned, so clean CI and staging resolution
are release gates, not a guarantee about future dependency versions. A native
Python 3.10 interpreter is not available locally; CI covers that family.
An additional Linux CPython 3.10 binary-wheel dry-run resolved all requirements
successfully (including pandas 2.3.2 and Streamlit 1.65). This verifies package
resolution, not execution on Render; the machine-readable report is retained
with the local verification outputs.

## Verification and remaining release gates

27 credential-free automated tests pass locally, including bounded retries,
non-retryable errors, explicit stale-cache behavior, fresh-cache request avoidance,
matching FRED definitions and date normalization, safe unavailable diagnostics,
ranking modes and the **full app.py navigation**: Radar → gold investigation →
gold/dollar/silver comparison → ranking change → Calendar → Radar. API results
are fixtures in tests only; a dummy OpenAI key permits route initialization
without sending requests. This is not a verification of Ask MacroLens responses.

The GitHub workflow tests Python 3.10 and 3.12 on Ubuntu, installs the repository
requirements, runs pip check and all unittest cases, with read-only repository
permissions. No live API credentials are required and it does not deploy. CI
results must be green on the final reviewed head; workflow creation alone does
not certify a passing run.

Before safe deployment:
- Approve the merge order above; keep both PRs unmerged until reviewed.
- Resolve the full supported Render runtime version and verify actual service
  settings/build command. Run a clean staging build for that exact version.
- Require green CI on the final branch/head and review dependency resolution.
- Configure existing credentials privately; verify actual BLS or compatible FRED
  economic retrieval and a credentialed Ask MacroLens response. BLS remains 503
  here and live FRED fallback is unverified because no key is configured.
- Check the live navigation/comparison workflow in the target deployment and
  review stale/unavailable warnings; no merge or deployment was performed here.

No Phase 3 features were introduced. Exact exchange/release calendars, historical
vintages, statistical relationship detection and research personalization remain
deferred.
