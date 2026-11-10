# G7 Core Phase B / Batch 1

The attached 35-mapping export is the seed manifest. Candidate lookup identifiers in the verifier are separate from the seed's approval fields.

The first adapter probes Bank of Canada Valet for the overnight target (V39079) and the daily 10-year government benchmark yield (BD.CDN.10YR.DQ.YLD; legacy lookup-table ID V39055). The Statistics Canada WDS adapter now attempts Canadian headline CPI (G7-CA-07, provisional vector 41690973, Table 18-10-0004-01) and unemployment (G7-CA-11, provisional vector 2062815, Table 14-10-0287-01). Each must independently pass publisher WDS metadata and observation responses. The Canadian real GDP mapping (G7-CA-01) remains unresolved pending a current chained-dollar GDP vector and base-period definition; historical series v62305752 refers to chained 2007 dollars and must not be silently treated as current chained 2017-dollar GDP. The other 31 mappings remain unqueried and unresolved. This includes the three country links to one ECB policy series key. The Bank of Canada bond lookup attributes the benchmark yield data to CanDeal DNA and Bank of Canada. Commercial display and export rights need a source-specific review for both Canadian candidates and remain pending for every mapping.

A verified result requires a matching publisher label and usable dated numeric samples from the publisher endpoint. Sample bounds are limited to the published evidence in the report. Full history and release vintages require independent evidence. The adapter currently has no publisher discontinuation evidence rule, so stale observations never generate a discontinuation verdict.

Run the tests with Node.js 22 or later.

```sh
node --test verification/g7-core-batch1/*.test.mjs
node verification/g7-core-batch1/verify.mjs "$(mktemp -d)"
```

The separate **G7 Core Batch 1 audit (development)** registration workflow runs from `main` and checks out the fixed feature commit listed in its YAML. After the registration PR is reviewed and merged, open Actions → G7 Core Batch 1 audit (development) → Run workflow, select `main`, then click Run workflow. Download the `g7-core-batch1-verification` artifact and check each result against the job log. A green job means report generation succeeded.

The reports record `RECENT_SAMPLE_ONLY` for operational successes and `NOT_APPROVED` for production on every mapping. Malformed responses leave identity unresolved. A mismatch requires a conflicting publisher label for the requested series key.

Publisher references

- [Bank of Canada Valet API](https://www.bankofcanada.ca/valet/docs)
- [Official Valet 10-year benchmark series metadata](https://www.bankofcanada.ca/valet/series/BD.CDN.10YR.DQ.YLD/json) (label: Benchmark bond yield, 10-year; unit: percent; business daily). The earlier hosted attempt using legacy V39055 returned 404; using this Valet key must be retested on GitHub before claiming access.
- [Bank of Canada benchmark bond yields and source notes](https://www.bankofcanada.ca/rates/interest-rates/lookup-bond-yields/?page_moved=1)

## Statistics Canada WDS candidate checks (not yet hosted-verified)

- WDS guide: https://www.statcan.gc.ca/en/developers/wds/user-guide
- CPI original historical publisher vector documentation: https://www150.statcan.gc.ca/n1/pub/62-001-x/2016008/t040-eng.htm
- CPI latest table 18-10-0004-01: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1810000401
- Unemployment table 14-10-0287-01: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410028701
- Real GDP expenditure table 36-10-0104-01: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=3610010401 (candidate GDP vector is still unresolved; note changing chain-dollar reference years)

No successful WDS retrieval has yet been observed in a GitHub-hosted run. A successful WDS response checks recent samples only, not full history or historic release vintages. Do not approve any of these series for production, and retain all rights gates as pending.

## Manifest-driven verification engine (development extension)

The reusable pilot runner reads a candidate manifest and dispatches by publisher adapter through `series-registry.mjs`. Mapping records are immutable proposals, not approvals. The registry currently configures **four Canadian mappings**: two Bank of Canada Valet and two Statistics Canada WDS. All other records remain explicit `UNRESOLVED / NOT_TESTED` exceptions, including Canada's GDP and the shared ECB policy mapping.

The runner accepts either the original 35-row batch or the full 245-row core manifest. Supply the latter as an optional third command-line argument (all rows must have the `operational_outcome=NOT_TESTED` seed state and include the pilot mappings). Example:

```sh
node --test verification/g7-core-batch1/*.test.mjs
node verification/g7-core-batch1/verify.mjs "$(mktemp -d)"
node verification/g7-core-batch1/verify.mjs "$(mktemp -d)" /path/to/MacroLens_G7_Core_Data_Manifest_v1_Reviewed.csv
```

The configured rows are selected from the authoritative manifest by mapping ID and publisher; API IDs, expected labels and adapter types live in the data-only **`series-registry.json`**. To add a mapping already supported by an adapter, edit the JSON candidate registry rather than editing JavaScript. New original publishers still require audited adapter implementations and tests. Publisher-returned metadata and samples determine the result. This is a **reusable framework**, not yet a complete set of G7 adapters. Adding adapters, full-history validation, revision/vintage reconstruction and source-specific commercial-rights review remain explicit future tasks. A passing test or green workflow does not approve a series for production.

Every new adapter must use bounded publisher requests, emit independent identity/access/history/vintage/rights gates and persist sanitized retrieval evidence. Keep the feature PR unmerged, use the existing manual-only workflow registration process, and do not create production ingestion, schedules, deployments or database changes.

## Expansion: US BLS and ECB (development candidate)

The data-only registry now configures nine country mappings across three original publishers:
- Canada: CPI, unemployment (Statistics Canada WDS), overnight target and 10-year benchmark (Bank of Canada Valet)
- United States: headline CPI-U NSA `CUUR0000SA0` and civilian unemployment SA `LNS14000000`, via the official BLS public API v1. BLS v1 returns an identified series and recent numeric observations but **does not independently certify its full descriptive metadata**, base period, or historical/vintage coverage; those remain separate outstanding evidence gates.
- Germany, France and Italy: three country mapping records linked to **one** ECB euro-area deposit facility candidate `FM.B.U2.EUR.4F.KR.DFR.LEV`. The proposed definition is a shared central-bank rate, not three national rates; its historical role and comparability require separate review. The official ECB SDMX REST data endpoint is queried with a bounded recent-sample CSV request.

Source documentation:
- https://www.bls.gov/developers/api_signature.htm
- https://www.bls.gov/cpi/factsheets/cpi-series-ids.htm
- https://data.ecb.europa.eu/help/api/data
- https://data.ecb.europa.eu/data/datasets/FM/FM.B.U2.EUR.4F.KR.DFR.LEV

The new adapters have mocked tests, but **no live GitHub-hosted retrieval evidence yet**. A green GitHub Actions job does not imply all mappings passed. The remaining 26 mappings are unconfigured and must be reported as such, not silently substituted. All 35 remain **NOT_APPROVED** for production; rights and vintages remain pending.

No publisher credentials, deployment, scheduled trigger, or production database changes are introduced. Each publisher adapter sends read-only HTTPS requests only to its strict first-party host allowlist.
