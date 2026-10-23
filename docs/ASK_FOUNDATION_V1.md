# Ask MacroLens Production Foundation

This is the first production Ask slice. It intentionally migrates contracts and cheap deterministic capabilities before current-move attribution or LLM synthesis.

## Live production-safe capabilities
- research plan contract
- market registry
- US economic indicator registry
- current market lookup
- period market calculation
- registered US economic lookup
- existing MacroLens macro-environment answer
- unified `customer_answer` contract
- optional follow-up questions and contextual MacroLens routes

## Deferred on purpose
- current-move attribution
- targeted web catalyst search
- historical relationship execution
- LLM question interpretation/synthesis

The planner may recognize a deferred request, but execution fails closed with `planned_not_implemented` rather than returning generic AI prose.

## API
- `POST /api/ask`
- `POST /api/ask/plan`

The primary answer is complete on-page. `explore` links exist only as optional deeper MacroLens research paths.
