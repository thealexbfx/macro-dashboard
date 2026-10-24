# Product decision

MacroLens is a daily market check and personal relationship-research notebook.

Navigation: Today, Investigate, My Research. Daily journey: check four dated market moves, follow a question, inspect a chart and one descriptive finding, write a conclusion, export and return later.

Keep: provider catalogue, unit metadata, gap-aware transformations, correlation/lag engines, version-1 investigation JSON and exports. Simplify: notebook inputs and findings; dates/methods and optional statistics go behind expanders. Merge: all economic/market browsing into indicator selection; saved work into My Research. Remove: production model-stance dashboards, regional model displays, regime dashboards, duplicate economic/market pages, onboarding essay, active ideas, placeholders and old sidebar/style system. Retain non-UI model engines for tested backend/research consumers, not loaded by the new app. Next.js/FastAPI are separate existing consumers, not a migration target.

PR #2 merged as 82e14d0; its numerical safeguards and save compatibility are inherited directly. Risks: provider outages, latest-vintage observations, local hosting storage is temporary, old model deep links change meaning. Redirect old links with an explicit notice; never imply old model output still exists. No secrets or infrastructure changes.

## Existing feature decisions

| Previous destination | Decision | New home / reason |
|---|---|---|
| How MacroLens Works (HowItWorks) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| Global Macro Monitor (MacroEngineGlobal) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| Active Ideas (ActiveIdeas) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| Research Workspace (ResearchWorkspace) | Simplify | Investigate; question-led evidence replaces model-led stance |
| United States (MacroEngineUSA) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| Euro Area (MacroEngineEuro) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| United Kingdom (MacroEngineUK) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| Japan (MacroEngineJapan) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| Regime Explorer (HistoricalRegimeExplorer) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| Regime Monitor (RegimeMonitor) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| Central Bank Watch (CentralBankWatch) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| Calendar (Calendar) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| Research Notes (ResearchNotes) | Remove / replace | Delete unfinished publication page; My Research contains actual saved questions |
| Global Macro Outlook (GlobalMacroView) | Remove | Does not earn a weekly place in the three jobs; no retained dashboard route |
| United States (UnitedStates) | Merge | Indicator catalogue within Investigate; delete duplicate page and chart UI |
| Euro Area (EuroArea) | Merge | Indicator catalogue within Investigate; delete duplicate page and chart UI |
| United Kingdom (UnitedKingdom) | Merge | Indicator catalogue within Investigate; delete duplicate page and chart UI |
| Japan (Japan) | Merge | Indicator catalogue within Investigate; delete duplicate page and chart UI |
| Rates & Bonds (RatesBonds) | Merge | Indicator catalogue within Investigate; delete duplicate page and chart UI |
| Equities (Equities) | Merge | Indicator catalogue within Investigate; delete duplicate page and chart UI |
| Commodities (Commodities) | Merge | Indicator catalogue within Investigate; delete duplicate page and chart UI |
| FX (FX) | Merge | Indicator catalogue within Investigate; delete duplicate page and chart UI |
| Crypto (Crypto) | Merge | Indicator catalogue within Investigate; delete duplicate page and chart UI |

## Metrics retained and their purpose

| Metric | Calculation / purpose | Placement and limit |
|---|---|---|
| Latest market move | Last two recorded observations; eligible price percent change or yield difference ×100 bp | Today, with exact dates/source; not a causal explanation or guaranteed calendar-day return |
| Coverage and missingness | Counts of paired levels and valid changes on explicit comparison grid | Evidence caption; establishes what was analysed, not quality of a forecast |
| Correlation | Pearson correlation of economically appropriate paired changes | One headline; descriptive linear association, not causation or prediction |
| Rolling correlation | Consecutive full windows of paired changes | Optional evidence; incomplete windows remain missing and latest valid date is explicit |
| Lag scan | Left(t) against right(t+h), with sample counts | Optional; signs explained, multiple testing prevents predictive claims |
| Historical splits | Correlation in grid halves | Optional; not a test of statistically significant structural change |
| Other transformations | Existing metadata-constrained returns, spreads, ratios, drawdown and volatility | Optional methodology; existing unit and missing-data safeguards remain |

Model conviction, classification-confidence percentages, macro scores, stance labels, similarity metrics and historical probabilities have no production UI display. Model engines remain because independent backend consumers and tests use them. This is not a promise that they are calibrated.
