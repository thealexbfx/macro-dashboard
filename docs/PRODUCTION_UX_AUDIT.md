# Production UX and analytical quality audit

## Scope and evidence

Baseline: cc4bf576923cfacbf13a1703899a2727239111bf, latest redesign-ui at inspection. Streamlit app.py is the production target. Next.js/FastAPI remain separate and are unchanged. Initial inventory is in PRODUCTION_UX_INVENTORY.md. No deployment configuration, secret, model weight or classification rule was changed.

The deployed site was inspected through browser accessibility trees for all 23 navigation destinations, including both research modes. Screenshots cover representative mobile landing/notebook and desktop monitor/evidence views. A route being opened is not proof that every nested control, provider, indicator or responsive breakpoint works. The US regional snapshot was captured before its final validation section finished rendering; other regional views completed. Four exact device breakpoints, screen-reader interaction, and exhaustive indicator selection were not available in this browser API. Tests complement these observations rather than replacing them.

## Page-by-page assessment

Each row identifies the purpose and primary action, then the material issue and remedy. All routes remain compatible.

| Page | Purpose / primary action | Priority and finding | Implementation / remaining limitation |
|---|---|---|---|
| Dashboard group | Choose a workflow | Medium: there is no separate dashboard route; the group mixes introduction and monitor | Preserve landing route; clearer working versus upcoming destinations |
| How MacroLens Works | Understand model and choose a research path | High: confidence explanation could be read as calibrated reliability; heavy typography on mobile | Shared typography/focus treatment; model caveat on evidence pages; existing methodology retained |
| Global Macro Monitor | Compare economies, open a regional view | High: confidence/conviction need distinct meanings; heatmap can rely heavily on colour | Added explicit model interpretation; existing text labels retained; full heatmap semantics remain an opportunity |
| Active Ideas | Review changes and open asset workspace | High: dense repeated change cards and percentage confidence | Added orientation and classification caveat; existing working asset links retained |
| Research Workspace — asset | Review model stance, confirmation and history | High: numeric confidence can be mistaken for direction probability | Added mode distinction and evidence caveat; graceful existing provider-error path retained |
| Research Workspace — independent | Ask, compare, interpret, save | High: indicators precede question; notes compete with evidence; gaps and lag signs hard to interpret | Question first; collapsed advanced methodology; calculated summary, stability labels, lag descriptions, rolling diagnostics; notes and save/export follow evidence |
| US Macro Engine | Inspect environment and pillars | High: extensive validation detail can suggest predictive validation | Shared orientation explains classification versus forecasts; no scoring changes |
| Euro Area Macro Engine | Inspect environment and pillars | High: same classification ambiguity and dense history | Shared orientation/caveat; existing history retained |
| UK Macro Engine | Inspect environment and pillars | High: low conviction versus confidence needs distinction | Shared orientation/caveat; unchanged calculations |
| Japan Macro Engine | Inspect environment and pillars | High: historical churn metrics not predictive validation | Shared orientation/caveat; unchanged classifications |
| Regime Explorer | Select environment and inspect forward outcomes | High: missing joined months can shift horizon; overlapping samples are descriptive | Exact calendar-month outcome lookup; explicit historical caveat and regression |
| Regime Monitor | Future monitoring tool | Medium: dead end appears as working navigation | Grouped Coming soon; useful working alternatives |
| Central Bank Watch | Future policy tool | Medium: dead end | Clear unavailable state and working alternatives |
| Calendar | Future events tool | Medium: no events despite prominent destination | Clear unavailable state and working alternatives |
| Research Notes | Future publication library | Medium: unavailable page despite library links | Clear unavailable state and path to saved investigations |
| Global Macro Outlook | Future synthesis tool | Medium: unavailable page | Clear unavailable state and working alternatives |
| US Economic Data | Choose indicator and inspect source/units | Medium: duplicate regional labels confuse raw data and model views | Data explorer versus Regional model views; orientation; shared controls and responsive styling |
| Euro Area Economic Data | Explore indicators | Medium: same duplicate naming and dense controls | Same shared improvements; explicit effective-state metadata retained |
| UK Economic Data | Explore indicators | Medium: same duplicate naming | Same shared improvements |
| Japan Economic Data | Explore indicators | Medium: same duplicate naming | Same shared improvements |
| Rates & Bonds | Explore yields and compare changes | High: axis ticks round different yields to the same integer | Two-decimal axis labels; basis-point transformation safeguards retained |
| Equities | Explore prices and comparisons | Medium: dense controls and inconsistent chart context | Shared styling/orientation; revised comparison chart metadata and zero reference |
| Commodities | Explore contracts and compare | High: futures returns should not be interpreted as spot or total return | Existing futures source labels retained; export/source discussion below; no invented roll adjustments |
| FX | Explore quotes and compare | High: repeated integer 1 ticks obscure EUR/USD movement | Two-decimal axes; shared comparison improvements |
| Crypto | Explore seven-day markets | Medium: cross-market calendars and annualisation differ | Existing 365-day crypto and mixed-weekday safeguards retained; shared orientation |

## Implemented design conventions

Reuse the existing CSS system rather than introducing a new frontend. Navy navigation, white evidence panels, blue and amber series, restrained weights and visible focus outlines. Controls retain at least 44px touch height. Long labels wrap. Mobile content reserves menu clearance; columns wrap and summary tiles become two columns. Reduced-motion preferences disable transitions. Captions use #475569 on white (approximately 7.6:1 contrast). This does not constitute a full WCAG certification; legacy inline styles and heatmap semantics still need specialist review.

All 23 route keys survive. Upcoming pages move to the bottom after usable tools. The mobile checkbox has an accessible name and becomes keyboard-focusable rather than display:none. Active links expose aria-current. No modal focus trap is claimed; keyboard users can toggle the navigation checkbox again.

