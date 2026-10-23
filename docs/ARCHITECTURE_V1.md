# MacroLens V1 Production Architecture

Current implementation and audit: see [RESEARCH_AUDIT.md](RESEARCH_AUDIT.md). The original first-slice milestones below are retained as migration history; the repository now includes Ask, Home, historical relationship services and a Next.js frontend.

## Target

Frontend (Next.js)
  -> HTTPS JSON API
Backend (FastAPI)
  -> research planner / executor / synthesis
  -> MacroLens engines and registries
  -> market/economic providers
  -> targeted web research
  -> cache

The existing Streamlit application remains a legacy/internal research interface during migration and is not the target public frontend.

## Migration principle
Do not port the Streamlit application line-by-line. Existing Python code earns reuse only when it improves the production product.

## Production backend boundaries
- `backend/app/api`: HTTP routes only.
- `backend/app/services`: stable application services exposed to routes.
- `backend/app/research`: planner, executor, synthesis, evidence contracts (next migration stage).
- existing `macro_engine`: retained research/model core while dependencies are progressively cleaned.
- existing `data` / `indicators`: migrate away from Streamlit caching/secrets before they become production service dependencies.

## First production slice
The first slice intentionally proves only:
- FastAPI application boots beside the real current MacroLens source.
- health endpoint works.
- Macro endpoint reads the real MacroLens environment cache without importing Streamlit page code.

This is the seam the new frontend and later Ask service will use.
