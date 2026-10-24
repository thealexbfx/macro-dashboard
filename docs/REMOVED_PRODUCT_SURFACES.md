# Removed production surfaces

These files were deleted, not hidden behind navigation. Useful engines and refresh loaders remain for non-UI consumers.

- app_pages/commodities.py
- app_pages/common.py
- app_pages/crypto.py
- app_pages/economy_page.py
- app_pages/equities.py
- app_pages/euro.py
- app_pages/fx.py
- app_pages/global_macro_view.py
- app_pages/historical_regime_explorer.py
- app_pages/home.py
- app_pages/home1.py
- app_pages/home_market_data.py
- app_pages/japan.py
- app_pages/macro_models.py
- app_pages/market_page.py
- app_pages/market_utils.py
- app_pages/rates_bonds.py
- app_pages/regime_monitor.py
- app_pages/uk.py
- app_pages/under_construction.py
- app_pages/usa.py
- app_pages/macro_engine/euro.py
- app_pages/macro_engine/global_overview.py
- app_pages/macro_engine/japan.py
- app_pages/macro_engine/uk.py
- app_pages/macro_engine/usa.py
- app_pages/research/active_ideas.py
- app_pages/research/research_workspace.py
- app_backup.py
- components/page_context.py

Retired tests (underlying page intentionally deleted; analytical engine tests remain):
- test_actual_market_page_preserves_single_and_comparison_paths
- test_country_dashboard_correlation_uses_rate_changes
- test_market_axes_preserve_fractional_quotes
- test_navigation_routes_preserved_and_placeholders_usable

Obsolete shared presentation files removed:
- components\cards.py
- components\charts.py
- components\help_text.py
- components\indicator_layout.py
- components\page_intro.py
- components\research_page.py
- components\sparkline.py
- components\macro_engine\environment_overview.py
- components\macro_engine\evidence.py
- components\macro_engine\formatting.py
- components\macro_engine\hero.py
- components\macro_engine\history.py
- components\macro_engine\indicator_inventory.py
- components\macro_engine\methodology.py
- components\macro_engine\pillar_grid.py
- components\macro_engine\placeholders.py
- components\macro_engine\validation\methodology.py
- components\macro_engine\validation\renderer.py
- components\macro_engine\validation\stability.py
- components\macro_engine\validation\summary.py
- components\macro_engine\validation\transitions.py
- styles\base.css
- styles\buttons.css
- styles\cards.css
- styles\charts.css
- styles\dashboard.css
- styles\macro_engine.css
- styles\quality.css
- styles\research.css
- styles\sidebar.css
- styles\tables.css
- styles\theme.css
- Legacy render_comparison wrapper and test_comparison_streamlit_smoke_and_invalid_mode retired; shared comparison_figure and calculation tests retained.
- Removed unused streamlit-option-menu dependency. OpenAI remains for the existing independent backend consumers; no OpenAI request is made by the Streamlit app.

Obsolete research-page presentation helpers deleted after checking retained imports: bottom_cards.py, research_chart.py, research_page.py, summary_bar.py
