# MacroLens V2 — isolated Phase 1

## Run
Requires Node 22+ and npm. From `frontend-v2`, run `npm ci`, then `npm run dev`. Open http://localhost:3001. No backend, API keys or environment variables are required. Production preview: `npm run build` then `npm start`.

## Architecture
This additive application uses Next.js App Router, React, strict TypeScript, Tailwind CSS, a shadcn-style Radix Slot/CVA Button, Lucide icons and Recharts. `app/page.tsx` contains the five interactive workspace views; `app/globals.css` defines the responsive terminal theme; `lib/mock.ts` defines typed datasets, investigations and deterministic synthetic series; `components/ui/button.tsx` supplies the shared button primitive. Navigation is client-side workspace state (not separate URL routes). Favourites and investigations persist in localStorage. All values, signals and answers are explicitly mock. No network data or AI calls occur.

The supplied reference guided horizontal navigation, dark navy surfaces, compact market cards, blue chart treatments and information density. This is an interpretation, not a pixel-identical reproduction. Browser visual verification remains outstanding.

## Repository audit and reusable backend
Audited the existing `frontend/package.json`, App Router file structure, frontend API adapter and Next config, backend README, relationship route and backend service/registry structure before choosing an additive sibling frontend. Existing frontend is Next 15.5.28 / React 19 in JavaScript, with no Tailwind or TypeScript setup. Its existing API integration remains untouched.

Reusable backend surfaces:
- `/api/home`: failure-tolerant market moves and cached US macro environment.
- `/api/macro/{country}`: US, UK, euro area and Japan environment snapshots.
- `/api/ask` and `/api/ask/plan`: existing answer and planning contracts; direct market lookups, period calculations and registered economic lookups.
- `/api/research/relationships/series` and `/api/research/relationships`: registered target/driver comparisons with validated timeframe/economy inputs and customer-answer envelopes.
- Services: historical relationships, current moves, catalysts, synthesis, direct answers; economic and market registries; cache infrastructure.
- Existing `macro_engine` environment/pillar/indicator and historical/cross-asset research engines, `discovery` engine/radar/store and data-provider packages are preserved.

Phase 2 should introduce an adapter from backend customer-answer/provenance envelopes to UI datasets and chart observations. Preserve source units and dates; synthetic indexed comparison series must not be presented as raw economic observations. Server persistence and AI evidence are deferred.

## Checks
`npm run build`, `npm run lint`, `npm run typecheck`. Initial lint: zero errors, two configuration export warnings. Build compiled, passed integrated lint/type validation and generated all static pages; see handoff for final process result. No backend or production configuration changes.

## Safety
Branch `feature/macrolens-v2` starts at `redesign-ui`. All tracked changes are under `frontend-v2`. No Render, domain, credentials, Python or existing frontend changes. No deployment or merge authorized or performed.
