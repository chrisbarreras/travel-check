# ADR-0002: Technology stack

- **Status:** Accepted
- **Date:** 2026-11-24

## Context

The stack should be widely used in industry (portfolio value), free to run, quick to develop with, and able to grow into a commercial product without a rewrite.

## Decision

| Layer | Choice |
|---|---|
| Frontend | React + TypeScript + Vite |
| Map | MapLibre GL JS via `react-map-gl`; Turf.js for great-circle route lines |
| Basemap | OpenFreeMap styles, or self-hosted Protomaps PMTiles |
| UI components and styling | shadcn/ui + Tailwind CSS |
| Data fetching | TanStack Query |
| Charts | Observable Plot or visx (chosen during Phase 1 planning) |
| Backend (Phase 2) | Python + FastAPI + Pydantic |
| Shared types | TypeScript types generated from the Pydantic models / OpenAPI schema |
| Analytics | DuckDB + Parquet |
| Analysis notebooks | Jupyter or marimo |
| Modeling | NumPy / SciPy; scikit-learn only for calibration utilities |
| Python tooling | uv, ruff, pytest, pyright |
| Frontend testing | Vitest + Testing Library; Playwright for key end-to-end flows |
| Infrastructure | Docker; GitHub Actions CI |
| Hosting | Static host for the frontend (Cloudflare Pages or Vercel); container host for the API (chosen in Phase 2) |

Repository layout: a single repo with `pipeline/`, `api/`, `web/`, `notebooks/`, `docs/` and `specs/`.

**Avoid unless a measured need appears:** Next.js, deck.gl, microservices, Kubernetes, Redis, job queues, and networkx for the recovery graph.

## Consequences

- One language (Python) covers the pipeline, the model and the API; TypeScript covers the frontend.
- No paid services are needed through Phase 4.
- Free hosting tiers change over time, so the hosting choice is confirmed against current terms when it's made.
