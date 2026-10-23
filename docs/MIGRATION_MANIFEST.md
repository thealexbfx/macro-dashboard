# Migration Manifest

## Reuse now
- `macro_engine/engine/`
- `macro_engine/models/`
- `macro_engine/metadata/`
- `macro_engine/cache/`
- existing environment cache objects

## Reuse after cleanup
- `macro_engine/pipelines/`
- `macro_engine/historical/`
- `macro_engine/research/`
- selected `macro_engine/decision/`
- `market_data/`
- `economy_data/`
- `data/`
- `indicators/`

## Prototype ideas to migrate selectively from V17
- adaptive research planner
- economic indicator registry
- direct market/economic answers
- market calculations
- targeted catalyst research
- current-move investigation contracts
- historical relationship engine
- MacroLens regime-conditioned historical analysis
- unified customer answer contract

## Do not migrate as public architecture
- Streamlit routing/navigation
- `app_pages/` presentation code
- `components/` presentation code
- monolithic `app.py`
- old top-level `models/` unless an individual component proves unique value
- V1-V17 package structure wholesale
