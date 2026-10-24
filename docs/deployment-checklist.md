# First Discovery Radar deployment

Prepared 2026-10-24. Deployment only: no new product features, merges or deploys.

## Recommended configuration

Use **CPython 3.12.15**, a supported Python 3.12 security release (security
support through October 2028). render.yaml now specifies the full version,
installs requirements.txt, and explicitly binds Streamlit to 0.0.0.0 and Render's
PORT. This fixes the old partial/end-of-life 3.10 selection and removes port
discovery ambiguity. The existing free service, repository and main branch are
unchanged. No hosting settings have been modified through the Render Dashboard.

| Setting | Value / purpose |
|---|---|
| Runtime | Python 3.12.15 |
| Build | `pip install -r requirements.txt` |
| Start | `streamlit run app.py --server.address 0.0.0.0 --server.port $PORT` |
| Health path | `/_stcore/health` (check/apply in Dashboard) |
| Auto-Deploy | **Off before either PR is merged**, until you approve deployment |
| APP_ENV | `prod`, to suppress internal exceptions in existing page wrappers |

### Private environment settings

Enter values privately in the existing Render service Environment page. Select
**Save only**, not Save and deploy or Save, rebuild, and deploy, while preparing.
No secret values belong in Git, reports, screenshots or this checklist.

| Variable | Requirement in this codebase |
|---|---|
| OPENAI_API_KEY | Required by the current global gate for all non-Radar routes. A missing key stops the Overview and existing pages. Radar alone can run without it. A dummy key used in UI tests does not prove real authorization. |
| FRED_API_KEY | Required for FRED-backed economic pages/models, Radar related real yields/breakevens, and the compatible economic fallback when BLS fails. |
| BLS_API_KEY | Optional registration for higher BLS allowances/history. Unregistered requests are attempted without it. Registration does not guarantee HTTP 503 recovery. |
| BEA_API_KEY | Required for BEA-backed GDP, PCE and other national-accounts indicators. |
| ESTAT_API_KEY | Required by e-Stat-backed Japanese indicators where used; other Japanese providers have separate availability. Include it if evaluating the full existing Japan page. |
| PYTHON_VERSION | Non-secret `3.12.15`; check actual service/group overrides match the reviewed manifest. |
| APP_ENV | Non-secret `prod`. |
| PORT | Supplied by Render; do not hardcode or replace it. |

Environment variables are the simplest option on Render. Existing Streamlit
secrets alternatives are `[openai].api_key`, `[fred].api_key`,
`[openai].BLS_API_KEY`, `[openai].BEA_API_KEY`. The unusual BLS/BEA section names
are existing conventions. ESTAT uses its environment variable. Avoid conflicting
values between secrets, .env and Render environment groups. config.py and app.py
load .env; no local .env or secrets file is included in deployment changes.

## What was verified

- Downloaded an isolated **exact Python 3.12.15** runtime and created a new venv.
  Clean `pip install --no-cache-dir -r requirements.txt` completed; pip check
  passed. Installation metadata and resolved package versions are saved in the
  local verification outputs. This local environment is Windows, not Render Linux.
- All **31 tests** pass on that clean exact runtime. They include all discovery
  tests, full Radar navigation/comparison, an actual Streamlit process reaching
  HTTP 200 / `ok` at /_stcore/health, and a missing-key startup check.
- Existing default views for Overview, US, Euro Area, UK, Japan, Rates & Bonds,
  Equities, Commodities, FX, Crypto, Global Macro View, Regime Monitor, Central
  Bank Watch, Research Notes and Calendar render without exceptions/errors with
  controlled provider fixtures and a dummy client-initialization key. These tests
  exercise actual renderers/calculations, not substitute pages; outbound API
  calls are blocked. They do not certify every indicator/dropdown/live provider.
- CI now targets Ubuntu on **3.12.15 exactly** (plus legacy 3.10 compatibility),
  installing the complete requirements and running pip check and the full suite.
  Check the green result on the final reviewed PR head before proceeding.
- BEA error handling was hardened so failed request URLs cannot display the
  API's UserID secret through stale-cache warnings or propagated errors. A
  regression test checks that behavior. No provider definition was changed.

