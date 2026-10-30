# World Bank private-ingestion readiness

29 October 2026 UTC (28 October America/Chicago).
Development branch: feature/macrolens-v2.
Application/test commit: bd0a01cc15ad11a398ac46c6080f1b6c53313e5a.
Production remains at c9ca57f3ad0c715b60a6f8e9645563723c72f0c2 per the operator's supplied status; no production operation was performed here.

## Decision

The code is suitable for a **controlled private ingestion test after approval and a successful read-only fetch from the Render runtime**. Do not enable scheduled production ingestion yet. Target-runtime access is still unverified; a single successful fetch would validate access at that time, not ongoing reliability.

No deployment, merge, production DB access, environment change, AI enablement, public exposure or new provider occurred. The optional flag remains default-off. All three pilot definitions retain public_display=0, ai_allowed=0 and unreviewed rights. The 30 public definitions and application workflows were unchanged.

## Download failure: reproduced and narrowed

A new [Ubuntu CI diagnostic](https://github.com/thealexbfx/macro-dashboard/actions/runs/40805513333) made two independent ordinary GETs to the same fixed official attachment from the same runner:

| Client | Response | Redirect | Edge classification | Challenge header |
| --- | --- | --- | --- | --- |
| Existing application requests.Session adapter | 200, genuine XLSX | None | Cloudflare | Not present |
| Original CI urllib client | 403 | None | Cloudflare | Not present |

The requests response parsed all 2,403 points and matched the Phase 4A SHA-256. This reproduces the original client-dependent HTTP denial. It rules out an unavailable workbook URL or an XLSX parsing failure as the cause of that CI error. **The exact server-side rejection rule is not known**: it may depend on HTTP/TLS/client characteristics, but this evidence cannot isolate User-Agent, another header or a specific edge rule. Cloudflare identification does not establish which component generated the denial. It was not an explicit cf-mitigated challenge.

The adapter already used requests; it was never necessary to change providers, impersonate a browser, solve a challenge, rotate proxies or loosen TLS. The original CI setup used urllib before the actual backend was launched. The new access workflow uses the actual adapter as its success criterion; urllib is an explicitly reported comparison, not an ingestion fallback. Its 403 is visible even when the adapter succeeds.

Additional local checks: default requests GET, HEAD, and GET with a normal XLSX Accept header all returned 200 without redirects; no browser cookies or credentials were supplied. The actual updated adapter also succeeded. Local urllib failed certificate verification before receiving HTTP (a separate local trust-store issue, not proof about CI's 403). Certificate verification was never disabled.

Official retrieval remains the [Monthly prices link on Commodity Markets](https://www.worldbank.org/en/research/commodity-markets):
https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx

Verified file: 586,099 bytes; SHA-256 ea1c350827878ea3bbe30e3cda16a13fd3bd5b409b8458940dc94a36b5a33154.
No alternative URL was guessed or activated. The official landing and document pages link to this same attachment; they are not independent redundant channels. If access is denied from Render, stop and seek World Bank support rather than routing around the denial.

## Targeted fixes and files

1. backend/app/ingestion/world_bank.py:
   - Parse both Retry-After delta-seconds and HTTP-date, clamp to one day, reject malformed/oversized header values without unbounded integer parsing.
   - Reject unexpected Content-Type, including a 200 HTML login/challenge page, before reading its body. Allow the actual XLSX MIME, generic ZIP/octet-stream and absent MIME only through the existing strict workbook validator.
   - Reject declared oversize Content-Length before reading; retain the authoritative streaming body limit.
   - Distinguish TLS, timeout and other transport errors using safe codes. Capture only fixed diagnostic categories: status, known MIME, redirect boolean, Cloudflare classification and explicit challenge boolean. Never return arbitrary response headers, bodies, cookie/auth values or exception text.
2. scripts/probe_worldbank_access.py: bounded official download/parser check with no Store, SQLite, worker, CLI ingestion or AI import. Optional one-request urllib comparison disables redirects and never reads a denied body.
3. backend/tests/test_worldbank_transport.py: 32 regression cases, including 403/redirect denial, safe diagnostic output, HTTP-date durable backoff, last-good preservation/recovery, MIME/body limits, expired-cache failure and transport classification.
4. .github/workflows/worldbank-access-check.yml: credential-free Ubuntu diagnostic, five-minute job timeout, one request per selected client and no application services/database.
5. This report.

No database/API schema change, new runtime dependency, data conversion, source substitution or UI change. Existing durable provider jobs, cursors, revisions and worker implementation are reused.

## Idempotence, recovery and resource bounds

A new **disposable local** database backfilled seven atomic slices (six of 360 rows, one of 243), storing exactly 801 periods per series, January 1960–September 2026. A separate fresh unchanged download inserted/revised zero rows. All 2,403 observations remained, revision count zero, integrity_check=ok, three private/AI-denied registry rows. Total disposable database size: 602,112 bytes. This is not a production size estimate or a production backup.

Existing regressions still verify changed values/withdrawals preserve prior revisions, expired-worker fencing, duplicate prevention, committed cursor recovery, malformed/outage last-good preservation, scheduler independence and cancellation. The new HTTP-date test proves durable next_due respects a 900-second provider delay, does no inline retry, then recovers unchanged without altering observations.

A 403 is recorded as http_403 and deferred through existing exponential backoff; it is not retried inline or through another client. Expired parsed-cache data is not returned as a successful fetch after a failure. Last-good stored observations remain intact.

Unchanged limits: one ingestion worker, 120-month/360-observation commits, 4 MiB HTTP body, 16 MiB expanded XLSX, member/cell/period caps, 5/10-second connect/read timeouts with a streaming deadline, no redirects, bounded DB waits and storage admission guards. No additional process, source history or concurrency setting was introduced.

## Definition and rights review

The current file hash matches the workbook whose Description sheet was inspected locally in Phase 4D. No benchmark conversion or seasonal adjustment was applied. Each selected column currently contains 801 nonmissing rows.

| Selector | Description / native unit | Treatment |
| --- | --- | --- |
| Crude oil, Brent | UK Brent, 38-degree API crude; USD/barrel | Preserve raw nominal monthly prices; supplier attribution includes Bloomberg, EIG, OPEC and World Bank |
| Copper | LME Grade A, minimum 99.9935% purity, cathodes/wire bar shapes, settlement price; USD/metric tonne | Preserve native values; suppliers include Bloomberg, Engineering and Mining Journal, Platts Metals Week, Thomson Reuters and World Bank |
| Iron ore, cfr spot | Descriptive spot benchmark: CFR China fines, 62% Fe from December 2008, previously 63.5% | Header says USD/dmtu but descriptions identify dry-ton spot prices and distinguish older contract data; retain unit_review on every observation, no conversion or homogeneous-history claim |

The workbook contains separate iron-ore descriptive entries for spot and older contracts (including VALE/CVRD/UNCTAD sources). The selected column's unit/history relationship remains unresolved. Do not silently relabel its 1960-present observations as one constant modern spot benchmark.

The [official catalog](https://datacatalog.worldbank.org/search/dataset/0038238/commodity-prices-history-and-projections) labels the dataset Public / CC BY 4.0. The [World Bank dataset terms](https://www.worldbank.org/ext/en/legal/terms-conditions/datasets) require attribution and retain third-party exceptions. A supplier credit alone proves neither a restriction nor a downstream grant. No express clearance of every selected supplier's redistribution or AI rights was obtained. No categorical claim is made that commercial use is prohibited: the catalog license supports reuse subject to the applicable exceptions.

Public redistribution, derived commercial research, external-model prompts/RAG and training remain for source-specific review. All pilot gates stay denied; no AI calls were made. No World Bank contact was sent and no paid source was introduced.

## Tests and Linux evidence

- New transport suite: 32 passed.
- Focused original ingestion/staging plus initial 30 transport cases: 73 passed.
- Full local Python before the final two probe-only cases: 601 passed, 5 live checks skipped. Initial long Windows paths caused tempfile errors/stalls; a short writable test directory resolved them without product changes.
- **Full Linux Python at the application commit: 603 passed, 5 skipped**, fatal lint passed.
- V2 frontend: 46 tests passed; lint, type-check and production build passed locally and in [Linux CI](https://github.com/thealexbfx/macro-dashboard/actions/runs/40805513259). Legacy frontend build passed in that CI run.
- Full Ruff rules for the changed Python files passed.
- [Updated hard-limit Linux run](https://github.com/thealexbfx/macro-dashboard/actions/runs/40805513262): both modes passed at bd0a01c with 512 MiB memory, zero swap, 0.5 CPU and a disposable approximately 1 GB filesystem. Backend clients remain outside the capped cgroup.

| Updated Linux peak | Ingestion disabled | Ingestion enabled |
| --- | ---: | ---: |
| Backend RSS | 370.56 MiB | 379.18 MiB |
| Sampled normal cgroup usage | 327.66 MiB | 338.54 MiB |
| Kernel cgroup peak including extra 64 MiB pressure probe | 396.43 MiB | 401.47 MiB |
| SQLite + WAL/SHM | 15.88 MiB | 23.42 MiB |

No OOM kills or unhandled HTTP 500 occurred. Deliberate concurrent saturation still produced controlled 503s (18 disabled / 21 enabled across unequal scenarios, including failed-readiness probes). Successful warm-phase p95 was 3.403 / 2.296 seconds; this is not a causal ingestion speed comparison. Warm CPU approached the half-core allocation; enabled scheduler-idle CPU averaged 1.38% of one core. Shutdown during a stalled fetch completed in 3.528 seconds; restart, lease/cursor/revision recovery and saved research preservation passed. The kernel high-water mark includes pressure; the normal figure is sampled, not a separate continuous peak. Container runtime version metadata limitations from Phase 4C still apply. These results support the small bounded pilot only, not a catalog/concurrency expansion.

The resource workload is synthetic and network-isolated; the separate live-access job validates official parsing/transport. Neither contacts the production service. Linux cgroup testing does not certify Render-specific network access, long-run history growth or every traffic level.

## Proposed approval boundary — no production commands executed

The next production operation should be **one read-only official workbook fetch using the already-deployed adapter**, not a backfill and not an environment change. At current c9ca57f the newly added probe is not deployed; an operator can run this minimal existing-code check after explicit approval:

```python
from backend.app.ingestion.world_bank import WorldBank
from backend.app.ingestion.contracts import ProviderError

try:
    batch = WorldBank().fetch()
    print({"ok": True, "bytes": batch.byte_count,
           "sha256": batch.source_hash, "points": len(batch.points)})
except ProviderError as error:
    print({"ok": False, "error_code": error.code})
```

This imports the provider only, opens no SQLite connection and does not enable ingestion or AI. It is subject to explicit operator approval and authenticated Render shell access, neither supplied/exercised in this task. If successful, capture sanitized result/runtime evidence and seek separate approval for a bounded private ingestion write. Keep scheduled ingestion off throughout that first test.

Before any write, reconfirm the backup/restore evidence and disk/memory baseline; the operator reports a restore-tested same-disk backup but no off-Render copy. Prefer completing a secure off-Render backup before any later production data-write experiment. Do not deploy this development commit or copy a disposable database into production without separate approval. Rollback target remains the operator-reported c9ca57f infrastructure release; preserve existing tables/history rather than restoring over newer research.