The independent workflow now follows question → data → methodology → calculated evidence → researcher notes → save/export. Advanced controls remain available. A frequency selector only allows coarsening; period-end observations remain explicit. Existing schema-version-1 records default to native alignment. Input changes invalidate displayed evidence until rerun. The module still loads data only on an explicit run; saved evidence opens without network calls. Temporary provider failures and local save failures have useful messages. Local saves remain server-scoped and ephemeral; the UI explicitly recommends export for durability.

## Gold versus US 10Y: real-data verification

The requested 2000-01-01 to 2026-10-24 sample was run on the deployed production UI, Changes, window 60. The exported JSON contained both raw source series and transformed values. Those source observations were independently recalculated locally with the shared engine; no synthetic data or hardcoded expected correlation was used.

| Measurement | Recalculated value |
|---|---:|
| First paired level | 2000-08-30 |
| Last paired level | 2026-10-22 |
| Comparison grid periods | 6,588 |
| Paired levels | 6,512 |
| Unpaired level periods | 76 |
| Valid paired changes | 6,435 |
| Full-sample correlation | -0.15965599 |
| First-half correlation (3,201 pairs) | -0.07785809 |
| Second-half correlation (3,234 pairs) | -0.27215318 |
| Valid 60-period windows | 3,517 |
| Initial warm-up periods | 59 |
| Later windows with incomplete paired changes | 3,012 |
| Complete windows with undefined variation | 0 |
| Latest valid rolling date | 2026-10-09 |
| Latest valid rolling correlation | -0.30551668 |

These reproduce the reference observations. The requested start precedes the available Gold futures series; the requested end is later than the last common source observation. No future observations were invented. The production server displayed October 24 while the client context date was October 23; calendar labels should be harmonised separately rather than silently rewriting captured evidence.

Gold uses eligible price percentage changes with fill_method=None. US 10Y uses first differences multiplied by 100 basis points per percentage point. The observed-session union retains a period missing on either side. Fully absent calendar dates do not become fabricated trading sessions. No changes bridge a missing cell on the retained grid. The 76 missing level periods and 153 missing transformed pairs measure different things: a missing level affects adjacent changes. Hence 6,588 minus 6,435 equals 153, rather than 76.

The window requires 60 consecutive grid periods with both changes. One missing change invalidates multiple windows; missing Gold observations on April 3/6 and missing yields on October 12/13 illustrate this. October 12/13 yield levels are missing, so the October 22 terminal window remains unavailable. Market-calendar differences and provider omissions are not distinguished without authoritative exchange calendars; do not label all gaps as provider errors. Values remain missing. The UI now separates warm-up, incomplete windows, undefined variation and valid windows, and identifies the last valid result explicitly.

Lag zero is stronger in magnitude than every nonzero scanned lag. The summary states this and makes no predictive claim. Positive h compares left(t) with right(t+h); negative h means right leads left. Units are comparison periods. Splitting halves uses the whole grid, yielding unequal valid counts. The second-half correlation is more negative, but no structural-change significance test was performed. Threshold labels describe |r| only: <.10 very weak, <.30 weak, <.50 moderate, <.70 strong, otherwise very strong. Correlation is not causation.

Gold is a Yahoo futures closing-price series, not a spot or total-return investment index. Contract roll conventions, release timing, revisions, autocorrelation and lag-selection multiplicity remain limitations. Weekly sampling, direct real yields and crisis-period sensitivity are proposed further tests, not explanations.

## Additional analytical review

Existing research safeguards were reviewed for price versus yield changes, no implicit percentage fill, compatible ratio metadata, separate axes/panels, drawdowns, return eligibility, frequency alignment, annualisation (252 market days versus 365 crypto days), lag sign and backward release-date joins. These protections remain. Broader historical outcomes use latest-vintage environment histories and may overlap; calibrated predictive accuracy is not established.

A genuine horizon defect was found in environment_validation.add_forward_outcomes: shifting rows after inner joins can turn a nominal one-month outcome into several calendar months when joined months are absent. The implementation now looks up month+h exactly and leaves unavailable endpoints missing. Duplicate months are rejected; nonfinite division results are unavailable. It does not alter economic model weights. Other legacy single-series charts and decision-model calculations were reviewed selectively, not mathematically proven in their entirety.

## Verification and release limits

Default tests, lint and whitespace checks are recorded in the final test report/PR. Tests retain the provider network guard and opt-in live checks. The real production investigation export is evidence for this sample, not a guarantee of future provider availability. The local asset view encountered Yahoo unavailability and displayed the expected recovery message.

Before/after screenshots are saved as deliverables. The after notebook reopens the real production export locally; it is neither a new live provider download nor synthetic data. Browser API supplied a 319px mobile surface and a 1280px desktop surface. Tablet/laptop-specific viewport emulation was not exposed. Do not infer four-device certification. Saved note updates and exports are exercised by automated UI tests in addition to browser checks.

## Deferred opportunities

- Durable per-user research storage and migration/import workflow: requires account/storage design; current local storage warning and export remain explicit.
- Vintage-aware macro backtests and calibrated forecasts: require historical releases and evaluation datasets; no UI change can establish them.
- Exchange-calendar-aware diagnostics: calendars and instrument-specific sessions must be curated before classifying every absence.
- Heatmap accessible data table, keyboard focus trap and full screen-reader audit: shared focus and textual caveats improve access but do not finish these tasks.
- Building the five upcoming tools: the scope is product quality, not invented event feeds or research publications.
- Full legacy chart retirement and every indicator/provider permutation: compatibility is preserved; systematic coverage can grow without a risky rewrite.
- Render branch discrepancy: owner reports redesign-ui, render.yaml says main. Configuration was intentionally untouched as requested.
