# MacroLens Production Backend

Current research endpoints, tests and limitations are documented in [the research audit](../docs/RESEARCH_AUDIT.md). In addition to the routes below, `GET /api/research/relationships/series` lists supported series and `GET /api/research/relationships` accepts `target`, `driver`, `timeframe` and `economy` query parameters.

Run from the repository root so the existing `macro_engine` package and local `cache/` directory resolve correctly:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

Initial endpoints:
- `GET /health`
- `GET /api/macro/{country}` where country is `usa`, `uk`, `euro`, or `japan` (common aliases supported).

This first slice deliberately does not expose the prototype Ask stack yet. The next migration step will bring selected V17 capabilities across behind clean production contracts.

## Ask MacroLens production slice

The production backend now also exposes:

- `POST /api/ask`
- `POST /api/ask/plan`

The first slice executes direct market lookups, period calculations, registered US economic lookups, and current MacroLens macro-environment answers. More expensive or higher-risk research paths are recognized but intentionally fail closed until their production services are migrated.

### Homepage snapshot

`GET /api/home` supplies the public frontend with five latest daily market moves (Gold, US 2Y, US 30Y, S&P 500, DXY) plus the latest cached US MacroLens environment. Individual provider failures are isolated so one missing series does not take down the homepage.
