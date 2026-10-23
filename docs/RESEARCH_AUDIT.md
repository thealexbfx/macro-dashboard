# MacroLens research audit and implementation

## Scope and architecture

Implemented against the supplied `macrolens-production-v1-frontend-v3(1).zip`, not a connected GitHub checkout. The archive contained no `.git` history or remote. A local repository preserves the supplied source as commit `f233f4b`, with work on `audit/research-correctness`. No changes were pushed or deployed.

The initial assessment identified two application paths:

| Area | Existing implementation and disposition |
|---|---|
| Streamlit entry | `app.py`; country pages delegate to `app_pages/economy_page.py`; market pages delegate to `app_pages/market_page.py`. Retained. |
| Economic data | `economy_data/{usa,uk,euro,japan}.py` maps, `indicators/` functions and `data/` connectors for FRED, BLS, BEA, ONS, ECB, Eurostat, Japan and Yahoo. Existing loaders and caching retained. |
| Comparison registry | Root `comparison_registry.py` is used by the pages. The duplicate `app_pages/comparison_registry.py` now re-exports it. Existing records are enriched, rather than replaced by a new catalogue. |
| Macro models | Active `macro_engine/metadata`, `engine`, `pipelines`, `models`, historical validation and cached country environments. Older `models/` functionality and scratch research coexist; these are not interchangeable production services. |
| Existing workspace | `app_pages/research/research_workspace.py`, `macro_engine/decision`, snapshots and asset-specific historical evidence. Preserved beside a new independent investigation mode. |
| Production API | `backend/app/main.py`, thin FastAPI routes, service boundaries, deterministic planner, customer-answer schemas and separate small production registries. No Streamlit dependency was introduced into the API. |
| Public frontend | `frontend/` Next.js App Router, existing Ask/Home/Markets/Macro views and answer blocks. Extended with a relationship page and richer evidence displays. |
| Legacy artifacts | Root `_bonds.py` and `crypto.py` contained captured patches/terminal text, not executable modules. No application imports referenced them. Their contents are preserved in `docs/legacy/*.py.txt`. Actual bond/crypto modules remain in place. |

Architecture documentation lagged the source: the described first backend slice and the claimed absent Next.js frontend were already superseded. Older scripts and precomputed research CSVs remain available but were not revalidated as investment evidence.

## Confirmed problems

1. Market comparison paths joined exact dates, losing meaningful overlap between different frequencies.
2. Percentage changes, rebasing, drawdowns and return correlations were applied without economic metadata checks.
3. Rolling volatility always used 252 periods; missing-period and publication timing assumptions were not visible.
4. Country dashboard correlation and accompanying commentary used levels, allowing trending levels to suggest misleading co-movement.
5. Market summaries called level dispersion “volatility” and assigned “Significance” from arbitrary dispersion thresholds.
6. The production relationship service transformed before alignment, described every sample as daily, and lacked lead/lag and stability evidence.
7. The frontend displayed every conditional target change with `%`, including yield changes measured in basis points. Its research link had no corresponding page.
8. Reconstructed regimes could include a snapshot later than the tested market sample and carried no finite staleness limit.
9. Monthly growth could bridge a missing month; year-over-year division could produce undefined values at zero denominators.
10. An unused OpenAI client blocked the entire Streamlit application without a key. Exception paths also referenced undefined `IS_PROD`; FX type annotations referenced an unimported model.
11. The supplied frontend dependencies had known vulnerabilities. Next.js, React and transitive packages were updated and audited.

## Changes by phase

### Phase 1: correctness

`macro_engine/research/analytics.py` provides pure calculations with metadata adapted from the existing registries. Metadata records representation, category, units, frequency, nonpositive-value eligibility, source, date conventions and explicit ratio compatibility. Market maps and the production market registry now state more quote conventions. Unspecified economic units are retained as unspecified rather than invented.

Prices and eligible indexes use percentage changes. Yields quoted in percent use basis-point differences. Rates and already-calculated growth rates use percentage-point differences. Other levels and signed flows use absolute differences. Relative performance and drawdown require eligible positive series. Ratios require an explicit matching ratio group and matching units; zero denominators reject the calculation. Gold/silver quote compatibility is explicitly recorded; broad “currency scale” labels alone do not authorize ratios.

