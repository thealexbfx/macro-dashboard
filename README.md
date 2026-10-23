# MacroLens

The existing Streamlit research application and Next.js/FastAPI production foundation.

See [Research audit, setup and validation](docs/RESEARCH_AUDIT.md) for the implementation, analytical rules, known limitations and complete run instructions.

Quick start from the repository root:

```powershell
python -m pip install -r requirements.txt -r backend/requirements.txt -r requirements-dev.txt
python -m streamlit run app.py
```

Independent investigations are available in the Research Workspace. The production relationship page is `/research/relationships` when the API and frontend are running.
