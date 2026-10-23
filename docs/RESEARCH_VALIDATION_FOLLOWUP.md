# Research validation follow-up

The original full run had 271 passes and 31 failures: 22 certificate failures, five BLS rate-limit responses, two missing FRED credentials, one non-JSON BEA response, and one shrinking Eurostat history window.

The default suite now isolates provider boundaries with deterministic source data while exercising the real indicator, bucket, pillar and research engines. Unexpected network access fails the test. Live checks require --run-live and credentials when applicable. Tests do not establish that unavailable providers have recovered.

Final local validation: 308 passed, five live checks skipped. Separate live checks: four passed (ECB and Eurostat), one skipped (FRED key absent). Fatal Python lint and the frontend production build passed. A new GitHub workflow runs tests and the frontend build; its remote result is not implied by local validation.

Manual verification:
- Streamlit: real ECB wages and effective policy-rate data; inspected alignment, sample sizes, limitations, stability, saving and repeated-save behavior. Added an automated save/reopen/update regression using synthetic data.
- Frontend: inspected the responsive form and provider-error behavior. Successful result, lead/lag and sample-stability rendering used an explicitly labeled synthetic API fixture because FRED public CSV requests timed out. This verifies rendering, not live FRED availability. The latest preview on a second origin encountered CORS; successful result rendering was checked on the allowed original origin.
- Yahoo returned no usable market data; the workspace now reports provider unavailability gracefully.

Corrections include bounded verified HTTP requests, fail-fast missing FRED keys, stable Eurostat history across the EA20/EA21 seam, explicit bounded persistence only for the ECB effective policy-rate state, stable notebook record selection and saved evidence reopening. Ordinary missing observations remain unfilled.

Screenshots were saved with the local deliverables. Personal investigation records, provider caches, temporary fixtures and local logs are excluded from this pull request.