The existing market comparison view now calls this layer and bypasses duplicated legacy summary calculations. Country dashboard rolling correlation and commentary use economically appropriate changes. Single-market summaries report annualized change standard deviation and remove unsupported significance labels. Invalid comparisons explain their restriction.

### Phase 2: data integrity

Alignment uses the slower declared frequency and the last observation within each period. Monthly/quarterly labels are period ends, not publication dates. Missing periods remain on the grid, so returns and lead/lag horizons do not silently jump across missing months. Daily comparisons use observed trading sessions; mixed crypto comparisons use weekday sampling. No interpolation or backward filling is performed.

An optional calculation-level availability path requires actual `publication_date` values and a positive staleness limit, then uses backward as-of matching. Existing connectors do not supply verified vintage histories, so live UI research remains explicitly observation-date/latest-vintage analysis. It is not presented as a point-in-time backtest. Terminal comparison periods may be incomplete; original last-observation dates are included in methodology.

Monthly connector growth now respects calendar gaps and disables implicit fill. Zero/nonpositive index denominators cannot generate infinite growth figures. Frequency, paired sample size, coverage, missing periods, source units and methodological limits are exposed.

### Phase 3: research evidence

The existing production relationship service now aligns levels before computing changes, reuses the existing eight US economic specifications alongside market series, and adds:

- Lead/lag correlations, paired counts, sample dates and direction. Positive lag means the left indicator at time t is compared with the right indicator at t+h.
- Full-sample, first-half and second-half correlations and rolling correlation estimates. These are sample-sensitivity diagnostics, not automatic “stable” or significant classifications.
- Existing regime conditioning with backward matching, a 100-day age limit and exclusion of future snapshots. Existing environment definitions use activity, inflation and financial impulses with +/-0.15 direction thresholds; the named combinations remain in `classify_macro_environment`.
- Explicit cautions about revised inputs, autocorrelation, overlapping windows and multiple lag comparisons. No p-values, predictive success or causal findings are asserted.

Additive API endpoints:

```text
GET /api/research/relationships/series
GET /api/research/relationships?target=gold&driver=us10y_real&timeframe=5_years&economy=usa
```

Existing routes and customer-answer fields remain. New fields are additive. The frontend research page lets users choose supported series, history and regime economy, and displays lag, stability and regime evidence. Ask routing now recognizes an explicit relationship involving an economic rate instead of treating it as a factual lookup.

### Phase 4: independent research experience

Choose **Independent investigation** in the existing Streamlit research workspace. Select any two entries in its broad existing registry, state a hypothesis, select dates/transformation/window, inspect evidence, and record support and counterarguments.

Investigations save locally as atomic UUID-named JSON records under `research_outputs/investigations/`. They retain settings, methodology, raw source observations, transformed data and evidence. Saved investigations can be reopened and updated. Changed settings require a fresh calculation before saving evidence. No database or account system was introduced.

Exports include CSV, methodology/investigation JSON and self-contained interactive Plotly HTML. Comparison charts use separate panels where units differ and carry sample and timing annotations. PNG export is available through Plotly's chart controls; automated publication-layout verification was not performed.

## Validation

Final results: **44 focused tests passed**. Full suite: **271 passed, 31 failed** (302 collected). Frontend build passed with the local packaging setting. Repository fatal-error lint and Python compilation passed. Frontend dependency audit: **zero known vulnerabilities**. One test-client deprecation warning and existing CSS compatibility warnings remain.

See the delivered validation files for exact final counts and commands. Synthetic tests cover the seven analysis modes, positive prices/indexes, equity/FX/commodity categories, nominal/negative real yields, percentage rates/growth rates, signed flows, zero/negative values, missing observations, insufficient samples, daily/weekly/monthly/quarterly alignment, publication timing, staleness, lag direction and constant inputs.

Offline integration tests cover the real enriched registry, production service and API, unit serialization, local persistence and path rejection, chart panels, country correlation, actual market-page paths, Streamlit notebook/comparison views, and root app startup without an OpenAI key. Provider data in these tests is synthetic.

