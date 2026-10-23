# MacroLens Production V1 — Build Status

Current status: the Next.js frontend and relationship research page are implemented. See [RESEARCH_AUDIT.md](RESEARCH_AUDIT.md) for the validated scope, remaining connector failures and deployment limitations. The milestone notes below describe the earlier migration checkpoint.

## Implemented production slices

- FastAPI production boundary (`/health`, `/api/macro/{country}`, `/api/ask`, `/api/ask/plan`)
- deterministic research planner and constrained production intent contract
- market registry and direct market lookups
- period market calculations
- US economic indicator registry and direct factual lookups
- existing MacroLens current macro environment service
- generic historical relationship research
- MacroLens historical-regime-conditioned relationship context
- selected current-move investigations: Gold, DXY, S&P 500, US 2Y, US 10Y, US 30Y
- targeted OpenAI web catalyst retrieval with fail-closed disabled mode and short TTL cache
- unified frontend-ready `customer_answer` blocks
- optional evidence-only OpenAI answer synthesis; disabled by default via `MACROLENS_ENABLE_AI_SYNTHESIS=false`

## Product safeguards

- AI is not the source of market/economic numbers.
- Web search returns candidate catalysts, not causal proof.
- Current-move answers surface daily-data timing limitations.
- Historical association is explicitly separated from causation.
- MacroLens regime conditioning uses a backward as-of join to reduce look-ahead risk.
- If a capability or required data is unavailable, Ask MacroLens fails closed rather than inventing an answer.

## Still deliberately not production-complete

- conceptual/mechanism questions
- scenario analysis
- arbitrary natural-language research planning via LLM
- full intraday event attribution
- professional/licensed market-data replacement
- user accounts, billing, usage metering
- Next.js customer frontend

## Next build milestone

Build the first Next.js customer shell against this stable answer contract: Home / Ask MacroLens, answer blocks, Markets, Macro, and How It Works. Do not add new research engines before that frontend proof is usable.
