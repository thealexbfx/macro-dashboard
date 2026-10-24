# MacroLens

A small Streamlit application for checking markets, investigating an economic question, and continuing personal research.

- **Today**: four dated market moves, their sources and a path into research. No inferred news or catalysts.
- **Investigate**: a question, two indicators and a comparison chart. Sample dates, transformations, frequencies and statistical tools are optional. Prices use appropriate returns; yields use basis-point changes. Missing observations remain missing.
- **My Research**: reopen local investigations, write conclusions, export records and restore exported version-1 records.

Run `streamlit run app.py`. Run tests with `python -m pytest -q`; live-provider checks require `--run-live` and provider credentials where applicable. The default suite blocks unintended HTTP access.

Saved JSON lives in `research_outputs/investigations/`. This is temporary server storage, not durable per-user cloud storage. Export a copy. Restored records are labelled unverified until recalculated.

The production entry imports neither the retired regional/model dashboards nor the separate Next.js/FastAPI application. Statistical and economic model engines remain for tested backend and research consumers. Refresh loaders now live under `macro_engine/refresh/`. No deployment or secrets configuration was changed.

See `docs/PRODUCT_SIMPLIFICATION.md`, `docs/REMOVED_PRODUCT_SURFACES.md` and `docs/REBUILD_VALIDATION.md` for decisions, removals and validation. Older audit documents describe the previous product and are retained as historical context, not current navigation instructions.