The full suite was also run. Live connector failures remain because FRED credentials are unavailable and some external HTTPS chains fail verification. One Euro sentiment test assumes a fixed 2006-07 start even though the existing rolling 240-month sample now starts 2006-10. Useful tests were retained unchanged. TLS verification was not disabled, and live integrations are not claimed to work.

Fatal-error linting across the repository and Python compilation pass. New modules additionally pass import/style/undefined-name checks. There is no configured Python static type checker; frontend build checks ran with the existing JavaScript project configuration. The frontend compiles and prerenders with `MACROLENS_LOCAL_BUILD=1`. Default standalone packaging encountered Windows symlink `EPERM`; its deployment default remains preserved. Existing CSS compatibility warnings remain.

The dependency audit reports zero known frontend vulnerabilities at verification time. This is not a general security certification. A source scan for common credential patterns is included separately; no credential values are copied into deliverables.

## Dependencies and running

No new Python runtime package or data service is required. `requirements-dev.txt` adds pytest and Ruff for validation. Frontend versions are pinned to Next.js 15.5.28 and React/React DOM 19.1.10; pnpm/npm overrides pin PostCSS 8.5.31 and Sharp 0.35.5. The pnpm lockfile records resolution. Sharp build scripts are disabled; an image-optimization deployment using Sharp needs separate verification. The original security advisory is available at [Next.js](https://nextjs.org/blog/CVE-2025-66478).

From the extracted repository root, using Python 3.11+:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r backend/requirements.txt -r requirements-dev.txt
python -m streamlit run app.py
```

Provide `FRED_API_KEY`, `BLS_API_KEY` and `BEA_API_KEY` in the environment or existing supported configuration as needed by the selected connectors. An OpenAI key is optional for app startup; AI synthesis/catalyst features retain their existing configuration. No secrets are bundled.

For the API, in another terminal from the root:

```powershell
python -m uvicorn backend.app.main:app --port 8000
```

For the frontend, using Node.js 22+ and pnpm 11:

```powershell
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

The frontend defaults to `http://127.0.0.1:8000`; use `NEXT_PUBLIC_MACROLENS_API_URL` when needed. On Windows, a local production build can use `$env:MACROLENS_LOCAL_BUILD='1'; pnpm build`. Omit that variable for the original standalone deployment target. CORS and deployment configuration were otherwise preserved; production hosting was not tested.

Focused tests:

```powershell
python -m pytest tests/test_research_analytics.py tests/test_research_integration.py backend/tests -q
```

## Remaining limitations and priorities

1. **Highest value: acquire release/vintage histories and audit every regime input's availability.** Current historical comparisons and cached regimes are descriptive; publication-aware alignment alone does not validate revised data.
2. **Restore and isolate live connector tests.** Configure credentials and trusted certificate chains, replace rolling-date assertions with explicit fixtures, and separate network checks from deterministic CI.
3. **Complete metadata curation.** Some legacy country units, seasonal/revision conventions and commodity contract conventions remain incomplete. Conservative defaults restrict some transformations and ratios until explicitly reviewed.
4. **Broaden the production economic catalogue.** The Streamlit notebook uses the broad country registries; the production API intentionally remains limited to its existing US economic specifications and market list. UK vacancy/wage and multi-leg differential investigations can use existing series and yield-spread tools, but a general saved multi-leg formula builder is not implemented.
5. **Strengthen research inference.** Add predeclared out-of-sample hypotheses, revision-aware forecast evaluation, autocorrelation-aware inference and multiple-testing controls before making predictive/significance claims.
6. **Finish production persistence and export QA.** Local notes are for trusted single-user use, without accounts, concurrent-edit protection or cloud persistence. Static export typography and a deployed browser/provider end-to-end run remain unverified.
7. **Retire legacy calculations after migration.** Older chart helpers remain for compatibility, although active market comparison routing uses the shared layer. Existing decision-workspace model confidence and stored research CSVs should not be read as validated statistical confidence.

Library delivery: the available tools expose no Library version-read/replacement operation. No remote Library item was overwritten or duplicated. The deliverables are an updated source ZIP and reviewable Git artifacts for the supplied archive.
