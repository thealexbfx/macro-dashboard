# Official CPI history and refresh validation

Development only. This pilot is explicitly invoked, uses a dedicated workspace and creates no display grants. Existing catalog registrations, release policies, public IDs and application startup are unchanged.

## Publisher history captured

| Series | Original identifier | First valid | Last | Valid values | Source nulls | Latest |
|---|---|---|---|---:|---:|---:|
| Canada all-items CPI, NSA, 2002=100 | 18-10-0004-01 / v41690973 / 2.2 | 1914-01 | 2026-09 | 1,353 | 0 | 170.0 |
| Canada CPI-trim, YoY percent | 18-10-0256-01 / v108785715 / 1.3 | 1990-01 | 2026-09 | 441 | 492 | 1.8 |
| Canada CPI-median, YoY percent | 18-10-0256-01 / v108785714 / 1.2 | 1990-01 | 2026-09 | 441 | 492 | 1.9 |
| Japan all-items CPI, NSA, 2025=100 | 0004052037 / 0001 | 1970-01 | 2026-09 | 681 | 0 | 102.2 |
| Japan CPI less fresh food, NSA, 2025=100 | 0004052037 / 0161 | 1970-01 | 2026-09 | 681 | 0 | 102.3 |
| Japan CPI less fresh food and energy, NSA, 2025=100 | 0004052037 / 0178 | 1970-01 | 2026-09 | 681 | 0 | 102.8 |

Total **4,278 values and 984 explicit nulls**. The two core Canadian vectors contain nulls from 1949-01 through 1989-12. No months are absent inside the published table windows. The Canada bounds come from the full table plus its cube metadata and exact national series rows. The Japanese scope is the publisher's named **January 1970–present** file. The earlier 1946 archive uses a different concept (excluding imputed rent). The parser checks first and last periods, exact monthly coverage, expected geography/vector or item codes, units where present in the archive, and a finite final value. Dataset definitions retain adjustment and base.

September release dates are 2026-10-19 (Canada) and 2026-10-23 (Japan). September values matched the official releases for all six. Earlier checks included Canada headline September 2025 and August 2026 (164.9 and 169.8), Canada trim April/August 2026 (2.0%/1.9%), median (2.1%/2.0%) and Japan August 2026 (102.2/102.0/102.5). Source publication stamps and reference periods are separate. Earlier publication dates remain unknown unless captured in a prior snapshot.

| Captured official artifact | SHA-256 |
|---|---|
| 18100004-eng.zip | `7852a5ea863a62129c7733059ba031c661348b8b3d38a3744d77e9053d10a390` |
| 18100256-eng.zip | `d62a5a525ae17f413d63d27cefd862c55f0d45ab6e3387c573205ff03d84877a` |
| zmi2025a.csv, file 000040482945 | `15c42c311c93266a6c7511ea6be17e38cd4abc4dc8ba5659f266284f91952083` |

[Canadian headline table](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401) · [Canadian core table](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810025601) · [Canadian release](https://www150.statcan.gc.ca/n1/daily-quotidien/261019/dq261019a-eng.pdf) · [Japanese historical file](https://www.e-stat.go.jp/en/stat-search/files?stat_infid=000040482945) · [Japanese release](https://www.stat.go.jp/data/cpi/sokuhou/tsuki/index-z.htm)

## Revisions, methodological breaks and rights

Canada CPI-trim and CPI-median can revise because their input price series are seasonally adjusted. Japan's January 2025 onward data were recomputed in the 2025 base, with earlier indexes linked by the publisher. The 2026 transition changed weights and items. This import uses the publisher's single linked index file and does not mix in 2020-base levels or reconstruct official growth rates from rounded linked levels. First capture has zero previously stored revisions. Older vintages were not reconstructed from current-vintage files. Subsequent changed periods preserve their previous values and provenance in the native revision table.

Commercial classification for these exact aggregate series is **supported subject to publisher terms**. Keep attribution and applicable conditions, including disclosure of modifications, and exclude third-party content. No paid display, export, AI or Discovery authorization was granted. [Statistics Canada licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence) · [Canadian core methodology](https://www.statcan.gc.ca/en/statistical-programs/document/2301_D64_T9_V3) · [Statistics Bureau terms](https://www.stat.go.jp/english/info/riyou.html) · [Japan 2025-base transition](https://www.stat.go.jp/english/data/cpi/2025plan.html)

## Refresh verification and live transport blocker

- The three complete publisher files were downloaded directly through the official browser links. The development backfill exercised the actual byte parsers and native SQLite ingestion via a capture transport. The transport replayed the publisher release metadata for that vintage. The SQLite integrity check returned `ok`.
- The private runner uses the native scheduler's durable due times and backoff, HTTP validators, immutable snapshots, partitioned atomic promotion and revision records. The Japan adapter discovers the exact history file from the official listing. The Canada adapter checks official table release metadata and reads bounded bulk ZIPs. Responses with missing periods, changed selectors or drifted units fail before promotion.
- Two focused tests passed. They cover initial promotion, unchanged HTTP 304, Retry-After and backoff, rejection of truncated history, retention of last-good data, successful recovery with a new period and a corrected value, a retained revision, zero public grants and rejection of an uninitialized development workspace. Refresh transport failures and next releases in these tests are simulated.
- The actual CLI's direct HTTPS probe failed with `network_or_tls_failure`. Shell DNS resolution failed for both `www150.statcan.gc.ca` and `www.e-stat.go.jp`. The official WDS full-table URL could not be fetched by the web reader either. The official browser bulk downloads resolved the backfill but do not establish unattended HTTP operation. No provider or proxy substitution was used.
- Next action is a staging run from a network-enabled environment with approved DNS/HTTPS egress to those official hosts. Verify actual listing/table HTML discovery, first backfill, HTTP validators and the next official release against the publisher. Keep access disabled until that evidence is recorded.

Run once from the repository root on an approved development host with a new dedicated path:

```sh
python -m scripts.g7_cpi_refresh /path/to/new-private-cpi-workspace --initialize
```

Invoke the same command without `--initialize` every minute from a development scheduler to drain staggered jobs and retries. The worker enforces daily checks per successful series. There is no scheduler registration in this commit. For the remaining G7, reuse these bounded artifact, validation and native revision steps. Start with Canada GDP/labour and Japan wages/household demand. Verify each transport and definition against two successive publisher vintages before expanding scope.
