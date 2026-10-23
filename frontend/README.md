# MacroLens Frontend — production V1 shell

Next.js customer-facing shell for the production FastAPI backend.

## Local run

Backend from repository root:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000.

By default the frontend calls `http://127.0.0.1:8000`. Override with:

```bash
NEXT_PUBLIC_MACROLENS_API_URL=https://your-api.example.com
```

No account, payment, database or production hosting is required for this local stage.

## Production frontend iteration 2
The Next.js frontend now includes real customer-facing routes for Ask, Markets, Macro and How It Works, plus dedicated renderers for current-move evidence and MacroLens macro-environment blocks. These remain pre-deployment product surfaces; auth/payments are intentionally deferred.

## Frontend V3

The homepage now consumes `GET /api/home` for a failure-tolerant, low-cost market pulse and current US MacroLens environment. Market moves are presented as research entry points, never as causal claims. Clicking a move launches the same `/api/ask` research path as a typed question. The homepage intentionally degrades gracefully if public market-data providers are unavailable.
