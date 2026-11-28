# Architecture

Travel Check shows how often a flight connection actually worked, from public U.S. on-time data. In Phase 1 it is a static site with no server. A Python pipeline computes everything ahead of time, and the browser only loads, checks and formats the results ([ADR-0001](adr/0001-static-first-delivery.md)).

## Data flow

```text
BTS on-time, DB1B, T-100 (pinned by checksum in config/)
        │
        ▼
pipeline/  (Python: flight_pipeline)
  prepare → slots → hubs → itineraries → analyze → curate → insights → publish
        │                                                     │
        │ Pydantic models (the one data contract, ADR-0007)   │
        ▼                                                     ▼
shared/schemas/showcase.schema.json          site-data/showcase/  (committed JSON)
shared/types/showcase.ts  (generated)          index.json, landing.json, manifest.json, routes/*.json
        │                                                     │
        ▼                                                     ▼
web/  (React, TypeScript, Vite)
  build: copies site-data/showcase/ unchanged into dist/data/showcase/ (checked by SHA-256)
         compiles standalone validators from the schema (npm run gen)
  page:  DataSource (web/src/data/)  →  validate  →  cross-check  →  format  →  components
        │
        ▼
GitHub Pages: https://chrisbarreras.github.io/travel-check/
```

- **One contract.** The pipeline's Pydantic models generate the JSON Schema and the TypeScript types. CI fails when they are stale. The web app imports the types through the `@contract` alias, and builds its runtime validators from the same schema. No data shape is written by hand anywhere ([constitution](../.specify/memory/constitution.md), Principle IV).
- **One way in.** Screens read data only through `web/src/data/`, a `DataSource` with `getIndex`, `getLanding`, `getRoute` and `getManifest`. A lint rule forbids `fetch` anywhere else. Every file is validated whole before use, and a bad or missing file gives a plain error state, never partial figures ([contract](../specs/003-web-foundation/contracts/data-access.md)).
- **Formatting only in the browser.** The page rounds and words values that the pipeline computed: whole percent, whole points, local clock times from the schedule. It does no statistics and no time-zone arithmetic. The transfer-time slider (feature `explorer-insights`) will be the first calculation in the browser, checked against the shared test cases in `shared/test-cases/`.

## Where Phase 2 plugs in

A future API implements the same `DataSource` interface and returns the same response shapes, so screens don't change. Whether the static files stay as the data format or as a fallback is an open Phase 2 decision ([roadmap](roadmap.md), Phase 2, "Decide before planning").

## Checks and delivery

| Workflow | Job | What it does |
|---|---|---|
| `pipeline` | `checks` | ruff, pyright, pytest, generated schema and types up to date |
| `web` | `web-checks` | Prettier, ESLint, `tsc`, Vitest, build with the data-copy check, size budgets (JS ≤ 150 KB gzip, first-view data ≤ 150 KB gzip) |
| `web` | `web-browser` | Playwright e2e, visual, axe (WCAG 2.2 AA) and keyboard tests, in the pinned `mcr.microsoft.com/playwright:v1.65.0-noble` image |
| `web` | `web-lighthouse` | Lighthouse CI, median of 3 mobile runs: performance ≥ 0.90, accessibility 1.00, LCP ≤ 2.5 s, CLS ≤ 0.1 |
| `web` | `web-deploy` | On `main` only, after the three web jobs: build for `/travel-check/`, deploy to GitHub Pages, smoke-check the live page |

**Merge blocking** ([ADR-0015](adr/0015-static-hosting-github-pages.md)): a ruleset on `main` requires a pull request and the checks `checks`, `web-checks`, `web-browser` and `web-lighthouse`, and blocks force pushes and deletion. It was set up once with the GitHub CLI:

```bash
# Pages, deployed by GitHub Actions
gh api -X POST repos/chrisbarreras/travel-check/pages -f build_type=workflow

# Ruleset on main
gh api -X POST repos/chrisbarreras/travel-check/rulesets --input ruleset.json
```

The ruleset's JSON is in [specs/003-web-foundation/validation.md](../specs/003-web-foundation/validation.md).
