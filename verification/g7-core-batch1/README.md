# G7 Core Phase B / Batch 1

The attached 35-mapping export is the seed manifest. Candidate lookup identifiers in the verifier are separate from the seed's approval fields.

The first adapter probes Bank of Canada Valet for the overnight target (V39079) and the daily 10-year government benchmark yield (BD.CDN.10YR.DQ.YLD; legacy lookup-table ID V39055). The remaining 33 mappings emit unresolved records without a request. This includes the three country links to one ECB policy series key. The Bank of Canada bond lookup attributes the benchmark yield data to CanDeal DNA and Bank of Canada. Commercial display and export rights need a source-specific review for both Canadian candidates and remain pending for every mapping.

A verified result requires a matching publisher label and usable dated numeric samples from the publisher endpoint. Sample bounds are limited to the published evidence in the report. Full history and release vintages require independent evidence. The adapter currently has no publisher discontinuation evidence rule, so stale observations never generate a discontinuation verdict.

Run the tests with Node.js 22 or later.

```sh
node --test verification/g7-core-batch1/verify.test.mjs
node verification/g7-core-batch1/verify.mjs "$(mktemp -d)"
```

The separate **G7 Core Batch 1 audit (development)** registration workflow runs from `main` and checks out the fixed feature commit listed in its YAML. After the registration PR is reviewed and merged, open Actions → G7 Core Batch 1 audit (development) → Run workflow, select `main`, then click Run workflow. Download the `g7-core-batch1-verification` artifact and check each result against the job log. A green job means report generation succeeded.

The reports record `RECENT_SAMPLE_ONLY` for operational successes and `NOT_APPROVED` for production on every mapping. Malformed responses leave identity unresolved. A mismatch requires a conflicting publisher label for the requested series key.

Publisher references

- [Bank of Canada Valet API](https://www.bankofcanada.ca/valet/docs)
- [Official Valet 10-year benchmark series metadata](https://www.bankofcanada.ca/valet/series/BD.CDN.10YR.DQ.YLD/json) (label: Benchmark bond yield, 10-year; unit: percent; business daily). The earlier hosted attempt using legacy V39055 returned 404; using this Valet key must be retested on GitHub before claiming access.
- [Bank of Canada benchmark bond yields and source notes](https://www.bankofcanada.ca/rates/interest-rates/lookup-bond-yields/?page_moved=1)
