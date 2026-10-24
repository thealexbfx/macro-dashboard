# Chart-first redesign

Based on the owner's visual examples and explicit request for no typing, fewer options, less terminology and charts covering the page. PR #3 is merged; this branch starts from latest redesign-ui (741aa59134e61725f3d84d49d98c3ea8fd99a27c).

- Today: four compact market readings, a two-column grid of four market charts, then two US economy charts. Dates are visible. Inflation is year-on-year CPI, unemployment is the unemployment rate. FRED public CSV sources use no secrets. No news or causal explanations are fabricated.
- Investigate: just Compare / With / Time. Eight curated series, three fixed time ranges, automatic loading, two large charts on aligned dates. Separate panels preserve different units. A short plain-English finding describes correlation of appropriate changes. Save generates its title; repeated save for the same pair/range updates the same record. Data details/downloads are optional. No text, notes, numeric or date typing controls on the production screen.
- My Research: select a saved comparison, see its large chart, read any existing notes and download its record. No writing/editing controls. Older records remain readable; linked older series can still refresh. Saved metadata is preferred for original frequency/unit interpretation. Old transformations are presented as saved source prices/readings, not falsely claimed to reproduce every old chart mode.

The three routes are unchanged. No framework rewrite, dependency changes, secrets or production infrastructure changes. Legacy typing UI remains only as compatibility/reference code, not called by production routes. Pure analytical safeguards remain: yields use basis-point changes, eligible prices use percent returns, alignment is explicit, no missing observations are invented and gaps are not filled for appearance.

Validation: 331 tests passed, five opt-in live checks skipped. Existing Today tests now exercise the chart loader boundary instead of an unused overview helper; no analytical coverage was removed. New tests check no typing controls, automatic charts, repeat-save identity, provider failures, plain wording and saved charts reopening without providers. Fatal lint, compilation and whitespace checks run before publication. One existing dependency deprecation warning remains.

Browser verification: actual Yahoo and FRED market/economic data rendered on Today; Investigate auto-loaded Gold/US 10Y and showed units and dates. Desktop (1280px override) and the actual narrow in-app surface were inspected; the temporary override is reset afterwards. Screenshots are local deliverables. This is representative visual QA, not an exhaustive accessibility certification.

Limitations: provider availability/revisions; latest-vintage observation dates rather than verified release times; no calibrated forecasting; local saved records remain server-scoped and may disappear on hosting restart. New UI intentionally does not create free-text hypotheses or conclusions, following the no-typing instruction; existing written work is retained read-only. The plain-English labels are descriptive bins, not tests of significance. Full lag scans and rolling controls remain outside this simplified production UI.

No merge or deployment is performed. The PR targets redesign-ui.
