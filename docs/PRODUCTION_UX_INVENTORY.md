# Production inventory — initial inspection

Baseline: cc4bf576923cfacbf13a1703899a2727239111bf (latest redesign-ui; previous audit merged). Dedicated branch: audit/production-ux-quality.

Production entry: app.py, Streamlit query parameter routes. render.yaml says main while the owner reports Render uses redesign-ui; verify in Render before deployment. Configuration and secrets will remain unchanged. Next.js/FastAPI are separate processes and are not invoked by the Streamlit entry point.

| Group | Route | Page | Primary workflow |
|---|---|---|---|
| Dashboard | ?page=HowItWorks | How MacroLens Works | Read methodology and choose a workflow |
| Dashboard | ?page=MacroEngineGlobal | Global Macro Monitor | Review model evidence, limitations and research implications |
| Decisions | ?page=ActiveIdeas | Active Ideas | Review changed assets and open research |
| Decisions | ?page=ResearchWorkspace | Research Workspace | Investigate, compare and save evidence |
| Macro Engine | ?page=MacroEngineUSA | United States | Review model evidence, limitations and research implications |
| Macro Engine | ?page=MacroEngineEuro | Euro Area | Review model evidence, limitations and research implications |
| Macro Engine | ?page=MacroEngineUK | United Kingdom | Review model evidence, limitations and research implications |
| Macro Engine | ?page=MacroEngineJapan | Japan | Review model evidence, limitations and research implications |
| Historical Research | ?page=HistoricalRegimeExplorer | Regime Explorer | Inspect historical conditional outcomes |
| Historical Research | ?page=RegimeMonitor | Regime Monitor | Unavailable placeholder; choose a related working page |
| Research Tools | ?page=CentralBankWatch | Central Bank Watch | Unavailable placeholder; choose a related working page |
| Research Tools | ?page=Calendar | Calendar | Unavailable placeholder; choose a related working page |
| Research Tools | ?page=ResearchNotes | Research Notes | Unavailable placeholder; choose a related working page |
| Research Tools | ?page=GlobalMacroView | Global Macro Outlook | Unavailable placeholder; choose a related working page |
| Economic + Market Data | ?page=UnitedStates | United States | Select data, inspect series and compare indicators |
| Economic + Market Data | ?page=EuroArea | Euro Area | Select data, inspect series and compare indicators |
| Economic + Market Data | ?page=UnitedKingdom | United Kingdom | Select data, inspect series and compare indicators |
| Economic + Market Data | ?page=Japan | Japan | Select data, inspect series and compare indicators |
| Economic + Market Data | ?page=RatesBonds | Rates & Bonds | Select data, inspect series and compare indicators |
| Economic + Market Data | ?page=Equities | Equities | Select data, inspect series and compare indicators |
| Economic + Market Data | ?page=Commodities | Commodities | Select data, inspect series and compare indicators |
| Economic + Market Data | ?page=FX | FX | Select data, inspect series and compare indicators |
| Economic + Market Data | ?page=Crypto | Crypto | Select data, inspect series and compare indicators |

Shared UI: components/layout.py; styles/theme.py injects eight CSS files. Plotly provides research charts; Streamlit dataframes and charts supply tables and rolling views. Research notebook persistence is local JSON in research_outputs/investigations; exports include JSON, CSV and standalone HTML. Local persistence on ephemeral hosting is not a durable account store.

Providers: Yahoo Finance, FRED, BLS, BEA, ECB, Eurostat and regional sources (Japan/UK). Pure research calculations: macro_engine/research/analytics.py; scoring and decision engines remain separate. Existing safeguards and validation are documented in docs/RESEARCH_AUDIT.md and docs/RESEARCH_VALIDATION_FOLLOWUP.md. Tests cover analytical metadata, units, alignment, persistence and provider boundaries.

Dashboard is a navigation group, not a separate Home route. HowItWorks is the landing page; dormant home modules are not additional deployed routes. Five future destinations are routed to app_pages/under_construction.py. Inventory is source-verified; individual visual verification is recorded separately and must not be inferred from this inventory.