Limits: no real credentials are configured in this environment. Live FRED/BEA
success and credentialed economic pages remain unverified. BLS most recently
returned 503 for both GET and POST; retries/cache/fallback behavior is covered by
tests. Earlier live gold/dollar/silver Radar workflow passed. The full site must
still be checked against real providers on the target service. Free-instance
memory, cold-start latency and provider throttling are not reproduced by CI.

**Existing feature/content discrepancy:** this repository initializes an OpenAI
client but contains no Ask MacroLens input, completion call or route. We cannot
certify an Ask workflow that is not present. If the currently hosted website has
one, identify/reconcile its deployed commit before replacing it. No Ask feature
was added or removed here. The existing Overview also includes hardcoded example
macro cards; it is not a live-data validation of the Radar or regime models.

## Auto-deployment risk and exact merge order

render.yaml tracks **main** and does not disable automatic deployment. For a
Git-provider-connected Render service, the default On Commit mode deploys when
main changes. Therefore **merging PR #5 alone may immediately deploy Phase 1**,
before #6 or its runtime fixes are present. After CI Checks Pass is still an
automatic-deploy mode, not a manual approval gate. A public-URL-created service
may instead be manual-only; repository files cannot prove the live setting.

1. In the **existing service's Dashboard**, set Settings → Auto-Deploy → **Off**
   **before merging either PR**. Check no deployment is already queued/running.
   If Blueprint-managed, inspect/pause automatic Blueprint syncing as well; do
   not sync runtime/environment changes yet. These account settings are not
   visible from this workspace and have not been changed by the agent.
2. Record the current live commit, service settings and rollback target. Confirm
   it corresponds to this repository, especially if it includes Ask MacroLens.
3. Privately prepare the variables above with **Save only**; verify no deploy was
   triggered. Avoid adding secret files or linking environment groups during
   preparation: those actions can trigger deploys.
4. Review and merge **PR #5 → main first**, preferably via **Create a merge
   commit**. Keep the Phase 1 branch until #6 has been retargeted.
5. Retarget **PR #6 → main**, review the resulting Phase 2/deployment-only diff,
   and require fresh CI against that base. If #5 was squash/rebase merged, rebase
   only Phase 2 commits onto main before retargeting (the release-readiness guide
   has the exact command); do not replay/reimplement Phase 1.
6. After separate approval, merge **PR #6 → main**. Keep Auto-Deploy Off. Confirm
   main contains both phases and the 3.12.15/port fixes. Record its final SHA and
   verify CI again. The workflow also runs on main after this deployment pass.
7. Review the actual Render environment/version/build/start settings against the
   table. Resolve any Dashboard/Blueprint overrides. Obtain your deployment
   approval; this checklist does **not** grant it or perform deployment.
8. Only when approved, manually deploy that final SHA, using a clean build if
   needed. Confirm logs report Python 3.12.15 and the health endpoint is healthy.
9. Open Overview and existing country/market/model pages with real credentials;
   check actual results, not only absence of an exception. Open Radar, inspect
   source diagnostics, investigate gold, compare gold/dollar/silver and a
   credentialed FRED series, change ranking/filters and return via navigation.
   Verify BLS or its explicitly labelled compatible FRED fallback supplies real
   unemployment/inflation; note freshness and release-date limitations.
10. If health, existing functionality or live economic data fails, keep the
    previous approved version/rollback target and investigate; do not label the
    first release fully validated. Keep Auto-Deploy Off during initial evaluation.

Remaining before approval: confirm account settings/old deployed commit, privately
configure/validate real provider credentials, review final exact-runtime CI and
the merged diff, then authorize a target-service build and live smoke test. No
new hosting, paid resources, product features, merges or deployments are included.

References: [Python 3.12.15](https://www.python.org/downloads/release/python-31215/),
[Render Python versions](https://render.com/docs/python-version),
[Render deploy controls](https://render.com/docs/deploys),
[Render environment save options](https://render.com/docs/configure-environment-variables),
[Render port binding](https://render.com/docs/web-services#port-binding).
