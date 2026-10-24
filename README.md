# MacroLens

Three chart-first pages: **Today**, **Investigate**, **My Research**.

Today: four compact market readings, four large market charts, and US inflation/unemployment charts. Dates stay visible; prices are daily closes, not live quotes or explanations of causes.

Investigate: choose two series and one of three time ranges. Charts appear automatically. No text, number or date-entry fields. Save comparisons with generated names. One short finding describes correlation of appropriate changes, not level correlation or a forecast.

My Research: choose a saved comparison, view its chart and any earlier written notes, and download the original record. Local saves belong to the server and may disappear on restart. Existing version-1 records remain readable. New UI intentionally omits writing/editing notes and advanced statistical forms.

Run `streamlit run app.py`. Tests: `python -m pytest -q`; live checks opt in with `--run-live`. Provider failure and missing observations do not create invented values.

Methodology/engine safeguards remain unchanged. Backend/frontend remain separate consumers. Older notebooks and UI tests remain as compatibility/reference code; production routes call `components/chart_workspace.py`, never the old typing form. See docs/CHART_FIRST_DESIGN.md for verification and limits.
