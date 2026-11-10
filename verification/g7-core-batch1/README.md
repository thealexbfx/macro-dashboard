# G7 Core Phase B / Batch 1

The attached 35-mapping export is the seed manifest. Candidate lookup identifiers in the verifier are separate from the seed's approval fields.

The first adapter probes Bank of Canada Valet for the overnight target (V39079) and the daily 10-year government benchmark yield (V39055). The remaining 33 mappings emit unresolved records without a request. This includes the three country links to one ECB policy series key. The Bank of Canada bond lookup attributes the benchmark yield data to CanDeal DNA and Bank of Canada. Commercial display and export rights need a source-specific review for both Canadian candidates and remain pending for every mapping.

A verified result requires a matching publisher label and usable dated numeric samples from the publisher endpoint. Sample bounds are limited to the published evidence in the report. Full history and release vintages require independent evidence. The adapter currently has no publisher discontinuation evidence rule, so stale observations never generate a discontinuation verdict.

Run the tests with Node.js 22 or later.

```sh
node --test verification/g7-core-batch1/verify.test.mjs
node verification/g7-core-batch1/verify.mjs "$(mktemp -d)"
```

GitHub requires the workflow path on the default branch before it can be dispatched. A separate registration PR can add just the workflow file to main. After that PR is reviewed and merged, open Actions  G7 Core Batch 1 verification  Run workflow, select feature/g7-core-batch1-verification, and click Run workflow. Review the selected commit and download the g7-core-batch1-verification artifact. A green job means report generation succeeded. Use the individual outcomes and receipts to evaluate retrieval.

Publisher references

- [Bank of Canada Valet API](https://www.bankofcanada.ca/valet/docs)
- [Bank of Canada benchmark bond yields and source notes](https://www.bankofcanada.ca/rates/interest-rates/lookup-bond-yields/?page_moved=1)
