# Existing and proposed MacroLens catalog

Audit date 8 November 2026 (US Central). Research-only snapshot.

| Evidence | Result |
|---|---|
| GitHub head of `feature/macrolens-v2` | `cb7a03cded7113231fe1bac42beadff0e92a274a`, identical to the supplied historical production SHA |
| Live catalog on the public domain | Two GET pages of 100 and 94 items, 194 distinct IDs, final next_offset null |
| Live backend | Catalog total 194. Older /api/v2/datasets route returns 30 legacy records by design |
| Current Render deployment SHA | Unverified. Dashboard requires sign-in. Public health exposes mode/status only and GitHub combined status is empty. No newer production revision was established |
| Universal refresh branch | `4200dac0face4276091f9cc5696513e4d5b67c0b`, incorporated by PR #14 at the baseline merge |
| Full expansion branch | `1699803baca4c53f264d0d38780725a18dff06ba`, supplementary Linux validation and candidate receipts |

Live evidence [page one](https://www.macrolensresearch.com/api/v2/catalog?limit=100), [page two](https://www.macrolensresearch.com/api/v2/catalog?limit=100&offset=100), [backend](https://macrolens-v2-backend.onrender.com/api/v2/catalog). Code evidence [baseline](https://github.com/thealexbfx/macro-dashboard/commit/cb7a03cded7113231fe1bac42beadff0e92a274a), [universal release](https://github.com/thealexbfx/macro-dashboard/blob/cb7a03cded7113231fe1bac42beadff0e92a274a/research/releases/universal/README.md).

## Registry reconciliation

Independently counted 309 manifest IDs (293 series and 16 planning selections), 313 rows in the composed release export and 194 distinct IDs in the publication plan (100 prior IDs plus 94 named approvals). The live public count independently agrees with the planned total. The exact live-to-plan set equality was not machine-checked. The 313-row export contains 100 public IDs as of 2 November, 94 reviewed release candidates at export time, 116 blocked or planned rows and three private-ingestion reports. The 194 IDs in the CSV are the release-plan set. That status does not certify historical completeness. Twenty-one rows outside the public plan have development validation receipts in the full-expansion candidate file. A development receipt is evidence of an implemented, tested route, with production publication and production ingestion tracked separately. Private World Bank IDs `wb_brent_monthly`, `wb_copper_monthly`, `wb_iron_ore_monthly` have user-reported ingestion only here. Synthetic fixtures are test evidence and contribute zero production datasets.

The CSV contains 391 unique IDs, one row per registered series or proposed selector. It excludes the 16 non-atomic planning records retained in the original export. Their IDs remain in the repository: `census_495989ca049225a4737d`, `hmrc_0eb8ded14b6894fd15a4`, `hmrc_f02d1947285134c80c0b`, `jodi_2234abe93e10dd71b4c9`, `jodi_50d263f0e929e084e5af`, `jodi_80d9e5c76ebdb327cde0`, `jodi_825df07111b4d9cd8a9b`, `jodi_83b9c7354cf41478e0a2`, `jodi_c98e8e7f606343db5396`, `jodi_d840583e1c012a0b395d`, `lme_b731c1487a759914b8cc`, `modot_70899a8fcc58ebeaa3de`, `modot_9ab75d81f608cc7d68df`, `usgs_191e0ede68d16a573a6e`, `usgs_d2f2407320608177d323`, `worldsteel_ab047d9c9ba67fc02273`. Alternative source routes are recorded on the existing row. Proposed selectors with unresolved dimensions or tenor coverage remain flagged. Current Eurostat HICP and real GDP selections stay on the existing IDs. Historical fields sourced from supplemental candidate receipts refer to that validation snapshot.

## Runtime and operations

The canonical view composes manifest, source overrides and releases. Legacy entries come from SPECS and persistent SQLite source_cache. Native entries require an explicit runtime grant, a matching definition and rights, and complete observations validated by NativeReader. The refresh policy never confers display, AI or Discovery permissions. Legacy caches use scheduled due checks, persistent failure backoff and leases. Existing docs describe daily/weekly/economic intervals at 6/12/24 hours, with release hints. Native refresh is opt-in and sequential, with per-series policy, immutable snapshots, partition cursors, conditional requests, definition and history checks, revision handling and retention of last good data. Actual current worker configuration, failures and private receipts require operator-side read-only evidence. CPI public metadata showed a successful check on 8 November and retained a missing October 2025 value. This is one sampled legacy series, not a health certificate.

The legacy route includes FRED and Yahoo. Native public catalog facets showed BEA, BoE, Census, DESNZ, ECB, EIA, Eurostat, Federal Reserve and ONS alongside FRED and Yahoo. A historical ID prefix can differ from the current retrieval provider. For example `fred_259d141714182247e607` retains its ID with Census retrieval.

## Existing research used

- PR #14 and the universal export, publication plan, refresh policy and hold checks document scope, provider blockers and attribution for the release.
- Full expansion has 185 candidate definitions with source contracts and development validation receipts. The representative Linux validation workflow is distinct from production coverage.
- PR #15 is the read-only runtime readiness audit. Its tested 194-series fixture is synthetic. The runbook expects cb7a03c and reads the deployed SQLite snapshot separately.
- PR #16 addresses bounded FRED credit-spread history and old cache telemetry. It records the two ICE windows and retains the previous prefix with explicit verification limitations.
- PRs #17–22 are open research/UX work. Browser fixture observations and unchanged backend permissions do not promote new datasets. PR #8 is the baseline branch PR, whose original description predates later catalog work.
- The incremental real-resource proposal records 34 selections, including permits, asphalt, construction inputs, materials and energy. Its proposal counts are separate from runtime grants.

[Registry logic](https://github.com/thealexbfx/macro-dashboard/blob/cb7a03cded7113231fe1bac42beadff0e92a274a/backend/app/catalog/operations.py) · [Publication plan](https://github.com/thealexbfx/macro-dashboard/blob/cb7a03cded7113231fe1bac42beadff0e92a274a/catalog/publication_plan.json) · [Readiness PR](https://github.com/thealexbfx/macro-dashboard/pull/15) · [Refresh corrections](https://github.com/thealexbfx/macro-dashboard/pull/16)
