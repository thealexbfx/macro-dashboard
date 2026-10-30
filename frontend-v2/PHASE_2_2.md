# MacroLens Phase 2.2 — Review and preview

Phase 2.2 corrects economic headline semantics and adds a dated source audit. The approved Phase 2.1 layout and analytical features are preserved. No Phase 3 work, deployment or merge was performed.

Read [DATA_INTEGRITY_AUDIT.md](DATA_INTEGRITY_AUDIT.md) for every V2 dataset, the additional upstream inventory, expected/actual values, source links, vintage reconciliation and limitations. [audit-evidence-2026-10-24.json](audit-evidence-2026-10-24.json) contains exact observed values and provider/release metadata from the audit snapshot.

## Before and after

| Indicator | Before | After |
|---|---|---|
| Payrolls | 159,044 thousand people as primary figure | +29,000 monthly jobs; original level remains available |
| CPI | SA price index as primary figure | 3.7% annual NSA inflation; SA monthly and raw indices retained |
| GDP | Q2 incorrectly marked stale from quarter-start age | 2.2% q/q annualized, latest September 30 release; next October 29 |
| Federal funds | Ambiguous policy-rate interpretation | Explicit monthly average effective federal funds rate, 3.75% |
| Market prices | Provider success could imply validation | Four Yahoo closes explicitly Unverified; H.15 yield separately primary-checked |

## Local preview

The refreshed review instance is at http://localhost:3016, with the isolated V2 backend at http://127.0.0.1:8016. These processes must remain running.

For a fresh checkout, use Python 3.12+ and Node 22+. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
.\.venv\Scripts\python -m uvicorn backend.app.v2.main:app --host 127.0.0.1 --port 8016
```

In a second terminal:

```powershell
cd frontend-v2
npm ci
npm run build
node node_modules/next/dist/bin/next start -p 3016
```

The existing local API URL defaults to 127.0.0.1:8016. No credentials or paid providers are required. Original saved investigations retain their dataset IDs and transformations; reopening fetches revised observations rather than a frozen vintage.

## Validation

- Full Python regression: **397 passed, 5 skipped**, 19 existing dependency/deprecation warnings. A fresh workspace-local pytest temporary/cache directory was used because old temporary folders are restricted.
- Ruff: passed on the isolated V2 package and affected tests.
- Frontend deterministic tests: **12 passed**.
- Frontend real-provider integration: **13 passed**, including every preset, YTD/MAX/custom boundaries, market movements, dated economic headlines, Today/Investigate exact consistency and explicit market-verification limits.
- Build, lint and strict typecheck: passed.
- Browser: Today displays annual NSA CPI, +29,000 payroll jobs, precisely labelled monthly FEDFUNDS and current Q2 GDP. Payroll headline opens the jobs transformation; switching to original values restores 159,044 thousand persons. Saving/reopening preserves the jobs transformation. Annual CPI opens CPIAUCNS with YoY selected and matches the exact backend calculation. Existing Phase 2.1 research remains available. Desktop and narrow responsive views preserve the established visual identity.

Deterministic fixtures verify calculations; provider integrations verify application consistency; dated primary/distributor comparisons verify only the explicitly recorded observations. These are separate forms of evidence. Four latest Yahoo prices and nine upstream-only registrations remain independently Unverified. Historical revisions are not a full vintage archive; future observations do not inherit this audit’s verification.

## Architecture and compatibility

- `backend/app/v2/definitions.py`: central canonical definitions and allowed transformations.
- `backend/app/v2/integrity.py`: validation, release-aware freshness, dated evidence reconciliation and market movement presentation.
- `backend/app/v2/audit_evidence.json`: dated expected observations and primary/distributor evidence.
- `backend/app/v2/main.py`: isolated identity-validating provider adapter, shared headline/Investigate transformations, additive quality metadata.
- Frontend contracts and widgets consume backend headlines/movements and expose detailed evidence in expandable panels.
- Two NSA CPI definitions are added; existing underlying observations, research engines, routes, saved IDs and production providers remain intact.

Branch: `feature/macrolens-v2`. Draft PR #8 continues to target `redesign-ui`; it is not merged or deployed.
