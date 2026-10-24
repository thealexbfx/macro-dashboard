# Production UX testing report

Final local default suite: **323 passed, five skipped**, no failures. The five skips are explicitly opt-in live-provider checks, unchanged from the existing test policy. One dependency deprecation warning (Starlette/httpx) remains. Fatal Ruff checks, Python compilation and Git whitespace checks passed. Frontend/FastAPI sources and dependencies are unchanged; the production target is Streamlit.

New regressions cover descriptive correlation thresholds, insufficient/constant samples, terminal rolling gaps and counts, lag-zero interpretation, all 23 preserved navigation keys, useful unavailable-page rendering, exact calendar-month historical horizons and yield units, fractional quote axes, frequency/window evidence invalidation, and the added rolling CSV export. Existing transformation, alignment, lag-sign, persistence and export tests remain enabled. The notebook save/reopen/update regression still passes.

The real deployed Gold/US 10Y investigation was exported and independently recomputed from its included source data. 6,512 paired levels, 6,435 valid changes; r=-0.15965599. The 60-period rolling result has 59 warm-up periods, 3,012 incomplete later windows and 3,517 valid windows; latest valid 2026-10-09, r=-0.30551668. Details: PRODUCTION_UX_AUDIT.md.

Browser checks covered all production routes through rendered accessibility observations and representative screenshots. Local verification reopens the real exported snapshot; it does not fabricate provider observations. Mobile (319px) and desktop (1280px) surfaces were available; explicit tablet/laptop viewport emulation and exhaustive screen-reader testing were not. Local Yahoo retrieval failed (database/cache access); its recovery message rendered correctly. This run does not certify all provider endpoints. Production supplied the real investigation successfully.

Review remaining opportunities and the Render main/redesign-ui configuration discrepancy in PRODUCTION_UX_AUDIT.md. No secrets, production configuration or deployments were changed. Remote CI status must be checked on the PR before deployment.
